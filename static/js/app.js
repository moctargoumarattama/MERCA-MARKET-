const CART_KEY = "merca_fruit_sec_cart";
const CUSTOMER_NAME_KEY = "merca_fruit_sec_customer_name";
const CUSTOMER_ADDRESS_KEY = "merca_fruit_sec_customer_address";
const DEFAULT_WHATSAPP = "212622135964";
const SEARCH_MIN_CHARS = 2;
const SEARCH_DEBOUNCE_MS = 220;
const QUICK_RETURN_POSITION_KEY = "merca_fruit_sec_quick_return_position";
const QUICK_RETURN_DRAG_THRESHOLD = 6;
const SHOWCASE_DRAG_THRESHOLD = 6;
const SHOWCASE_AUTO_SCROLL_SPEED = 0.05;
const liveSearchState = new WeakMap();
const showcaseMarqueeState = new WeakMap();
const DEFAULT_UI_STRINGS = {
    "js.search.loading": "Recherche en cours...",
    "js.search.unavailable": "La recherche est temporairement indisponible.",
    "js.search.no_results": "Aucun resultat pour {query}. Essayez un autre mot-cle.",
    "js.search.categories": "Categories",
    "js.search.products": "Produits",
    "js.search.category_count": "{count} produit{suffix}",
    "js.search.stock_available": "{count} en stock",
    "js.cart.max_quantity": "Quantite maximale atteinte pour ce produit.",
    "js.cart.out_of_stock": "Ce produit est en rupture de stock.",
    "js.cart.added": "{name} a ete ajoute au panier.",
    "js.cart.removed": "Produit supprime du panier.",
    "js.cart.empty": "Votre panier est vide.",
    "js.cart.empty_already": "Votre panier est deja vide.",
    "js.cart.clear_confirm": "Vider le panier ?",
    "js.cart.cleared": "Panier vide.",
    "js.cart.checkout_intro": "Bonjour {shop_name}, je souhaite passer cette commande :",
    "js.cart.total": "Total : {total}",
    "js.cart.name": "Nom : {name}",
    "js.cart.address": "Adresse : {address}",
    "js.cart.confirm": "Merci de confirmer ma commande.",
    "js.cart.unit": "unite",
    "js.cart.stock_available_short": "{count} dispo",
    "js.cart.stock_out": "Rupture",
    "js.cart.explore": "Explorer le catalogue",
    "js.menu.open": "Ouvrir le menu",
    "js.menu.close": "Fermer le menu",
    "js.quick_return.products": "Produits",
    "js.quick_return.search": "Recherche",
    "js.modal.product": "Produit",
    "js.modal.no_description": "Aucune description disponible.",
    "js.modal.close": "Fermer",
    "home.product.add": "Ajouter au panier",
    "home.product.out_of_stock": "Rupture",
    "home.product.category_empty": "Sans categorie",
    "cart.empty.title": "Votre panier est vide",
    "cart.empty.body": "Ajoutez des produits depuis le catalogue pour construire votre commande.",
    "cart.empty.button": "Explorer le catalogue",
};
const quickReturnState = {
    dragging: false,
    dragStarted: false,
    pointerId: null,
    startX: 0,
    startY: 0,
    startLeft: 0,
    startTop: 0,
    suppressClick: false,
};
let shopConfigCache = null;
let translationWarningsLogged = false;

function getShopConfig() {
    if (shopConfigCache) {
        return shopConfigCache;
    }

    try {
        const configElement = document.getElementById("shop-config");

        if (configElement && configElement.textContent) {
            shopConfigCache = JSON.parse(configElement.textContent);
            return shopConfigCache;
        }
    } catch (error) {
        console.warn("Unable to parse shop config:", error);
    }

    shopConfigCache = window.SHOP_CONFIG || {};
    return shopConfigCache;
}

function getCurrentLanguage() {
    const config = getShopConfig();
    return String(config.currentLanguage || document.documentElement.lang || "fr").toLowerCase();
}

function formatTemplate(template, params = {}) {
    return String(template || "").replace(/\{(\w+)\}/g, (_, key) => {
        const value = params[key];
        return value === undefined || value === null ? "" : String(value);
    });
}

function getUiStrings() {
    const config = getShopConfig();
    const missingKeys = Array.isArray(config.translationMissingKeys) ? config.translationMissingKeys : [];

    if (!translationWarningsLogged && getCurrentLanguage() !== "fr" && missingKeys.length) {
        translationWarningsLogged = true;
        console.warn(
            `Missing translations for ${getCurrentLanguage()}: ${missingKeys.join(", ")}`
        );
    }

    return {
        ...DEFAULT_UI_STRINGS,
        ...(config.defaultUiStrings || {}),
        ...(config.uiStrings || {}),
    };
}

function t(key, params = {}, fallback = "") {
    const template = getUiStrings()[key] ?? fallback ?? key;
    return formatTemplate(template, params);
}

function pluralSuffix(count) {
    const value = Number(count) || 0;

    if (value === 1) {
        return "";
    }

    return getCurrentLanguage() === "ar" ? "ات" : "s";
}

function formatCurrency(value) {
    const amount = Number(value) || 0;
    const locale = getCurrentLanguage() === "ar" ? "ar-MA" : "fr-MA";

    try {
        return `${new Intl.NumberFormat(locale, {
            minimumFractionDigits: 2,
            maximumFractionDigits: 2
        }).format(amount)} DH`;
    } catch {
        return `${amount.toFixed(2)} DH`;
    }
}

function normalizeStock(stock) {
    if (stock === null || stock === undefined || stock === "") {
        return null;
    }

    const parsed = Number(stock);
    return Number.isFinite(parsed) ? Math.max(0, Math.trunc(parsed)) : null;
}

function normalizeItem(item) {
    return {
        id: Number(item.id),
        name: String(item.name || ""),
        price: Number(item.price) || 0,
        image: item.image || "",
        stock: normalizeStock(item.stock),
        quantity: Math.max(1, Number(item.quantity) || 1)
    };
}

function normalizeSearchQuery(value) {
    return String(value || "").trim().replace(/\s+/g, " ");
}

function buildShopUrl(baseUrl, params = {}) {
    const url = new URL(baseUrl || "/", window.location.origin);

    Object.entries(params).forEach(([key, value]) => {
        if (value !== null && value !== undefined && value !== "") {
            url.searchParams.set(key, String(value));
        }
    });

    return url.toString();
}

function buildStaticImageUrl(filename) {
    if (!filename) {
        return "";
    }

    const baseUrl = String(getShopConfig().staticImagesUrl || "/static/images/");
    const normalizedBase = baseUrl.endsWith("/") ? baseUrl : `${baseUrl}/`;
    const normalizedName = String(filename).replace(/^\/+/, "");

    return `${normalizedBase}${encodeURIComponent(normalizedName)}`;
}

function getLiveSearchState(root) {
    let state = liveSearchState.get(root);

    if (!state) {
        state = {
            timer: null,
            controller: null,
        };
        liveSearchState.set(root, state);
    }

    return state;
}

function renderLiveSearchCategory(category, productsUrl) {
    const categoryName = String(category.name || "");
    const categoryUrl = buildShopUrl(productsUrl, { category: category.id });
    const count = Number(category.product_count) || 0;
    const media = category.cover_image
        ? `<img src="${escapeHtml(buildStaticImageUrl(category.cover_image))}" alt="">`
        : `<div class="search-live-category-fallback">${escapeHtml(categoryName.slice(0, 1).toUpperCase() || "M")}</div>`;

    return `
        <a class="search-live-category" href="${escapeHtml(categoryUrl)}">
            <div class="search-live-category-media">${media}</div>
            <div class="search-live-category-body">
                <strong>${escapeHtml(categoryName)}</strong>
                <small>${escapeHtml(t("js.search.category_count", { count, suffix: pluralSuffix(count) }))}</small>
            </div>
        </a>
    `;
}

function renderLiveSearchProduct(product) {
    const stock = normalizeStock(product.stock);
    const stockLabel = stock === null
        ? ""
        : stock === 0
            ? t("js.cart.out_of_stock")
            : t("js.search.stock_available", { count: stock });
    const imageMarkup = product.image
        ? `<img src="${escapeHtml(buildStaticImageUrl(product.image))}" alt="">`
        : `<div class="search-live-product-fallback">MF</div>`;

    return `
        <article class="search-live-product">
            <div class="search-live-product-media">${imageMarkup}</div>
            <div class="search-live-product-body">
                <small>${escapeHtml(product.category_name || t("home.product.category_empty"))}</small>
                <strong>${escapeHtml(product.name || "")}</strong>
                <span>
                    ${escapeHtml(formatCurrency(product.price))}
                    ${stockLabel ? `&middot; ${escapeHtml(stockLabel)}` : ""}
                </span>
            </div>
            <button
                type="button"
                class="button-primary"
                ${stock === 0 ? "disabled" : ""}
                data-cart-add
                data-product-id="${escapeHtml(product.id)}"
                data-product-name="${escapeHtml(product.name || "")}"
                data-product-price="${escapeHtml(product.price)}"
                data-product-image="${escapeHtml(product.image || "")}"
                data-product-stock="${escapeHtml(stock === null ? "" : stock)}"
            >
                ${stock === 0 ? t("home.product.out_of_stock") : t("home.product.add")}
            </button>
        </article>
    `;
}

function renderLiveSearchResults(root, payload, query) {
    const resultsNode = root.querySelector("[data-live-search-results]");

    if (!resultsNode) {
        return;
    }

    const normalizedQuery = normalizeSearchQuery(query);

    if (normalizedQuery.length < SEARCH_MIN_CHARS) {
        resultsNode.hidden = true;
        resultsNode.innerHTML = "";

        return;
    }

    const categories = Array.isArray(payload?.categories) ? payload.categories : [];
    const products = Array.isArray(payload?.products) ? payload.products : [];
    const productsUrl = getShopConfig().productsUrl || `${getShopConfig().indexUrl || "/"}#products`;
    const sections = [];

    if (categories.length) {
        sections.push(`
            <section class="search-live-group">
                <h3>${escapeHtml(t("js.search.categories"))}</h3>
                <div class="search-live-grid">
                    ${categories.map((category) => renderLiveSearchCategory(category, productsUrl)).join("")}
                </div>
            </section>
        `);
    }

    if (products.length) {
        sections.push(`
            <section class="search-live-group">
                <h3>${escapeHtml(t("js.search.products"))}</h3>
                <div class="search-live-grid">
                    ${products.map((product) => renderLiveSearchProduct(product)).join("")}
                </div>
            </section>
        `);
    }

    resultsNode.hidden = false;
    resultsNode.innerHTML = sections.length
        ? sections.join("")
        : `<div class="search-live-empty">${escapeHtml(t("js.search.no_results", { query: normalizedQuery }))}</div>`;

}

async function performLiveSearch(root) {
    const state = getLiveSearchState(root);
    const input = root.querySelector("[data-live-search-input]");
    const resultsNode = root.querySelector("[data-live-search-results]");

    if (!input || !resultsNode) {
        return;
    }

    const query = normalizeSearchQuery(input.value);

    if (query.length < SEARCH_MIN_CHARS) {
        if (state.controller) {
            state.controller.abort();
            state.controller = null;
        }

        renderLiveSearchResults(root, { categories: [], products: [] }, query);
        return;
    }

    if (state.controller) {
        state.controller.abort();
    }

    const controller = new AbortController();
    state.controller = controller;

    resultsNode.hidden = false;
    resultsNode.innerHTML = `<div class="search-live-empty">${escapeHtml(t("js.search.loading"))}</div>`;

    try {
        const url = new URL(getShopConfig().searchUrl || "/api/search", window.location.origin);
        url.searchParams.set("q", query);

        const response = await fetch(url.toString(), {
            headers: {
                Accept: "application/json",
            },
            signal: controller.signal,
        });

        if (!response.ok) {
            throw new Error(`Search request failed with status ${response.status}`);
        }

        const payload = await response.json();

        if (!controller.signal.aborted) {
            renderLiveSearchResults(root, payload, query);
        }
    } catch (error) {
        if (error && error.name === "AbortError") {
            return;
        }

        resultsNode.hidden = false;
        resultsNode.innerHTML = `<div class="search-live-empty">${escapeHtml(t("js.search.unavailable"))}</div>`;
    } finally {
        if (state.controller === controller) {
            state.controller = null;
        }
    }
}

function scheduleLiveSearch(root) {
    const state = getLiveSearchState(root);

    if (state.timer) {
        window.clearTimeout(state.timer);
    }

    state.timer = window.setTimeout(() => {
        performLiveSearch(root);
    }, SEARCH_DEBOUNCE_MS);
}

function bindLiveSearch(root) {
    const input = root.querySelector("[data-live-search-input]");
    const resultsNode = root.querySelector("[data-live-search-results]");

    if (!input || !resultsNode) {
        return;
    }

    const state = getLiveSearchState(root);

    input.addEventListener("input", () => {
        const query = normalizeSearchQuery(input.value);

        if (query.length < SEARCH_MIN_CHARS) {
            if (state.controller) {
                state.controller.abort();
                state.controller = null;
            }

            renderLiveSearchResults(root, { categories: [], products: [] }, query);
            return;
        }

        scheduleLiveSearch(root);
    });

    input.addEventListener("focus", () => {
        if (normalizeSearchQuery(input.value).length >= SEARCH_MIN_CHARS && resultsNode.hidden) {
            scheduleLiveSearch(root);
        }
    });

    if (normalizeSearchQuery(input.value).length >= SEARCH_MIN_CHARS) {
        scheduleLiveSearch(root);
    }
}

function getCart() {
    try {
        const raw = JSON.parse(localStorage.getItem(CART_KEY));
        if (!Array.isArray(raw)) {
            return [];
        }

        return raw.map(normalizeItem);
    } catch {
        return [];
    }
}

function saveCart(cart) {
    localStorage.setItem(CART_KEY, JSON.stringify(cart.map(normalizeItem)));
    updateCartCount();
}

function ensureToastContainer() {
    let container = document.getElementById("toast-container");
    if (!container) {
        container = document.createElement("div");
        container.id = "toast-container";
        container.className = "toast-container";
        document.body.appendChild(container);
    }

    return container;
}

function notify(message, type = "success") {
    if (!document.body) {
        return;
    }

    const container = ensureToastContainer();
    const toast = document.createElement("div");
    toast.className = `toast toast-${type}`;
    toast.textContent = message;
    container.appendChild(toast);

    requestAnimationFrame(() => {
        toast.classList.add("is-visible");
    });

    window.setTimeout(() => {
        toast.classList.remove("is-visible");
        window.setTimeout(() => toast.remove(), 220);
    }, 2800);
}

function addToCart(id, name, price, image, stock = null) {
    const cart = getCart();
    const productId = Number(id);
    const productName = String(name || "");
    const productPrice = Number(price) || 0;
    const productStock = normalizeStock(stock);
    const existing = cart.find((item) => item.id === productId);

    if (existing) {
        if (productStock !== null && existing.quantity >= productStock) {
            notify(t("js.cart.max_quantity"), "error");
            return;
        }

        existing.quantity += 1;
        if (existing.stock === null && productStock !== null) {
            existing.stock = productStock;
        }
    } else {
        if (productStock === 0) {
            notify(t("js.cart.out_of_stock"), "error");
            return;
        }

        cart.push({
            id: productId,
            name: productName,
            price: productPrice,
            image: image || "",
            stock: productStock,
            quantity: 1,
        });
    }

    saveCart(cart);
    notify(t("js.cart.added", { name: productName }));
}

function updateCartCount() {
    const element = document.getElementById("cart-count");
    if (!element) {
        return;
    }

    const total = getCart().reduce((sum, item) => sum + item.quantity, 0);
    element.textContent = total;
}

function changeQuantity(id, delta) {
    const cart = getCart();
    const item = cart.find((entry) => entry.id === id);

    if (!item) {
        return;
    }

    if (delta > 0 && item.stock !== null && item.quantity >= item.stock) {
        notify(t("js.cart.max_quantity"), "error");
        return;
    }

    item.quantity += delta;

    if (item.quantity <= 0) {
        const index = cart.findIndex((entry) => entry.id === id);
        cart.splice(index, 1);
    }

    saveCart(cart);
    renderCart();
}

function removeFromCart(id) {
    const cart = getCart().filter((item) => item.id !== id);
    saveCart(cart);
    renderCart();
    notify(t("js.cart.removed"), "info");
}

function clearCart() {
    const cart = getCart();
    if (!cart.length) {
        notify(t("js.cart.empty_already"), "info");
        return;
    }

    if (!window.confirm(t("js.cart.clear_confirm"))) {
        return;
    }

    localStorage.removeItem(CART_KEY);
    updateCartCount();
    renderCart();
    notify(t("js.cart.cleared"), "info");
}

function renderCart() {
    const container = document.getElementById("cart-items");
    const totalElement = document.getElementById("cart-total");

    if (!container || !totalElement) {
        return;
    }

    const cart = getCart();

    if (cart.length === 0) {
        const productsUrl = getShopConfig().productsUrl || `${getShopConfig().indexUrl || "/"}#products`;
        container.innerHTML = `
            <div class="empty-state empty-state--compact">
                <h3>${escapeHtml(t("cart.empty.title"))}</h3>
                <p>${escapeHtml(t("cart.empty.body"))}</p>
                <a class="button-primary" href="${escapeHtml(productsUrl)}">${escapeHtml(t("cart.empty.button"))}</a>
            </div>
        `;
        totalElement.textContent = formatCurrency(0);
        return;
    }

    let total = 0;
    container.innerHTML = cart
        .map((item) => {
            const lineTotal = item.price * item.quantity;
            total += lineTotal;

            const stockLabel = item.stock === null
                ? ""
                : item.stock === 0
                    ? `<span class="cart-stock is-empty">${escapeHtml(t("js.cart.stock_out"))}</span>`
                    : `<span class="cart-stock">${escapeHtml(t("js.cart.stock_available_short", { count: item.stock }))}</span>`;

            return `
                <article class="cart-row">
                    <div class="cart-row-main">
                        <strong>${escapeHtml(item.name)}</strong>
                        <div class="cart-row-meta">
                            <span>${formatCurrency(item.price)} / ${escapeHtml(t("js.cart.unit"))}</span>
                            ${stockLabel}
                        </div>
                    </div>

                    <div class="quantity">
                        <button type="button" onclick="changeQuantity(${item.id}, -1)">-</button>
                        <strong>${item.quantity}</strong>
                        <button type="button" onclick="changeQuantity(${item.id}, 1)">+</button>
                    </div>

                    <strong>${formatCurrency(lineTotal)}</strong>

                    <button type="button" class="danger" onclick="removeFromCart(${item.id})">
                        ${escapeHtml(t("common.delete"))}
                    </button>
                </article>
            `;
        })
        .join("");

    totalElement.textContent = formatCurrency(total);
}

function bindCustomerFields() {
    const nameInput = document.getElementById("customer-name");
    const addressInput = document.getElementById("customer-address");

    if (nameInput) {
        nameInput.value = localStorage.getItem(CUSTOMER_NAME_KEY) || "";
        nameInput.addEventListener("input", () => {
            localStorage.setItem(CUSTOMER_NAME_KEY, nameInput.value.trim());
        });
    }

    if (addressInput) {
        addressInput.value = localStorage.getItem(CUSTOMER_ADDRESS_KEY) || "";
        addressInput.addEventListener("input", () => {
            localStorage.setItem(CUSTOMER_ADDRESS_KEY, addressInput.value.trim());
        });
    }
}

function sendOrderToWhatsApp() {
    const cart = getCart();

    if (!cart.length) {
        notify(t("js.cart.empty"), "error");
        return;
    }

    const name = document.getElementById("customer-name")?.value.trim() || "";
    const address = document.getElementById("customer-address")?.value.trim() || "";
    const shopName = getShopConfig().shopName || "MERCA FRUIT SEC";
    const phone = String(getShopConfig().whatsappNumber || DEFAULT_WHATSAPP).replace(/\D/g, "");

    if (name) {
        localStorage.setItem(CUSTOMER_NAME_KEY, name);
    }

    if (address) {
        localStorage.setItem(CUSTOMER_ADDRESS_KEY, address);
    }

    let total = 0;
    const lines = [t("js.cart.checkout_intro", { shop_name: shopName }), ""];

    cart.forEach((item) => {
        const lineTotal = item.price * item.quantity;
        total += lineTotal;
        lines.push(`- ${item.name} x ${item.quantity} : ${formatCurrency(lineTotal)}`);
    });

    lines.push("", t("js.cart.total", { total: formatCurrency(total) }));

    if (name) {
        lines.push("", t("js.cart.name", { name }));
    }

    if (address) {
        lines.push(t("js.cart.address", { address }));
    }

    lines.push("", t("js.cart.confirm"));

    const url = `https://wa.me/${phone}?text=${encodeURIComponent(lines.join("\n"))}`;
    window.open(url, "_blank", "noopener,noreferrer");
}

function escapeHtml(value) {
    return String(value)
        .replaceAll("&", "&amp;")
        .replaceAll("<", "&lt;")
        .replaceAll(">", "&gt;")
        .replaceAll('"', "&quot;")
        .replaceAll("'", "&#039;");
}

function setMobileMenuState(isOpen) {
    const nav = document.getElementById("main-nav");
    const button = document.querySelector(".menu-toggle");

    if (!nav || !button) {
        return;
    }

    nav.classList.toggle("open", isOpen);
    button.classList.toggle("is-open", isOpen);
    button.setAttribute("aria-expanded", String(isOpen));
    button.setAttribute("aria-label", isOpen ? t("js.menu.close") : t("js.menu.open"));
}

function toggleMobileMenu() {
    const nav = document.getElementById("main-nav");

    if (!nav) {
        return;
    }

    setMobileMenuState(!nav.classList.contains("open"));
}

function closeMobileMenu() {
    setMobileMenuState(false);
}

function clamp(value, min, max) {
    return Math.min(Math.max(value, min), max);
}

function loadQuickReturnPosition() {
    try {
        const raw = localStorage.getItem(QUICK_RETURN_POSITION_KEY);

        if (!raw) {
            return null;
        }

        const parsed = JSON.parse(raw);

        if (!parsed || typeof parsed.left !== "number" || typeof parsed.top !== "number") {
            return null;
        }

        return parsed;
    } catch {
        return null;
    }
}

function saveQuickReturnPosition(position) {
    try {
        localStorage.setItem(QUICK_RETURN_POSITION_KEY, JSON.stringify(position));
    } catch {
        // Ignore storage failures.
    }
}

function clearQuickReturnPosition() {
    try {
        localStorage.removeItem(QUICK_RETURN_POSITION_KEY);
    } catch {
        // Ignore storage failures.
    }
}

function applyQuickReturnPosition(button, position) {
    if (!position) {
        button.style.removeProperty("left");
        button.style.removeProperty("top");
        button.style.removeProperty("right");
        button.style.removeProperty("bottom");
        return;
    }

    const rect = button.getBoundingClientRect();
    const width = rect.width || button.offsetWidth || 150;
    const height = rect.height || button.offsetHeight || 64;
    const maxLeft = Math.max(12, window.innerWidth - width - 12);
    const maxTop = Math.max(12, window.innerHeight - height - 12);
    const left = clamp(position.left, 12, maxLeft);
    const top = clamp(position.top, 12, maxTop);

    button.style.left = `${left}px`;
    button.style.top = `${top}px`;
    button.style.right = "auto";
    button.style.bottom = "auto";
}

function resetQuickReturnPosition(button) {
    button.style.removeProperty("left");
    button.style.removeProperty("top");
    button.style.removeProperty("right");
    button.style.removeProperty("bottom");
    clearQuickReturnPosition();
}

function updateQuickReturnButton(button, stage) {
    const title = button.querySelector("[data-quick-return-title]");

    if (title) {
        title.textContent = stage === 0 ? t("js.quick_return.products") : t("js.quick_return.search");
    }
}

function scrollQuickReturnTarget(stage) {
    const productsSection = document.getElementById("products");
    const searchSection = document.getElementById("search");

    if (stage === 0 && productsSection) {
        productsSection.scrollIntoView({ behavior: "smooth", block: "center" });
        return true;
    }

    if (stage === 1 && searchSection) {
        searchSection.scrollIntoView({ behavior: "smooth", block: "start" });
        return true;
    }

    return false;
}

function bindQuickReturnButton() {
    const button = document.querySelector("[data-quick-return]");
    const productsSection = document.getElementById("products");
    const searchSection = document.getElementById("search");

    if (!button || !productsSection || !searchSection) {
        return;
    }

    let stage = 0;
    button.hidden = false;
    updateQuickReturnButton(button, stage);

    const savedPosition = loadQuickReturnPosition();

    if (savedPosition) {
        applyQuickReturnPosition(button, savedPosition);
    }

    button.addEventListener("pointerdown", (event) => {
        if (event.button !== undefined && event.button !== 0) {
            return;
        }

        quickReturnState.pointerId = event.pointerId;
        quickReturnState.dragging = false;
        quickReturnState.dragStarted = false;
        quickReturnState.suppressClick = false;
        quickReturnState.startX = event.clientX;
        quickReturnState.startY = event.clientY;

        const rect = button.getBoundingClientRect();
        quickReturnState.startLeft = rect.left;
        quickReturnState.startTop = rect.top;

        button.setPointerCapture?.(event.pointerId);
    });

    button.addEventListener("pointermove", (event) => {
        if (quickReturnState.pointerId !== event.pointerId) {
            return;
        }

        const deltaX = event.clientX - quickReturnState.startX;
        const deltaY = event.clientY - quickReturnState.startY;
        const distance = Math.hypot(deltaX, deltaY);

        if (!quickReturnState.dragStarted && distance < QUICK_RETURN_DRAG_THRESHOLD) {
            return;
        }

        if (!quickReturnState.dragStarted) {
            quickReturnState.dragStarted = true;
            quickReturnState.dragging = true;
            quickReturnState.suppressClick = true;
            button.classList.add("is-dragging");
        }

        applyQuickReturnPosition(button, {
            left: quickReturnState.startLeft + deltaX,
            top: quickReturnState.startTop + deltaY,
        });
    });

    const finishPointer = (event) => {
        if (quickReturnState.pointerId !== event.pointerId) {
            return;
        }

        if (quickReturnState.dragStarted) {
            const rect = button.getBoundingClientRect();
            saveQuickReturnPosition({
                left: rect.left,
                top: rect.top,
            });
            button.classList.remove("is-dragging");
        }

        quickReturnState.dragging = false;
        quickReturnState.dragStarted = false;
        quickReturnState.pointerId = null;

        window.setTimeout(() => {
            quickReturnState.suppressClick = false;
        }, 0);
    };

    button.addEventListener("pointerup", finishPointer);
    button.addEventListener("pointercancel", finishPointer);

    button.addEventListener("click", () => {
        if (quickReturnState.suppressClick) {
            return;
        }

        const moved = scrollQuickReturnTarget(stage);

        if (moved) {
            stage = stage === 0 ? 1 : 0;
            updateQuickReturnButton(button, stage);
        }
    });
}

function getProductModalElements() {
    const root = document.querySelector("[data-product-modal]");

    if (!root) {
        return null;
    }

    return {
        root,
        visual: root.querySelector("[data-product-modal-visual]"),
        image: root.querySelector("[data-product-modal-image]"),
        title: root.querySelector("[data-product-modal-title]"),
        category: root.querySelector("[data-product-modal-category]"),
        description: root.querySelector("[data-product-modal-description]"),
        closeButtons: root.querySelectorAll("[data-product-modal-close]"),
    };
}

function openProductModal({ name, category, description, image }) {
    const elements = getProductModalElements();

    if (!elements) {
        return;
    }

    const imageUrl = image ? buildStaticImageUrl(image) : "";

    if (elements.title) {
        elements.title.textContent = name || t("js.modal.product");
    }

    if (elements.category) {
        elements.category.textContent = category || "";
    }

    if (elements.description) {
        elements.description.textContent = description || t("js.modal.no_description");
    }

    if (elements.visual && elements.image) {
        if (imageUrl) {
            elements.image.src = imageUrl;
            elements.image.alt = name || t("js.modal.product");
            elements.visual.hidden = false;
        } else {
            elements.image.removeAttribute("src");
            elements.image.alt = "";
            elements.visual.hidden = true;
        }
    }

    elements.root.hidden = false;
    document.body.classList.add("modal-open");
}

function closeProductModal() {
    const elements = getProductModalElements();

    if (!elements) {
        return;
    }

    if (elements.image) {
        elements.image.removeAttribute("src");
        elements.image.alt = "";
    }

    if (elements.visual) {
        elements.visual.hidden = true;
    }

    elements.root.hidden = true;
    document.body.classList.remove("modal-open");
}

function bindProductModal() {
    const elements = getProductModalElements();

    if (!elements) {
        return;
    }

    elements.closeButtons.forEach((button) => {
        button.addEventListener("click", closeProductModal);
    });

    elements.root.addEventListener("click", (event) => {
        if (event.target === elements.root) {
            closeProductModal();
        }
    });

    document.addEventListener("keydown", (event) => {
        if (event.key === "Escape" && !elements.root.hidden) {
            closeProductModal();
        }
    });
}

function getShowcaseMarqueeState(root) {
    let state = showcaseMarqueeState.get(root);

    if (!state) {
        state = {
            animationFrame: null,
            cycleWidth: 0,
            dragging: false,
            ignoreScrollEventsUntil: 0,
            lastTimestamp: 0,
            pointerId: null,
            resumeAt: 0,
            startScrollLeft: 0,
            startX: 0,
            suppressClick: false,
            normalizing: false,
        };
        showcaseMarqueeState.set(root, state);
    }

    return state;
}

function cloneShowcaseGroup(group) {
    const clone = group.cloneNode(true);

    clone.setAttribute("aria-hidden", "true");
    clone.querySelectorAll("a, button").forEach((element) => {
        element.setAttribute("tabindex", "-1");
    });

    return clone;
}

function ensureShowcaseWidth(root, track, state) {
    const groups = Array.from(track.querySelectorAll(".showcase-group"));

    if (!groups.length) {
        return;
    }

    const cycleWidth = groups[0].getBoundingClientRect().width;

    if (!cycleWidth) {
        return;
    }

    state.cycleWidth = cycleWidth;

    const minimumWidth = root.clientWidth + cycleWidth * 2;
    const template = groups.find((group) => group.getAttribute("aria-hidden") === "true") || groups[groups.length - 1];

    while (track.scrollWidth < minimumWidth) {
        track.appendChild(cloneShowcaseGroup(template));
    }
}

function normalizeShowcaseScroll(root, state) {
    if (!state.cycleWidth) {
        return;
    }

    let nextScrollLeft = root.scrollLeft;

    while (nextScrollLeft >= state.cycleWidth) {
        nextScrollLeft -= state.cycleWidth;
    }

    while (nextScrollLeft < 0) {
        nextScrollLeft += state.cycleWidth;
    }

    if (nextScrollLeft !== root.scrollLeft) {
        state.normalizing = true;
        state.ignoreScrollEventsUntil = performance.now() + 80;
        root.scrollLeft = nextScrollLeft;
        window.requestAnimationFrame(() => {
            state.normalizing = false;
        });
    }
}

function bindShowcaseMarquee(root) {
    if (root.dataset.showcaseBound === "true") {
        return;
    }

    const track = root.querySelector(".showcase-track");

    if (!track) {
        return;
    }

    root.dataset.showcaseBound = "true";

    const state = getShowcaseMarqueeState(root);
    const reducedMotionQuery = window.matchMedia("(prefers-reduced-motion: reduce)");

    ensureShowcaseWidth(root, track, state);
    root.scrollLeft = 0;
    normalizeShowcaseScroll(root, state);

    const tick = (timestamp) => {
        if (state.animationFrame === null) {
            return;
        }

        const delta = state.lastTimestamp ? Math.min(40, timestamp - state.lastTimestamp) : 16;
        state.lastTimestamp = timestamp;

        if (!document.hidden && !state.dragging && !reducedMotionQuery.matches && timestamp >= state.resumeAt) {
            state.ignoreScrollEventsUntil = performance.now() + 80;
            root.scrollLeft += SHOWCASE_AUTO_SCROLL_SPEED * delta;
            normalizeShowcaseScroll(root, state);
        }

        state.animationFrame = window.requestAnimationFrame(tick);
    };

    state.animationFrame = window.requestAnimationFrame(tick);

    const pauseAutoScroll = (duration = 900) => {
        state.resumeAt = Math.max(state.resumeAt, performance.now() + duration);
    };

    root.addEventListener("pointerdown", (event) => {
        if (event.button !== 0) {
            return;
        }

        state.pointerId = event.pointerId;
        state.startX = event.clientX;
        state.startScrollLeft = root.scrollLeft;
        state.dragging = false;
        state.suppressClick = false;
        pauseAutoScroll(1200);
        root.setPointerCapture?.(event.pointerId);
    });

    root.addEventListener("pointermove", (event) => {
        if (state.pointerId !== event.pointerId) {
            return;
        }

        const deltaX = event.clientX - state.startX;

        if (!state.dragging && Math.abs(deltaX) < SHOWCASE_DRAG_THRESHOLD) {
            return;
        }

        if (!state.dragging) {
            state.dragging = true;
            state.suppressClick = true;
            root.classList.add("is-dragging");
        }

        root.scrollLeft = state.startScrollLeft - deltaX;
        normalizeShowcaseScroll(root, state);
    });

    const finishPointer = (event) => {
        if (state.pointerId !== event.pointerId) {
            return;
        }

        if (state.dragging) {
            normalizeShowcaseScroll(root, state);
        }

        state.dragging = false;
        state.pointerId = null;
        root.classList.remove("is-dragging");

        window.setTimeout(() => {
            state.suppressClick = false;
        }, 0);

        pauseAutoScroll(1200);
    };

    root.addEventListener("pointerup", finishPointer);
    root.addEventListener("pointercancel", finishPointer);

    root.addEventListener("scroll", () => {
        if (state.normalizing || state.dragging || performance.now() < state.ignoreScrollEventsUntil) {
            return;
        }

        pauseAutoScroll(900);
        normalizeShowcaseScroll(root, state);
    }, { passive: true });

    root.addEventListener("click", (event) => {
        if (!state.suppressClick) {
            return;
        }

        event.preventDefault();
        event.stopPropagation();
    }, true);

    window.addEventListener("resize", () => {
        ensureShowcaseWidth(root, track, state);
        normalizeShowcaseScroll(root, state);
    });
}

document.addEventListener("DOMContentLoaded", () => {
    updateCartCount();
    renderCart();
    bindCustomerFields();
    bindQuickReturnButton();
    bindProductModal();

    document.querySelectorAll(".showcase-marquee").forEach((root) => {
        bindShowcaseMarquee(root);
    });

    document.querySelectorAll("[data-live-search-root]").forEach((root) => {
        bindLiveSearch(root);
    });

    document.addEventListener("click", (event) => {
        if (!(event.target instanceof Element)) {
            return;
        }

        const button = event.target.closest("[data-cart-add]");

        if (!button) {
            return;
        }

        addToCart(
            button.dataset.productId,
            button.dataset.productName,
            button.dataset.productPrice,
            button.dataset.productImage,
            button.dataset.productStock
        );
    });

    document.addEventListener("click", (event) => {
        if (!(event.target instanceof Element)) {
            return;
        }

        const trigger = event.target.closest("[data-show-description]");

        if (!trigger) {
            return;
        }

        event.preventDefault();
        event.stopPropagation();

        openProductModal({
            name: trigger.dataset.productName,
            category: trigger.dataset.productCategory,
            description: trigger.dataset.productDescription,
            image: trigger.dataset.productImage,
        });
    });

    const nav = document.getElementById("main-nav");

    if (nav) {
        nav.querySelectorAll("a").forEach((link) => {
            link.addEventListener("click", closeMobileMenu);
        });
    }

    window.addEventListener("resize", () => {
        if (window.innerWidth > 900) {
            closeMobileMenu();
        }
    });
});
