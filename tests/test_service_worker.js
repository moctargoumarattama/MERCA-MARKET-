const assert = require("node:assert/strict");
const { readFileSync } = require("node:fs");
const path = require("node:path");
const test = require("node:test");
const vm = require("node:vm");

const workerSource = readFileSync(
    path.join(__dirname, "../static/js/service-worker.js"), "utf8"
);
const origin = "https://merca.example";
const page = (language) => new Response(`<html lang="${language}"></html>`);

function worker({ online = true, currentLanguage = "fr" } = {}) {
    const listeners = new Map();
    const entries = new Map([[`${origin}/`, page("ar")]]);
    const key = (request) => new URL(request.url || request, origin).href;
    const cache = {
        async match(request) { return entries.get(key(request))?.clone(); },
        async put(request, response) { entries.set(key(request), response.clone()); },
    };

    vm.runInNewContext(workerSource, {
        URL, Response,
        self: {
            location: { origin },
            addEventListener: (name, listener) => listeners.set(name, listener),
        },
        caches: { open: async () => cache, match: cache.match },
        fetch: async (request) => {
            if (!online) throw new Error("Offline");
            const language = new URL(request.url).pathname.match(/^\/language\/(fr|ar)$/);
            if (language) currentLanguage = language[1];
            return page(currentLanguage);
        },
    });

    return {
        async navigate(url) {
            const pending = [];
            let response;
            listeners.get("fetch")({
                request: { url: new URL(url, origin).href, method: "GET", mode: "navigate" },
                respondWith: (promise) => { response = Promise.resolve(promise); },
                waitUntil: (promise) => pending.push(promise),
            });
            try {
                return await response;
            } finally {
                await Promise.allSettled(pending);
            }
        },
    };
}

test("FR -> AR -> FR displays the chosen language despite an Arabic cached page", async () => {
    const browser = worker();
    for (const language of ["fr", "ar", "fr"]) {
        const response = await browser.navigate(`/language/${language}?next=/`);
        assert.equal(await response.text(), `<html lang="${language}"></html>`);
    }
});

test("online navigation displays the current language instead of stale Arabic", async () => {
    const response = await worker().navigate("/");
    assert.equal(await response.text(), '<html lang="fr"></html>');
});

test("offline navigation can still display the cached home page", async () => {
    const response = await worker({ online: false }).navigate("/cart");
    assert.equal(await response.text(), '<html lang="ar"></html>');
});

test("an offline language change does not appear to succeed with cached HTML", async () => {
    const response = await worker({ online: false })
        .navigate("/language/fr?next=/")
        .catch(() => null);
    assert.ok(!response || !response.ok, "A language change needs a server response");
});
