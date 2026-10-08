
function openCartDrawer() {
    const backdrop = document.querySelector('[data-drawer-backdrop="cart"]');
    const panel = document.querySelector('[data-drawer-panel="cart"]');
    if (backdrop) backdrop.classList.add("is-open");
    if (panel) panel.classList.add("is-open");
    renderDrawerCart();
    document.body.style.overflow = "hidden";
}

function closeCartDrawer() {
    const backdrop = document.querySelector('[data-drawer-backdrop="cart"]');
    const panel = document.querySelector('[data-drawer-panel="cart"]');
    if (backdrop) backdrop.classList.remove("is-open");
    if (panel) panel.classList.remove("is-open");
    document.body.style.overflow = "";
}

function renderDrawerCart() {
    const container = document.getElementById("drawer-items");
    const totalElement = document.getElementById("drawer-total-val");
    const clearBtn = document.getElementById("drawer-clear-btn");
    if (!container || !totalElement) return;

    const cart = getCart();
    if (clearBtn) {
        clearBtn.hidden = cart.length === 0;
    }

    if (cart.length === 0) {
        container.innerHTML = `
            <div class="drawer-empty-state">
                <div style="font-size:2.8rem;margin-bottom:8px;">🛍️</div>
                <p><strong>${escapeHtml(t("cart.empty.title"))}</strong></p>
                <p style="font-size:0.84rem;color:var(--color-text-muted);">${escapeHtml(t("cart.empty.body"))}</p>
            </div>
        `;
        totalElement.textContent = formatCurrency(0);
        return;
    }

    let total = 0;
    const staticImagesUrl = getShopConfig().staticImagesUrl || "/static/images/";
    container.innerHTML = cart.map((item) => {
        const lineTotal = item.price * item.quantity;
        total += lineTotal;
        const imgSrc = item.image ? `${staticImagesUrl}${encodeURIComponent(item.image)}` : "";
        const imgHtml = imgSrc
            ? `<img class="drawer-item-img" src="${escapeHtml(imgSrc)}" alt="${escapeHtml(item.name)}">`
            : `<div class="drawer-item-img" style="display:flex;align-items:center;justify-content:center;background:#F3EFEA;color:#1E382B;font-weight:bold;">🌿</div>`;

        return `
            <div class="drawer-item-card">
                ${imgHtml}
                <div class="drawer-item-details">
                    <h4 class="drawer-item-title">${escapeHtml(item.name)}</h4>
                    ${item.weightLabel ? `<div class="drawer-item-weight">${escapeHtml(item.weightLabel)}</div>` : ""}
                    <div class="drawer-item-price">${formatCurrency(item.price)}</div>
                </div>
                <div class="drawer-item-qty">
                    <button type="button" class="drawer-qty-btn" data-cart-quantity data-product-id="${escapeHtml(item.id)}" data-product-weight-label="${escapeHtml(item.weightLabel)}" data-cart-delta="-1" aria-label="Diminuer la quantité">−</button>
                    <span class="drawer-qty-val">${item.quantity}</span>
                    <button type="button" class="drawer-qty-btn" data-cart-quantity data-product-id="${escapeHtml(item.id)}" data-product-weight-label="${escapeHtml(item.weightLabel)}" data-cart-delta="1" aria-label="Augmenter la quantité">+</button>
                </div>
                <button type="button" class="drawer-item-remove" data-cart-remove data-product-id="${escapeHtml(item.id)}" data-product-weight-label="${escapeHtml(item.weightLabel)}" title="Supprimer cet article" aria-label="Supprimer cet article">✕</button>
            </div>
        `;
    }).join("");

    totalElement.textContent = formatCurrency(total);
}

function checkoutFromDrawer() {
    const cart = getCart();
    if (!cart.length) {
        notify(t("js.cart.empty"), "info");
        return;
    }
    const shopConfig = getShopConfig();
    const whatsappNumber = shopConfig.whatsappNumber || DEFAULT_WHATSAPP;
    const shopName = shopConfig.shopName || "MERCA FRUIT SEC";

    let total = 0;
    const lines = [
        `Bonjour ${shopName}, je souhaite passer cette commande :`,
        ""
    ];
    cart.forEach((item) => {
        const lineTotal = item.price * item.quantity;
        total += lineTotal;
        const weight = item.weightLabel ? ` (${item.weightLabel})` : "";
        lines.push(`• ${item.name}${weight} x${item.quantity} = ${lineTotal.toFixed(2)} DH`);
    });
    lines.push("");
    lines.push(`Total : ${total.toFixed(2)} DH`);
    lines.push("Merci de confirmer ma commande.");

    const message = encodeURIComponent(lines.join("\n"));
    window.open(`https://wa.me/${whatsappNumber}?text=${message}`, "_blank");
}

let currentCatModalProducts = [];
let catModalRequest = null;

function openCategoryModal(categoryId, categoryName, categoryCount) {
    const backdrop = document.querySelector('[data-cat-modal-backdrop]');
    const panel = document.querySelector('[data-cat-modal-panel]');
    const titleEl = document.getElementById('cat-modal-name');
    const badgeEl = document.getElementById('cat-modal-badge');
    const countEl = document.getElementById('cat-modal-count-sub');
    const searchInput = document.getElementById('cat-modal-search-input');
    const bodyEl = document.getElementById('cat-modal-body');

    if (!backdrop || !panel) return;

    catModalRequest?.abort();
    const request = new AbortController();
    catModalRequest = request;
    currentCatModalProducts = [];
    const isCurrentRequest = () => catModalRequest === request
        && !request.signal.aborted && panel.classList.contains('is-open');

    if (titleEl) titleEl.textContent = categoryName || "Rayon";
    if (badgeEl) badgeEl.textContent = "Rayon";
    if (countEl) countEl.textContent = categoryCount ? `${categoryCount} articles` : "";
    if (searchInput) {
        searchInput.value = "";
        searchInput.disabled = true;
    }

    backdrop.classList.add('is-open');
    panel.classList.add('is-open');
    document.body.style.overflow = "hidden";

    if (bodyEl) {
        bodyEl.innerHTML = `
            <div class="cat-modal-loading">
                <div class="cat-modal-spinner"></div>
                <span>${escapeHtml(t("category_modal.loading"))}</span>
            </div>
        `;
    }

    fetch(`/api/category/${categoryId}/products`, { signal: request.signal })
        .then(res => {
            if (!res.ok) throw new Error(`Category products request failed: ${res.status}`);
            return res.json();
        })
        .then(data => {
            // An aborted request may already be decoding JSON: only the last click may render.
            if (!isCurrentRequest()) return;
            currentCatModalProducts = data.products || [];
            if (countEl) {
                const count = currentCatModalProducts.length;
                countEl.textContent = t("category_modal.products_count", { count, suffix: pluralSuffix(count) });
            }
            renderCatModalProducts(currentCatModalProducts);
        })
        .catch(err => {
            if (err.name === "AbortError" || !isCurrentRequest()) return;
            console.error("Failed to load category products", err);
            if (bodyEl) {
                bodyEl.innerHTML = `
                    <div class="cat-modal-empty">
                        <p>${escapeHtml(t("category_modal.no_products"))}</p>
                    </div>
                `;
            }
        })
        .finally(() => {
            if (!isCurrentRequest()) return;
            catModalRequest = null;
            if (searchInput) searchInput.disabled = false;
        });
}

function closeCategoryModal() {
    catModalRequest?.abort();
    catModalRequest = null;
    currentCatModalProducts = [];
    const searchInput = document.getElementById('cat-modal-search-input');
    if (searchInput) searchInput.disabled = false;
    const backdrop = document.querySelector('[data-cat-modal-backdrop]');
    const panel = document.querySelector('[data-cat-modal-panel]');
    if (backdrop) backdrop.classList.remove('is-open');
    if (panel) panel.classList.remove('is-open');
    document.body.style.overflow = "";
}

function renderCatModalProducts(productsList) {
    const bodyEl = document.getElementById('cat-modal-body');
    if (!bodyEl) return;

    if (!productsList || productsList.length === 0) {
        bodyEl.innerHTML = `
            <div class="cat-modal-empty">
                <div style="font-size:2rem; margin-bottom:6px;">🍃</div>
                <p><strong>${escapeHtml(t("category_modal.no_search_results"))}</strong></p>
            </div>
        `;
        return;
    }

    const staticImagesUrl = getShopConfig().staticImagesUrl || "/static/images/";

    bodyEl.innerHTML = `
        <div class="cat-modal-grid">
            ${productsList.map((prod, idx) => {
                const weightOptions = prod.weight_options || [];
                const firstWeight = weightOptions.length > 0 ? weightOptions[0] : null;
                const defaultPrice = firstWeight ? firstWeight.price : prod.price;
                const defaultWeightLabel = firstWeight ? firstWeight.label : "";
                
                const imgSrc = prod.image ? `${staticImagesUrl}${encodeURIComponent(prod.image)}` : "";
                const imgMarkup = imgSrc
                    ? `<img src="${escapeHtml(imgSrc)}" alt="${escapeHtml(prod.name)}" loading="lazy">`
                    : `<div class="cat-item-img-fallback">🌿</div>`;

                const chipsMarkup = weightOptions.length > 1
                    ? `<div class="cat-item-weight-chips">
                        ${weightOptions.map((opt, oIdx) => `
                            <button type="button" class="cat-weight-chip ${oIdx === 0 ? 'is-selected' : ''}" 
                                data-cat-weight-label="${escapeHtml(opt.label)}" 
                                data-cat-weight-price="${escapeHtml(opt.price)}">
                                ${escapeHtml(opt.label)}
                            </button>
                        `).join("")}
                       </div>`
                    : (firstWeight ? `<span class="cat-item-single-weight">${escapeHtml(firstWeight.label)}</span>` : '');

                return `
                    <div class="cat-modal-item-card" data-product-id="${prod.id}">
                        <div class="cat-item-thumb" data-cat-detail-trigger data-cat-detail-idx="${idx}" data-prod-id="${prod.id}" role="button" tabindex="0" title="Agrandir la photo">
                            ${imgMarkup}
                            <span class="cat-thumb-zoom-badge" aria-label="Agrandir">🔍</span>
                        </div>
                        <div class="cat-item-content">
                            <h4 class="cat-item-title" data-cat-detail-trigger data-cat-detail-idx="${idx}" data-prod-id="${prod.id}" role="button" tabindex="0" title="Voir les détails">${escapeHtml(prod.name)}</h4>
                            ${prod.description ? `<p class="cat-item-desc" data-cat-detail-trigger data-cat-detail-idx="${idx}" data-prod-id="${prod.id}">${escapeHtml(prod.description)}</p>` : ''}
                            ${chipsMarkup}
                            <div class="cat-item-footer">
                                <span class="cat-item-price" data-cat-price-display>${formatCurrency(defaultPrice)}</span>
                                <button type="button" class="cat-item-add-btn" 
                                    data-cat-add-btn
                                    data-prod-id="${prod.id}"
                                    data-prod-name="${escapeHtml(prod.name)}"
                                    data-prod-price="${defaultPrice}"
                                    data-prod-image="${escapeHtml(prod.image || '')}"
                                    data-prod-weight="${escapeHtml(defaultWeightLabel)}">
                                    + ${escapeHtml(t("home.product.add"))}
                                </button>
                            </div>
                        </div>
                    </div>
                `;
            }).join("")}
        </div>
    `;
}

const CART_KEY = "merca_fruit_sec_cart";
const CUSTOMER_NAME_KEY = "merca_fruit_sec_customer_name";
const CUSTOMER_ADDRESS_KEY = "merca_fruit_sec_customer_address";
const DEFAULT_WHATSAPP = "212622135964";
const SEARCH_MIN_CHARS = 2;
const SEARCH_DEBOUNCE_MS = 220;
const QUICK_RETURN_POSITION_KEY = "merca_fruit_sec_quick_return_position";
const QUICK_RETURN_DRAG_THRESHOLD = 6;
const liveSearchState = new WeakMap();
const DEFAULT_UI_STRINGS = {
    "js.search.loading": "Recherche en cours...",
    "js.search.unavailable": "La recherche est temporairement indisponible.",
    "js.search.no_results": "Aucun resultat pour {query}. Essayez un autre mot-cle.",
    "js.search.categories": "Categories",
    "js.search.products": "Produits",
    "js.search.category_count": "{count} produit{suffix}",
    "js.cart.max_quantity": "Quantite maximale atteinte pour ce produit.",
    "js.cart.added": "{name} a ete ajoute au panier.",
    "js.cart.removed": "Produit supprime du panier.",
    "js.cart.empty": "Votre panier est vide.",
    "js.cart.empty_already": "Votre panier est deja vide.",
    "js.cart.clear_confirm": "Vider le panier ?",
    "js.cart.cleared": "Panier vide.",
    "js.cart.checkout_unavailable": "La commande n'a pas pu etre verifiee. Reessayez dans un instant.",
    "js.cart.checkout_intro": "Bonjour {shop_name}, je souhaite passer cette commande :",
    "js.cart.total": "Total : {total}",
    "js.cart.name": "Nom : {name}",
    "js.cart.address": "Adresse : {address}",
    "js.cart.confirm": "Merci de confirmer ma commande.",
    "js.cart.unit": "unite",
    "js.cart.explore": "Explorer le catalogue",
    "home.product.weight_select": "Choisir un poids",
    "admin.product.weight_label_placeholder": "Poids : 100 g",
    "admin.product.weight_price_placeholder": "Prix : 15 DH",
    "admin.product.remove_weight_option": "Supprimer",
    "js.menu.open": "Ouvrir le menu",
    "js.menu.close": "Fermer le menu",
    "js.quick_return.products": "Produits",
    "js.quick_return.search": "Recherche",
    "js.modal.product": "Produit",
    "js.modal.no_description": "Aucune description disponible.",
    "js.modal.close": "Fermer",
    "home.product.add": "Ajouter au panier",
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
let deferredInstallPrompt = null;

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

function bindInstalledMobileNavigation() {
    if (!document.querySelector(".mobile-bottom-nav")) {
        return;
    }

    const isMobileDevice = /Android|iPhone|iPad|iPod/i.test(navigator.userAgent)
        || (navigator.platform === "MacIntel" && navigator.maxTouchPoints > 1);
    const standaloneMode = window.matchMedia("(display-mode: standalone)");
    const updateNavigation = () => {
        const isInstalledApp = standaloneMode.matches || navigator.standalone === true;
        document.body.classList.toggle("is-installed-mobile-app", isMobileDevice && isInstalledApp);
    };

    updateNavigation();
    standaloneMode.addEventListener?.("change", updateNavigation);
    window.addEventListener("pageshow", updateNavigation);
}

function bindPwaInstall() {
    const installButton = document.querySelector("[data-pwa-install]");

    if (!("serviceWorker" in navigator)) {
        return;
    }

    window.addEventListener("load", () => {
        const serviceWorkerUrl = getShopConfig().pwaServiceWorkerUrl || "/service-worker.js";
        navigator.serviceWorker.register(serviceWorkerUrl).then((reg) => {
            reg.update();
        }).catch((error) => {
            console.warn("Unable to register the service worker:", error);
        });
    });

    window.addEventListener("beforeinstallprompt", (event) => {
        event.preventDefault();
        deferredInstallPrompt = event;

        if (installButton) {
            installButton.hidden = false;
        }
    });

    installButton?.addEventListener("click", async () => {
        if (!deferredInstallPrompt) {
            return;
        }

        deferredInstallPrompt.prompt();
        await deferredInstallPrompt.userChoice;
        deferredInstallPrompt = null;
        installButton.hidden = true;
    });

    window.addEventListener("appinstalled", () => {
        deferredInstallPrompt = null;
        if (installButton) {
            installButton.hidden = true;
        }
    });
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

function normalizeWeightLabel(label) {
    return String(label || "").trim().replace(/\s+/g, " ");
}

function normalizeWeightOptions(options) {
    if (!Array.isArray(options)) {
        return [];
    }

    return options
        .map((option) => {
            const label = normalizeWeightLabel(option?.label);
            const price = Number(option?.price);

            if (!label || !Number.isFinite(price) || price < 0) {
                return null;
            }

            return { label, price };
        })
        .filter(Boolean);
}

function normalizeItem(item) {
    return {
        id: Number(item.id),
        name: String(item.name || ""),
        price: Number(item.price) || 0,
        image: item.image || "",
        weightLabel: normalizeWeightLabel(item.weightLabel || item.weight_label),
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

function getSelectedWeightDetails(root) {
    const select = root?.querySelector("[data-product-weight-select]");

    if (!select) {
        return null;
    }

    const option = select.selectedOptions?.[0];
    if (!option) {
        return null;
    }

    const price = Number(option.dataset.price);
    return {
        label: normalizeWeightLabel(option.value),
        price: Number.isFinite(price) && price >= 0 ? price : 0,
    };
}

function updateProductWeightSelection(root) {
    const selected = getSelectedWeightDetails(root);

    if (!selected) {
        return;
    }

    const addButton = root.querySelector("[data-cart-add]");
    const priceDisplay = root.querySelector("[data-product-price-display]");

    if (addButton) {
        addButton.dataset.productPrice = String(selected.price);
        addButton.dataset.productWeightLabel = selected.label;
    }

    if (priceDisplay) {
        priceDisplay.textContent = formatCurrency(selected.price);
    }
}

function renderWeightSelect(options) {
    const weightOptions = normalizeWeightOptions(options);

    if (!weightOptions.length) {
        return "";
    }

    return `
        <select class="product-weight-select" data-product-weight-select aria-label="${escapeHtml(t("home.product.weight_select"))}">
            ${weightOptions.map((option, index) => `
                <option
                    value="${escapeHtml(option.label)}"
                    data-price="${escapeHtml(option.price)}"
                    ${index === 0 ? "selected" : ""}
                >
                    ${escapeHtml(option.label)} - ${escapeHtml(formatCurrency(option.price))}
                </option>
            `).join("")}
        </select>
    `;
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
    const weightOptions = normalizeWeightOptions(product.weight_options);
    const selectedWeightOption = weightOptions[0] || null;
    const displayPrice = selectedWeightOption ? selectedWeightOption.price : Number(product.display_price ?? product.price) || 0;
    const imageMarkup = product.image
        ? `<img src="${escapeHtml(buildStaticImageUrl(product.image))}" alt="">`
        : `<div class="search-live-product-fallback">MF</div>`;
    const weightSelect = renderWeightSelect(weightOptions);

    const encodedWeights = escapeHtml(JSON.stringify(weightOptions));
    return `
        <article class="search-live-product" data-product-id="${escapeHtml(product.id)}">
            <div class="search-live-product-media"
                data-show-description
                data-product-id="${escapeHtml(product.id)}"
                data-product-name="${escapeHtml(product.name || '')}"
                data-product-category="${escapeHtml(product.category_name || '')}"
                data-product-description="${escapeHtml(product.description || '')}"
                data-product-image="${escapeHtml(product.image || '')}"
                data-product-price="${escapeHtml(displayPrice)}"
                data-product-weights="${encodedWeights}"
                role="button"
                tabindex="0"
                style="cursor: pointer;"
                title="Agrandir la photo"
            >
                ${imageMarkup}
                <span class="cat-thumb-zoom-badge" aria-label="Agrandir">🔍</span>
            </div>
            <div class="search-live-product-body">
                <small>${escapeHtml(product.category_name || t("home.product.category_empty"))}</small>
                <strong
                    data-show-description
                    data-product-id="${escapeHtml(product.id)}"
                    data-product-name="${escapeHtml(product.name || '')}"
                    data-product-category="${escapeHtml(product.category_name || '')}"
                    data-product-description="${escapeHtml(product.description || '')}"
                    data-product-image="${escapeHtml(product.image || '')}"
                    data-product-price="${escapeHtml(displayPrice)}"
                    data-product-weights="${encodedWeights}"
                    style="cursor: pointer;"
                    title="Voir les détails"
                >${escapeHtml(product.name || "")}</strong>
                <span>
                    <span data-product-price-display>${escapeHtml(formatCurrency(displayPrice))}</span>
                </span>
                ${weightSelect}
            </div>
            <button
                type="button"
                class="button-primary"
                data-cart-add
                data-product-id="${escapeHtml(product.id)}"
                data-product-name="${escapeHtml(product.name || "")}"
                data-product-price="${escapeHtml(displayPrice)}"
                data-product-image="${escapeHtml(product.image || "")}"
                data-product-weight-label="${escapeHtml(selectedWeightOption?.label || "")}"
            >
                ${t("home.product.add")}
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
    toast.className = `toast toast-${type} toast-pill toast-pill-${type}`;

    let icon = "✓";
    if (type === "error") icon = "✕";
    if (type === "info") icon = "🌿";

    toast.innerHTML = `
        <span class="toast-pill-badge">${icon}</span>
        <span class="toast-pill-text">${escapeHtml(message)}</span>
    `;

    toast.addEventListener("click", () => {
        toast.classList.remove("is-visible");
        setTimeout(() => toast.remove(), 250);
    });

    container.appendChild(toast);

    requestAnimationFrame(() => {
        toast.classList.add("is-visible");
    });

    window.setTimeout(() => {
        toast.classList.remove("is-visible");
        window.setTimeout(() => toast.remove(), 250);
    }, 2500);
}

function cartItemsMatch(item, productId, weightLabel = "") {
    return item.id === Number(productId) && item.weightLabel === normalizeWeightLabel(weightLabel);
}

function addToCart(id, name, price, image, weightLabel = "") {
    const cart = getCart();
    const productId = Number(id);
    const productName = String(name || "");
    const productPrice = Number(price) || 0;
    const productWeightLabel = normalizeWeightLabel(weightLabel);
    const existing = cart.find((item) => cartItemsMatch(item, productId, productWeightLabel));

    if (existing) {
        existing.quantity += 1;
        existing.price = productPrice;
    } else {
        cart.push({
            id: productId,
            name: productName,
            price: productPrice,
            image: image || "",
            weightLabel: productWeightLabel,
            quantity: 1,
        });
    }

    saveCart(cart);
    updateCartCount();
    renderCart();
    renderDrawerCart();
    notify(t("js.cart.added", { name: productName }));
    // Do not force-open drawer: let the customer browse freely!
    updateFloatingCartReminder();
}

function updateFloatingCartReminder() {
    const bar = document.getElementById("floating-cart-bar");
    if (!bar) return;
    const cart = getCart();
    const totalCount = cart.reduce((sum, item) => sum + item.quantity, 0);
    const totalAmount = cart.reduce((sum, item) => sum + (item.price * item.quantity), 0);

    const badgeEl = document.getElementById("floating-cart-badge");
    const totalEl = document.getElementById("floating-cart-total");

    if (totalCount > 0) {
        if (badgeEl) badgeEl.textContent = totalCount;
        if (totalEl) {
            const itemWord = totalCount === 1 ? "article" : "articles";
            totalEl.textContent = `${totalCount} ${itemWord} • ${formatCurrency(totalAmount)}`;
        }
        bar.hidden = false;
        bar.classList.add("is-visible");
    } else {
        bar.classList.remove("is-visible");
        bar.hidden = true;
    }
}

function updateCartCount() {
    const total = getCart().reduce((sum, item) => sum + item.quantity, 0);
    const element = document.getElementById("cart-count");
    if (element) {
        element.textContent = total;
    }
    const mobileElement = document.getElementById("mobile-cart-count");
    if (mobileElement) {
        mobileElement.textContent = total;
    }
    updateFloatingCartReminder();
}

function changeQuantity(id, delta, weightLabel = "") {
    const cart = getCart();
    const item = cart.find((entry) => cartItemsMatch(entry, id, weightLabel));

    if (!item) {
        return;
    }

    item.quantity += delta;

    if (item.quantity <= 0) {
        const index = cart.findIndex((entry) => cartItemsMatch(entry, id, weightLabel));
        cart.splice(index, 1);
    }

    saveCart(cart);
    renderCart();
    renderDrawerCart();
}

function removeFromCart(id, weightLabel = "") {
    const cart = getCart().filter((item) => !cartItemsMatch(item, id, weightLabel));
    saveCart(cart);
    renderCart();
    renderDrawerCart();
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
    renderDrawerCart();
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

            const weightLabel = item.weightLabel
                ? `<span class="cart-weight">${escapeHtml(item.weightLabel)}</span>`
                : "";

            return `
                <article class="cart-row">
                    <div class="cart-row-main">
                        <strong>${escapeHtml(item.name)}</strong>
                        <div class="cart-row-meta">
                            ${weightLabel}
                            <span>${formatCurrency(item.price)} / ${escapeHtml(t("js.cart.unit"))}</span>
                        </div>
                    </div>

                    <div class="quantity">
                        <button
                            type="button"
                            data-cart-quantity
                            data-product-id="${escapeHtml(item.id)}"
                            data-product-weight-label="${escapeHtml(item.weightLabel)}"
                            data-cart-delta="-1"
                        >-</button>
                        <strong>${item.quantity}</strong>
                        <button
                            type="button"
                            data-cart-quantity
                            data-product-id="${escapeHtml(item.id)}"
                            data-product-weight-label="${escapeHtml(item.weightLabel)}"
                            data-cart-delta="1"
                        >+</button>
                    </div>

                    <strong>${formatCurrency(lineTotal)}</strong>

                    <button
                        type="button"
                        class="danger"
                        data-cart-remove
                        data-product-id="${escapeHtml(item.id)}"
                        data-product-weight-label="${escapeHtml(item.weightLabel)}"
                    >
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

async function sendOrderToWhatsApp() {
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

    let order;

    try {
        const response = await fetch(getShopConfig().checkoutUrl || "/api/checkout", {
            method: "POST",
            headers: { "Content-Type": "application/x-www-form-urlencoded;charset=UTF-8" },
            body: new URLSearchParams({
                items: JSON.stringify(cart.map((item) => ({
                    id: item.id,
                    quantity: item.quantity,
                    weight_label: item.weightLabel,
                }))),
                _csrf_token: getShopConfig().csrfToken || "",
            }),
        });

        if (!response.ok) {
            throw new Error(`Checkout validation failed: ${response.status}`);
        }

        order = await response.json();
    } catch (error) {
        console.warn("Unable to validate the order:", error);
        notify(t("js.cart.checkout_unavailable"), "error");
        return;
    }

    if (!Array.isArray(order.items) || order.items.length === 0) {
        notify(t("js.cart.empty"), "error");
        return;
    }

    const lines = [t("js.cart.checkout_intro", { shop_name: shopName }), ""];

    order.items.forEach((item) => {
        const lineTotal = item.price * item.quantity;
        const weightLabel = item.weight_label ? ` (${item.weight_label})` : "";
        lines.push(`- ${item.name}${weightLabel} x ${item.quantity} : ${formatCurrency(lineTotal)}`);
    });

    lines.push("", t("js.cart.total", { total: formatCurrency(order.total) }));

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

function bindAdminRealtimeFilter(root) {
    const input = root.querySelector("[data-admin-realtime-search]");
    const emptyState = root.querySelector("[data-admin-filter-empty]");
    const list = root.parentElement?.querySelector("[data-admin-filter-list]");

    if (!input || !list) {
        return;
    }

    input.addEventListener("input", () => {
        const query = normalizeSearchQuery(input.value).toLocaleLowerCase(getCurrentLanguage());
        let visibleCount = 0;

        list.querySelectorAll("[data-admin-filter-item]").forEach((item) => {
            const text = String(item.dataset.adminFilterText || "").toLocaleLowerCase(getCurrentLanguage());
            const matches = !query || text.includes(query);
            item.hidden = !matches;
            visibleCount += Number(matches);
        });

        if (emptyState) {
            emptyState.hidden = visibleCount > 0 || !query;
        }
    });
}

function bindAdminCategoryModal() {
    const dialog = document.querySelector("[data-admin-category-modal]");
    if (!dialog || typeof dialog.showModal !== "function") {
        return;
    }

    const title = dialog.querySelector("#admin-category-modal-title");
    const count = dialog.querySelector("[data-admin-category-count]");
    const content = dialog.querySelector("[data-admin-category-content]");
    let controller = null;
    let previousOverflow = "";
    let opener = null;
    let modalActive = false;

    dialog.addEventListener("close", () => {
        // A queued close event may belong to the previous opening.
        if (dialog.open || !modalActive) return;
        modalActive = false;
        controller?.abort();
        controller = null;
        document.body.style.overflow = previousOverflow;
        opener?.focus();
    });

    dialog.addEventListener("click", (event) => {
        if (event.target.closest("[data-admin-category-close]")) {
            dialog.close();
        } else if (event.target === dialog) {
            const rect = dialog.getBoundingClientRect();
            if (event.clientX < rect.left || event.clientX > rect.right
                || event.clientY < rect.top || event.clientY > rect.bottom) {
                dialog.close();
            }
        }
    });

    document.addEventListener("click", async (event) => {
        if (event.defaultPrevented || event.button !== 0 || event.ctrlKey
            || event.metaKey || event.shiftKey || event.altKey
            || !(event.target instanceof Element)) {
            return;
        }
        const link = event.target.closest("[data-admin-category-open]");
        if (!link) {
            return;
        }

        event.preventDefault();
        opener = link;
        dialog.dataset.categoryId = new URL(link.href).searchParams.get("category");
        dialog.querySelector("[data-admin-product-notice]")?.remove();
        const addButton = dialog.querySelector("[data-admin-open-add-product]");
        if (addButton) {
            addButton.dataset.preselectCategory = dialog.dataset.categoryId;
            addButton.hidden = true;
        }
        title.textContent = link.dataset.categoryName;
        count.textContent = t("admin.category.edit_subtitle", { count: link.dataset.categoryCount });
        content.innerHTML = `<p class="admin-category-modal-message" role="status">${escapeHtml(t("category_modal.loading"))}</p>`;
        controller?.abort();
        const request = new AbortController();
        controller = request;
        if (!dialog.open) {
            if (!modalActive) previousOverflow = document.body.style.overflow;
            modalActive = true;
            dialog.showModal();
            document.body.style.overflow = "hidden";
        }

        try {
            const response = await fetch(link.href, { signal: request.signal });
            if (response.redirected) {
                window.location.assign(response.url);
                return;
            }
            if (!response.ok) {
                throw new Error("Category products request failed");
            }
            const page = new DOMParser().parseFromString(await response.text(), "text/html");
            if (request.signal.aborted || !dialog.open) {
                return;
            }
            const panel = page.querySelector(".admin-panel--product-view");
            const search = panel?.querySelector("[data-admin-filter-root]");
            const list = panel?.querySelector(".admin-products[data-admin-filter-list]");
            if (!search || !list) {
                throw new Error("Category products list missing");
            }
            content.replaceChildren(search, list);
            if (addButton) addButton.hidden = false;
            count.textContent = t("admin.category.edit_subtitle", {
                count: list.querySelectorAll("[data-admin-filter-item]").length,
            });
            bindAdminRealtimeFilter(search);
        } catch (error) {
            if (error.name !== "AbortError" && controller === request && dialog.open) {
                content.innerHTML = `<p class="admin-category-modal-message" role="alert">${escapeHtml(t("admin.products.load_error"))}</p>`;
            }
        }
    });
}

function bindAdminAccountsModal() {
    const dialog = document.querySelector("[data-admin-accounts-modal]");
    if (!dialog || typeof dialog.showModal !== "function") return;

    document.body.append(dialog);
    const content = dialog.querySelector("[data-admin-accounts-content]");
    const accountsUrl = new URL(dialog.dataset.url, location.href);
    let opener = null;
    let previousOverflow = "";
    let loadingRequest = null;
    let requestId = 0;
    let saving = false;

    function openModal() {
        if (dialog.open) return;
        document.getElementById("main-nav")?.classList.remove("is-open");
        document.querySelector(".menu-toggle")?.setAttribute("aria-expanded", "false");
        document.body.classList.remove("menu-open");
        previousOverflow = document.body.style.overflow;
        dialog.showModal();
        document.body.style.overflow = "hidden";
    }

    function showError(key) {
        content.querySelector("[data-admin-accounts-error]")?.remove();
        const message = document.createElement("p");
        message.className = "flash error";
        message.dataset.adminAccountsError = "";
        message.setAttribute("role", "alert");
        message.textContent = t(key);
        content.prepend(message);
        content.scrollTop = 0;
    }

    async function showResponse(response, id) {
        if (id !== requestId || !dialog.open) return;
        // A POST redirects back to the accounts list; an expired session redirects to login.
        if (response.redirected && new URL(response.url).pathname !== accountsUrl.pathname) {
            window.location.assign(response.url);
            return;
        }
        if (!response.ok) throw new Error("Admin accounts request failed");
        const page = new DOMParser().parseFromString(await response.text(), "text/html");
        const body = page.querySelector("[data-admin-accounts-content]");
        if (!body) throw new Error("Admin accounts content missing");
        if (id !== requestId || !dialog.open) return;
        content.replaceChildren(...body.childNodes);
        content.scrollTop = 0;
        const message = content.querySelector(".flash");
        if (message) {
            message.tabIndex = -1;
            message.focus({ preventScroll: true });
        }
    }

    dialog.addEventListener("close", () => {
        requestId++;
        loadingRequest?.abort();
        document.body.style.overflow = previousOverflow;
        if (dialog.dataset.returnUrl) {
            window.location.replace(dialog.dataset.returnUrl);
            return;
        }
        const menu = document.querySelector(".menu-toggle");
        (menu && getComputedStyle(menu).display !== "none" ? menu : opener)?.focus();
    });

    dialog.addEventListener("click", (event) => {
        if (event.target.closest("[data-admin-accounts-close]")) {
            dialog.close();
        } else if (event.target === dialog) {
            const rect = dialog.getBoundingClientRect();
            if (event.clientX < rect.left || event.clientX > rect.right
                || event.clientY < rect.top || event.clientY > rect.bottom) dialog.close();
        }
    });

    document.addEventListener("click", async (event) => {
        if (event.defaultPrevented || event.button !== 0 || event.ctrlKey || event.metaKey
            || event.shiftKey || event.altKey || !(event.target instanceof Element)) return;
        const link = event.target.closest("[data-admin-open-accounts]");
        if (!link) return;
        event.preventDefault();
        opener = link;
        loadingRequest?.abort();
        loadingRequest = new AbortController();
        const id = ++requestId;
        content.innerHTML = `<p class="admin-accounts-empty" role="status">${escapeHtml(t("common.loading"))}</p>`;
        openModal();
        try {
            await showResponse(await fetch(link.href, { signal: loadingRequest.signal }), id);
        } catch (error) {
            if (error.name !== "AbortError" && id === requestId && dialog.open) {
                content.replaceChildren();
                showError("admin.admins.load_error");
            }
        }
    });

    dialog.addEventListener("submit", async (event) => {
        if (event.defaultPrevented || !(event.target instanceof HTMLFormElement)) return;
        event.preventDefault();
        const form = event.target;
        if (saving || !form.reportValidity()) return;
        saving = true;
        loadingRequest?.abort();
        const id = ++requestId;
        const buttons = Array.from(dialog.querySelectorAll("button[type=submit]"));
        buttons.forEach(button => { button.disabled = true; });
        content.setAttribute("aria-busy", "true");
        try {
            await showResponse(await fetch(form.getAttribute("action"), {
                method: "POST",
                body: new FormData(form),
            }), id);
        } catch (error) {
            if (id === requestId && dialog.open) showError("admin.admins.save_error");
        } finally {
            saving = false;
            buttons.forEach(button => { button.disabled = false; });
            content.removeAttribute("aria-busy");
        }
    });

    if (dialog.dataset.autoOpen === "true") {
        dialog.removeAttribute("open");
        openModal();
    }
}

function bindAdminAddProductModal() {
    const dialog = document.querySelector("[data-admin-add-product-modal]");
    if (!dialog || typeof dialog.showModal !== "function") {
        return;
    }

    const form = dialog.querySelector("#admin-add-product-form");
    const nameInput = dialog.querySelector("#admin-product-name-input");
    const categorySelect = dialog.querySelector("#admin-product-category-select");
    const fileInput = dialog.querySelector("[data-file-input]");
    const fileDropzone = dialog.querySelector("[data-file-dropzone]");
    const previewBox = dialog.querySelector("[data-image-preview]");
    const previewImg = dialog.querySelector("[data-preview-img]");
    const previewName = dialog.querySelector("[data-preview-name]");
    const previewClear = dialog.querySelector("[data-preview-clear]");

    let previousOverflow = "";
    let opener = null;

    function openModal(preselectedCategoryId = null) {
        if (dialog.open) return;
        previousOverflow = document.body.style.overflow;

        // Fermer le menu mobile s'il est ouvert
        const navPanel = document.getElementById("main-nav");
        const menuToggle = document.querySelector(".menu-toggle");
        if (navPanel && navPanel.classList.contains("is-open")) {
            navPanel.classList.remove("is-open");
            if (menuToggle) menuToggle.setAttribute("aria-expanded", "false");
            document.body.classList.remove("menu-open");
        }

        if (preselectedCategoryId && categorySelect) {
            categorySelect.value = preselectedCategoryId;
        }

        dialog.showModal();
        document.body.style.overflow = "hidden";
        setTimeout(() => {
            nameInput?.focus();
        }, 50);
    }

    function closeModal() {
        if (!dialog.open || form?.dataset.pending === "true") return;
        dialog.close();
        document.body.style.overflow = previousOverflow;

        // Nettoyage de l'URL si on etait sur ?panel=add-product
        if (window.location.search.includes("panel=add-product")) {
            const url = new URL(window.location.href);
            url.searchParams.delete("panel");
            window.history.replaceState({}, "", url.pathname + (url.search ? url.search : ""));
        }

        opener?.focus({ preventScroll: true });
    }

    // Auto-ouverture si demande dans l'URL ou data-auto-open
    if (dialog.dataset.autoOpen === "true" || window.location.search.includes("panel=add-product")) {
        openModal();
    }

    // Declencheurs d'ouverture in-page
    document.addEventListener("click", (event) => {
        if (event.defaultPrevented || event.button !== 0 || event.ctrlKey
            || event.metaKey || event.shiftKey || event.altKey
            || !(event.target instanceof Element)) {
            return;
        }

        const trigger = event.target.closest("[data-admin-open-add-product]");
        if (!trigger) return;

        event.preventDefault();
        opener = trigger;
        const preselect = trigger.dataset.preselectCategory || null;
        openModal(preselect);
    });

    // Boutons de fermeture et clic sur le fond
    dialog.addEventListener("click", (event) => {
        if (event.target.closest("[data-admin-add-product-close]")) {
            event.preventDefault();
            closeModal();
        } else if (event.target === dialog) {
            const rect = dialog.getBoundingClientRect();
            if (event.clientX < rect.left || event.clientX > rect.right
                || event.clientY < rect.top || event.clientY > rect.bottom) {
                closeModal();
            }
        }
    });

    dialog.addEventListener("cancel", (event) => {
        if (form?.dataset.pending === "true") {
            event.preventDefault();
            return;
        }
        document.body.style.overflow = previousOverflow;
        if (window.location.search.includes("panel=add-product")) {
            const url = new URL(window.location.href);
            url.searchParams.delete("panel");
            window.history.replaceState({}, "", url.pathname + (url.search ? url.search : ""));
        }
    });

    // Gestion de la miniature d'apercu image en direct
    if (fileInput) {
        fileInput.addEventListener("change", () => {
            const file = fileInput.files?.[0];
            if (file) {
                const reader = new FileReader();
                reader.onload = (e) => {
                    if (previewImg) previewImg.src = e.target.result;
                    if (previewName) previewName.textContent = file.name;
                    if (previewBox) previewBox.hidden = false;
                    if (fileDropzone) fileDropzone.hidden = true;
                };
                reader.readAsDataURL(file);
            }
        });

        previewClear?.addEventListener("click", (e) => {
            e.preventDefault();
            fileInput.value = "";
            if (previewImg) previewImg.src = "";
            if (previewName) previewName.textContent = "";
            if (previewBox) previewBox.hidden = true;
            if (fileDropzone) fileDropzone.hidden = false;
        });
    }

    // Progressive enhancement: never replay a POST after an uncertain response.
    if (form) {
        form.addEventListener("submit", async (event) => {
            if (!form.checkValidity() || !window.AdminProducts) {
                return;
            }

            event.preventDefault();
            const data = await window.AdminProducts.submit(form);
            if (data) {
                closeModal();
                form.reset();
                if (previewBox) previewBox.hidden = true;
                if (previewImg) previewImg.removeAttribute("src");
                if (fileDropzone) fileDropzone.hidden = false;
            }
        });
    }
}

function createWeightOptionRow(compact = false) {
    return `
        <div class="weight-option-row" data-weight-option-row>
            <input
                name="weight_label"
                placeholder="${compact ? '100 g' : escapeHtml(t("admin.product.weight_label_placeholder"))}"
                aria-label="${escapeHtml(t("admin.product.weight_label_placeholder"))}"
                autocomplete="off"
            >
            <input
                name="weight_price"
                type="number"
                min="0"
                step="0.01"
                placeholder="${compact ? '15 DH' : escapeHtml(t("admin.product.weight_price_placeholder"))}"
                aria-label="${escapeHtml(t("admin.product.weight_price_placeholder"))}"
            >
            <button
                type="button"
                class="button-secondary weight-option-remove"
                data-weight-option-remove
                aria-label="${escapeHtml(t("admin.product.remove_weight_option"))}"
            >
                ${compact ? '<span aria-hidden="true">×</span>' : escapeHtml(t("admin.product.remove_weight_option"))}
            </button>
        </div>
    `;
}

function bindWeightOptionsEditors(scope = document) {
    scope.querySelectorAll("[data-weight-options-editor]").forEach((editor) => {
        if (editor.dataset.bound === "true") return;
        const list = editor.querySelector("[data-weight-option-list]");
        const addButton = editor.querySelector("[data-weight-option-add]");

        if (!list) {
            return;
        }

        editor.dataset.bound = "true";

        addButton?.addEventListener("click", () => {
            list.insertAdjacentHTML("beforeend", createWeightOptionRow(editor.hasAttribute("data-weight-options-compact")));
            list.querySelector("[data-weight-option-row]:last-child input")?.focus();
        });

        editor.addEventListener("click", (event) => {
            if (!(event.target instanceof Element)) {
                return;
            }

            const removeButton = event.target.closest("[data-weight-option-remove]");
            if (!removeButton) {
                return;
            }

            const rows = Array.from(list.querySelectorAll("[data-weight-option-row]"));
            const row = removeButton.closest("[data-weight-option-row]");

            if (rows.length <= 1) {
                row?.querySelectorAll("input").forEach((input) => {
                    input.value = "";
                });
                return;
            }

            row?.remove();
        });

        if (!list.querySelector("[data-weight-option-row]")) {
            list.insertAdjacentHTML("beforeend", createWeightOptionRow());
        }
    });
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

let currentProductModalState = {
    id: null,
    name: "",
    image: "",
    price: 0,
    weightLabel: "",
};

function getProductModalElements() {
    const root = document.querySelector("[data-product-modal]");

    if (!root) {
        return null;
    }

    return {
        root,
        panel: root.querySelector(".product-modal-panel"),
        visual: root.querySelector("[data-product-modal-visual]"),
        image: root.querySelector("[data-product-modal-image]"),
        fallback: root.querySelector("[data-product-modal-fallback]"),
        title: root.querySelector("[data-product-modal-title]"),
        category: root.querySelector("[data-product-modal-category]"),
        price: root.querySelector("[data-product-modal-price]"),
        weightsWrap: root.querySelector("[data-product-modal-weights]"),
        weightsChips: root.querySelector("[data-product-modal-chips]"),
        description: root.querySelector("[data-product-modal-description]"),
        addBtn: root.querySelector("[data-product-modal-add-btn]"),
        closeButtons: root.querySelectorAll("[data-product-modal-close]"),
    };
}

function openProductModal({ id, name, category, description, image, price, weight_options }) {
    const elements = getProductModalElements();

    if (!elements) {
        return;
    }

    const weights = Array.isArray(weight_options) ? weight_options : [];
    let initialPrice = Number(price) || 0;
    let initialWeightLabel = "";

    if (weights.length > 0) {
        initialPrice = Number(weights[0].price) || initialPrice;
        initialWeightLabel = weights[0].label || "";
    }

    currentProductModalState = {
        id: id || null,
        name: name || t("js.modal.product"),
        image: image || "",
        price: initialPrice,
        weightLabel: initialWeightLabel,
    };

    const imageUrl = image ? buildStaticImageUrl(image) : "";

    if (elements.title) {
        elements.title.textContent = name || t("js.modal.product");
    }

    if (elements.category) {
        if (category) {
            elements.category.textContent = category;
            elements.category.hidden = false;
        } else {
            elements.category.textContent = "";
            elements.category.hidden = true;
        }
    }

    if (elements.price) {
        elements.price.textContent = formatCurrency(initialPrice);
    }

    if (elements.description) {
        elements.description.textContent = description || t("js.modal.no_description");
    }

    if (elements.visual && elements.image) {
        elements.visual.classList.remove("is-contain");
        elements.visual.onclick = () => {
            elements.visual.classList.toggle("is-contain");
        };
        elements.visual.style.cursor = "zoom-in";
        elements.visual.title = "Cliquer pour afficher la photo en entier (sans recadrage)";
        if (imageUrl) {
            elements.image.src = imageUrl;
            elements.image.alt = name || t("js.modal.product");
            elements.image.hidden = false;
            if (elements.fallback) elements.fallback.hidden = true;
            elements.visual.hidden = false;
        } else {
            elements.image.removeAttribute("src");
            elements.image.hidden = true;
            if (elements.fallback) elements.fallback.hidden = false;
            elements.visual.hidden = false;
        }
    }

    // Weight selection chips
    if (elements.weightsWrap && elements.weightsChips) {
        if (weights.length > 1) {
            elements.weightsWrap.hidden = false;
            elements.weightsChips.innerHTML = weights.map((opt, idx) => `
                <button type="button" class="product-modal-chip ${idx === 0 ? 'is-selected' : ''}"
                    data-modal-weight-label="${escapeHtml(opt.label)}"
                    data-modal-weight-price="${escapeHtml(opt.price)}">
                    ${escapeHtml(opt.label)}
                </button>
            `).join("");

            elements.weightsChips.querySelectorAll(".product-modal-chip").forEach(chip => {
                chip.addEventListener("click", () => {
                    elements.weightsChips.querySelectorAll(".product-modal-chip").forEach(c => c.classList.remove("is-selected"));
                    chip.classList.add("is-selected");
                    const optPrice = Number(chip.dataset.modalWeightPrice) || 0;
                    const optLabel = chip.dataset.modalWeightLabel || "";
                    currentProductModalState.price = optPrice;
                    currentProductModalState.weightLabel = optLabel;
                    if (elements.price) {
                        elements.price.textContent = formatCurrency(optPrice);
                    }
                });
            });
        } else if (weights.length === 1) {
            elements.weightsWrap.hidden = false;
            elements.weightsChips.innerHTML = `<span class="product-modal-single-weight">${escapeHtml(weights[0].label)}</span>`;
        } else {
            elements.weightsWrap.hidden = true;
            elements.weightsChips.innerHTML = "";
        }
    }

    // Add to cart action
    if (elements.addBtn) {
        elements.addBtn.disabled = !id;
        elements.addBtn.onclick = (e) => {
            e.preventDefault();
            if (!currentProductModalState.id) return;
            addToCart(
                currentProductModalState.id,
                currentProductModalState.name,
                currentProductModalState.price,
                currentProductModalState.image,
                currentProductModalState.weightLabel
            );

            // Visual feedback on button
            const originalHtml = elements.addBtn.innerHTML;
            elements.addBtn.classList.add("is-added");
            elements.addBtn.innerHTML = `✓ ${escapeHtml(t("home.product.add"))}`;
            notify(t("js.cart.added", { name: currentProductModalState.name }));

            setTimeout(() => {
                elements.addBtn.classList.remove("is-added");
                elements.addBtn.innerHTML = originalHtml;
            }, 1200);
        };
    }

    elements.root.hidden = false;
    document.body.classList.add("modal-open");
    document.body.style.overflow = "hidden";
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
        elements.visual.hidden = false;
        elements.visual.classList.remove("is-contain");
        elements.visual.onclick = null;
    }

    elements.root.hidden = true;
    document.body.classList.remove("modal-open");

    const isCatModalOpen = document.querySelector('[data-cat-modal-panel]')?.classList.contains('is-open');
    const isCartDrawerOpen = document.querySelector('.cart-drawer-panel')?.classList.contains('is-open');
    if (!isCatModalOpen && !isCartDrawerOpen) {
        document.body.style.overflow = "";
    }
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

document.addEventListener("DOMContentLoaded", () => {
    bindAdminCategoryModal();
    bindAdminAccountsModal();
    bindAdminAddProductModal();
    bindInstalledMobileNavigation();
    bindPwaInstall();
    updateCartCount();
    renderCart();
    bindCustomerFields();
    bindQuickReturnButton();
    bindProductModal();
    bindWeightOptionsEditors();

    document.querySelectorAll("[data-product-weight-select]").forEach((select) => {
        updateProductWeightSelection(select.closest(".product-card, .search-live-product"));
    });

    document.querySelectorAll("[data-live-search-root]").forEach((root) => {
        bindLiveSearch(root);
    });

    document.querySelectorAll("[data-admin-filter-root]").forEach((root) => {
        bindAdminRealtimeFilter(root);
    });

    document.addEventListener("click", (event) => {
        if (!(event.target instanceof Element)) {
            return;
        }

        const button = event.target.closest("[data-cart-add]");

        if (!button) {
            return;
        }

        const origContent = button.innerHTML;
        button.classList.add("is-added");
        button.innerHTML = `<span style="display:inline-flex;align-items:center;gap:4px;">✓ Ajouté</span>`;
        setTimeout(() => {
            button.classList.remove("is-added");
            button.innerHTML = origContent;
        }, 1200);

        addToCart(
            button.dataset.productId,
            button.dataset.productName,
            button.dataset.productPrice,
            button.dataset.productImage,
            button.dataset.productWeightLabel
        );
    });

    document.addEventListener("change", (event) => {
        if (!(event.target instanceof Element)) {
            return;
        }

        const select = event.target.closest("[data-product-weight-select]");
        if (!select) {
            return;
        }

        updateProductWeightSelection(select.closest(".product-card, .search-live-product"));
    });

    document.addEventListener("click", (event) => {
        if (!(event.target instanceof Element)) {
            return;
        }

        const quantityButton = event.target.closest("[data-cart-quantity]");
        if (quantityButton) {
            changeQuantity(
                Number(quantityButton.dataset.productId),
                Number(quantityButton.dataset.cartDelta),
                quantityButton.dataset.productWeightLabel
            );
            return;
        }

        const removeButton = event.target.closest("[data-cart-remove]");
        if (removeButton) {
            removeFromCart(
                Number(removeButton.dataset.productId),
                removeButton.dataset.productWeightLabel
            );
        }
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

        let weightOptions = [];
        try {
            if (trigger.dataset.productWeights) {
                weightOptions = JSON.parse(trigger.dataset.productWeights);
            }
        } catch (e) {
            console.error("Failed to parse product weights", e);
        }

        openProductModal({
            id: trigger.dataset.productId,
            name: trigger.dataset.productName,
            category: trigger.dataset.productCategory,
            description: trigger.dataset.productDescription,
            image: trigger.dataset.productImage,
            price: trigger.dataset.productPrice,
            weight_options: weightOptions,
        });
    });

    document.addEventListener("keydown", (event) => {
        if (event.key === "Enter" || event.key === " ") {
            const trigger = event.target.closest("[data-show-description], [data-cat-detail-trigger]");
            if (trigger && (trigger.tagName === "DIV" || trigger.tagName === "SPAN" || trigger.tagName === "H4" || trigger.tagName === "H3")) {
                event.preventDefault();
                trigger.click();
            }
        }
    });

    const nav = document.getElementById("main-nav");

    if (nav) {
        nav.querySelectorAll("a").forEach((link) => {
            link.addEventListener("click", closeMobileMenu);
        });
    }

    
    // Drawer open/close and checkout handlers
    document.addEventListener("click", (event) => {
        const openBtn = event.target.closest('[data-drawer-open="cart"]');
        if (openBtn) {
            event.preventDefault();
            openCartDrawer();
            return;
        }
        const closeBtn = event.target.closest('[data-drawer-close="cart"], [data-drawer-backdrop="cart"]');
        if (closeBtn) {
            event.preventDefault();
            closeCartDrawer();
            return;
        }
        const clearBtn = event.target.closest('#drawer-clear-btn');
        if (clearBtn) {
            event.preventDefault();
            clearCart();
            return;
        }
        const closeCatModal = event.target.closest('[data-cat-modal-close], [data-cat-modal-backdrop]');
        if (closeCatModal) {
            event.preventDefault();
            closeCategoryModal();
            return;
        }
        const catCard = event.target.closest('.category-dept-card');
        if (catCard) {
            event.preventDefault();
            const catId = catCard.dataset.categoryId;
            const catName = catCard.dataset.categoryName;
            const catCount = catCard.dataset.categoryCount;
            openCategoryModal(catId, catName, catCount);
            return;
        }
        const catDetailTrigger = event.target.closest('[data-cat-detail-trigger]');
        if (catDetailTrigger) {
            event.preventDefault();
            const prodIdx = catDetailTrigger.dataset.catDetailIdx;
            const prodId = catDetailTrigger.dataset.prodId;
            let prod = null;
            if (prodIdx !== undefined && currentCatModalProducts[Number(prodIdx)]) {
                prod = currentCatModalProducts[Number(prodIdx)];
            } else if (prodId) {
                prod = currentCatModalProducts.find(p => String(p.id) === String(prodId));
            }
            if (prod) {
                const defaultWeight = prod.weight_options && prod.weight_options.length > 0 ? prod.weight_options[0] : null;
                const defaultPrice = defaultWeight ? defaultWeight.price : prod.price;
                openProductModal({
                    id: prod.id,
                    name: prod.name,
                    category: prod.category_name,
                    description: prod.description,
                    image: prod.image,
                    price: defaultPrice,
                    weight_options: prod.weight_options || []
                });
            }
            return;
        }
        const catChip = event.target.closest('.cat-weight-chip');
        if (catChip) {
            const card = catChip.closest('.cat-modal-item-card');
            if (card) {
                card.querySelectorAll('.cat-weight-chip').forEach((c) => c.classList.remove('is-selected'));
                catChip.classList.add('is-selected');
                const price = Number(catChip.dataset.catWeightPrice);
                const label = catChip.dataset.catWeightLabel;
                const priceEl = card.querySelector('[data-cat-price-display]');
                if (priceEl && !isNaN(price)) {
                    priceEl.textContent = formatCurrency(price);
                }
                const addBtn = card.querySelector('[data-cat-add-btn]');
                if (addBtn) {
                    addBtn.dataset.prodPrice = price;
                    addBtn.dataset.prodWeight = label;
                }
            }
            return;
        }
        const catAddBtn = event.target.closest('[data-cat-add-btn]');
        if (catAddBtn) {
            event.preventDefault();
            const id = catAddBtn.dataset.prodId;
            const name = catAddBtn.dataset.prodName;
            const price = Number(catAddBtn.dataset.prodPrice);
            const image = catAddBtn.dataset.prodImage;
            const weight = catAddBtn.dataset.prodWeight;
            addToCart(id, name, price, image, weight);

            const origText = catAddBtn.textContent;
            catAddBtn.textContent = "✓ Ajouté";
            catAddBtn.style.background = "#2D4739";
            catAddBtn.style.color = "#FFFFFF";
            setTimeout(() => {
                catAddBtn.textContent = origText;
                catAddBtn.style.background = "";
                catAddBtn.style.color = "";
            }, 1200);
            return;
        }
        const checkoutBtn = event.target.closest('#drawer-checkout-btn');
        if (checkoutBtn) {
            event.preventDefault();
            checkoutFromDrawer();
            return;
        }
        const chip = event.target.closest('.weight-chip-btn');
        if (chip) {
            const card = chip.closest('.product-card');
            if (card) {
                card.querySelectorAll('.weight-chip-btn').forEach((btn) => btn.classList.remove('is-selected'));
                chip.classList.add('is-selected');
                const price = Number(chip.dataset.weightPrice);
                const label = chip.dataset.weightLabel;
                const priceDisplay = card.querySelector('[data-product-price-display]');
                if (priceDisplay && !isNaN(price)) {
                    priceDisplay.textContent = formatCurrency(price);
                }
                const addBtn = card.querySelector('[data-cart-add]');
                if (addBtn) {
                    addBtn.dataset.productPrice = price;
                    addBtn.dataset.productWeightLabel = label;
                }
                const select = card.querySelector('[data-product-weight-select]');
                if (select) {
                    select.value = label;
                }
            }
        }
    });

    const catModalSearch = document.getElementById("cat-modal-search-input");
    if (catModalSearch) {
        catModalSearch.addEventListener("input", (e) => {
            if (catModalRequest || catModalSearch.disabled
                || !document.querySelector('[data-cat-modal-panel]')?.classList.contains('is-open')) return;
            const query = (e.target.value || "").trim().toLowerCase();
            if (!query) {
                renderCatModalProducts(currentCatModalProducts);
            } else {
                const filtered = currentCatModalProducts.filter((p) =>
                    (p.name && p.name.toLowerCase().includes(query)) ||
                    (p.description && p.description.toLowerCase().includes(query))
                );
                renderCatModalProducts(filtered);
            }
        });
    }

    const categoryFilterInput = document.getElementById("category-filter-input");
    if (categoryFilterInput) {
        const categoryCards = document.querySelectorAll(".category-dept-card");
        categoryFilterInput.addEventListener("input", (e) => {
            const query = (e.target.value || "").trim().toLowerCase();
            let visibleCount = 0;
            categoryCards.forEach((card) => {
                const name = (card.dataset.categoryName || "").toLowerCase();
                const matches = !query || name.includes(query);
                card.style.display = matches ? "flex" : "none";
                if (matches) visibleCount++;
            });
            let noMatchEl = document.getElementById("category-no-match");
            if (visibleCount === 0 && query) {
                if (!noMatchEl) {
                    noMatchEl = document.createElement("div");
                    noMatchEl.id = "category-no-match";
                    noMatchEl.className = "empty-state";
                    noMatchEl.style.cssText = "grid-column: 1 / -1; text-align: center; padding: 32px 16px; background: #fff; border-radius: 16px; border: 1px dashed rgba(45,71,57,0.15);";
                    noMatchEl.innerHTML = `<p style="color:var(--color-text-muted);font-size:0.95rem;">Aucun rayon ne correspond à "<strong>${escapeHtml(query)}</strong>"</p>`;
                    const grid = document.querySelector(".categories-department-grid");
                    if (grid) grid.appendChild(noMatchEl);
                } else {
                    const strong = noMatchEl.querySelector("strong");
                    if (strong) strong.textContent = query;
                    noMatchEl.style.display = "block";
                }
            } else if (noMatchEl) {
                noMatchEl.style.display = "none";
            }
        });
    }

    document.addEventListener("keydown", (event) => {
        if (event.key === "Escape") {
            closeCartDrawer();
            closeCategoryModal();
        }
    });

    renderDrawerCart();

    window.addEventListener("resize", () => {
        if (window.innerWidth > 900) {
            closeMobileMenu();
        }
    });
});
