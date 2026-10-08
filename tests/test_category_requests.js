const assert = require("node:assert/strict");
const { readFileSync } = require("node:fs");
const path = require("node:path");
const test = require("node:test");
const { setImmediate: nextTurn } = require("node:timers/promises");
const vm = require("node:vm");

const source = readFileSync(path.join(__dirname, "../static/js/app.js"), "utf8");

function deferred() {
    let resolve, reject;
    const promise = new Promise((yes, no) => { resolve = yes; reject = no; });
    return { promise, resolve, reject };
}

function element() {
    const classes = new Set();
    return {
        innerHTML: "", textContent: "", value: "", disabled: false,
        classList: {
            add: name => classes.add(name), remove: name => classes.delete(name),
            contains: name => classes.has(name),
        },
    };
}

function browser() {
    const panel = element(), backdrop = element();
    const nodes = Object.fromEntries([
        "cat-modal-name", "cat-modal-badge", "cat-modal-count-sub",
        "cat-modal-search-input", "cat-modal-body",
    ].map(id => [id, element()]));
    const requests = [], errors = [];
    const context = vm.createContext({
        AbortController,
        document: {
            body: { style: {} }, documentElement: { lang: "fr" },
            addEventListener() {},
            querySelector: selector => selector === "[data-cat-modal-panel]" ? panel
                : selector === "[data-cat-modal-backdrop]" ? backdrop : null,
            getElementById: id => nodes[id] || null,
        },
        window: { SHOP_CONFIG: { uiStrings: {
            "category_modal.loading": "Chargement",
            "category_modal.products_count": "{count} produits",
            "category_modal.no_products": "Indisponible",
        } } },
        console: { error: (...args) => errors.push(args), warn() {} },
        fetch(url, options) {
            const request = { ...deferred(), url, signal: options?.signal };
            requests.push(request);
            // Intentionally ignore abort: already received responses may still finish.
            return request.promise;
        },
    });
    vm.runInContext(source, context);
    return {
        open: context.openCategoryModal, close: context.closeCategoryModal,
        requests, errors, panel,
        body: nodes["cat-modal-body"], title: nodes["cat-modal-name"],
        count: nodes["cat-modal-count-sub"], search: nodes["cat-modal-search-input"],
        productIds: () => vm.runInContext("currentCatModalProducts.map(p => p.id).join(',')", context),
    };
}

const product = (id, name) => ({ id, name, price: 15, weight_options: [] });
const response = products => ({ ok: true, json: async () => ({ products }) });

test("rapid category clicks keep the latest products, title and count when responses arrive backwards", async () => {
    const page = browser();
    page.open(1, "Amandes", 8);
    page.open(2, "Noix", 2);
    page.open(3, "Dattes", 1);
    assert.equal(page.requests[0].signal.aborted, true);
    assert.equal(page.requests[1].signal.aborted, true);
    page.requests[2].resolve(response([product(30, "Dattes choisies")]));
    await nextTurn();
    const displayed = page.body.innerHTML;
    page.requests[1].resolve(response([product(20, "Anciennes noix")]));
    page.requests[0].resolve(response([product(10, "Anciennes amandes")]));
    await nextTurn();
    assert.match(displayed, /Dattes choisies/);
    assert.equal(page.body.innerHTML, displayed);
    assert.equal(page.title.textContent, "Dattes");
    assert.equal(page.count.textContent, "1 produits");
    assert.equal(page.productIds(), "30");
    assert.equal(page.search.disabled, false);
});

test("an older response still decoding JSON cannot overwrite the next category", async () => {
    const page = browser(), json = deferred();
    page.open(1, "Amandes", 1);
    page.requests[0].resolve({ ok: true, json: () => json.promise });
    await nextTurn();
    page.open(2, "Noix", 1);
    page.requests[1].resolve(response([product(20, "Noix choisies")]));
    await nextTurn();
    json.resolve({ products: [product(10, "Anciennes amandes")] });
    await nextTurn();
    assert.equal(page.productIds(), "20");
    assert.match(page.body.innerHTML, /Noix choisies/);
    assert.doesNotMatch(page.body.innerHTML, /Anciennes amandes/);
});

test("an old failure does not replace a newer successful result", async () => {
    const page = browser();
    page.open(1, "Amandes", 1);
    page.open(2, "Noix", 1);
    page.requests[1].resolve(response([product(20, "Noix choisies")]));
    await nextTurn();
    const displayed = page.body.innerHTML;
    page.requests[0].reject(new Error("Late network error"));
    await nextTurn();
    assert.equal(page.body.innerHTML, displayed);
    assert.equal(page.errors.length, 0);
});

test("old request cleanup cannot enable search while the newest request is pending", async () => {
    const page = browser();
    page.open(1, "Amandes", 1);
    page.requests[0].resolve(response([product(10, "Amandes")]));
    await nextTurn();
    page.open(2, "Noix", 1);
    assert.equal(page.productIds(), "");
    assert.equal(page.search.disabled, true);
    page.open(3, "Dattes", 1);
    page.requests[1].reject(Object.assign(new Error("Aborted"), { name: "AbortError" }));
    await nextTurn();
    assert.equal(page.search.disabled, true);
    assert.match(page.body.innerHTML, /cat-modal-loading/);
    assert.equal(page.errors.length, 0);
    page.requests[2].resolve(response([product(30, "Dattes")]));
    await nextTurn();
    assert.equal(page.search.disabled, false);
});

test("closing the category cancels its request and ignores a response received afterwards", async () => {
    const page = browser();
    page.open(1, "Amandes", 1);
    page.close();
    const closedContent = page.body.innerHTML;
    assert.equal(page.requests[0].signal.aborted, true);
    page.requests[0].resolve(response([product(10, "Anciennes amandes")]));
    await nextTurn();
    assert.equal(page.panel.classList.contains("is-open"), false);
    assert.equal(page.body.innerHTML, closedContent);
    assert.equal(page.productIds(), "");
});

test("reopening the same category ignores the response from its previous opening", async () => {
    const page = browser();
    page.open(1, "Amandes", 1);
    page.close();
    page.open(1, "Amandes", 1);
    page.requests[1].resolve(response([product(11, "Nouvelle selection")]));
    await nextTurn();
    page.requests[0].resolve(response([product(10, "Ancienne selection")]));
    await nextTurn();
    assert.equal(page.productIds(), "11");
    assert.match(page.body.innerHTML, /Nouvelle selection/);
});

test("a current HTTP failure ends loading and another category can still load", async () => {
    const page = browser();
    page.open(1, "Amandes", 1);
    page.requests[0].resolve({ ok: false, status: 500, json: () => assert.fail("Do not render an error response") });
    await nextTurn();
    assert.equal(page.search.disabled, false);
    assert.equal(page.productIds(), "");
    assert.equal(page.errors.length, 1);
    assert.doesNotMatch(page.body.innerHTML, /cat-modal-loading/);
    page.open(2, "Noix", 1);
    page.requests[1].resolve(response([product(20, "Noix")]));
    await nextTurn();
    assert.equal(page.productIds(), "20");
    assert.equal(page.search.disabled, false);
});
