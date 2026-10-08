/* Product mutations update server-rendered cards without navigating the dashboard. */
(() => {
    "use strict";

    let mutationPending = false;
    const headers = { "X-Requested-With": "XMLHttpRequest", Accept: "application/json" };

    function announce(message) {
        const dialog = document.querySelector("[data-admin-category-modal][open]");
        if (!dialog) {
            notify(message, "success");
            return;
        }
        // Body-level toasts sit behind a native dialog's top layer.
        let notice = dialog.querySelector("[data-admin-product-notice]");
        if (!notice) {
            notice = document.createElement("p");
            notice.className = "admin-product-notice";
            notice.dataset.adminProductNotice = "";
            notice.setAttribute("role", "status");
            dialog.querySelector(".admin-category-modal-toolbar").append(notice);
        }
        notice.textContent = message;
    }

    function showError(container, message) {
        let alert = container.querySelector("[data-admin-product-error]");
        if (!alert) {
            alert = document.createElement("p");
            alert.dataset.adminProductError = "";
            alert.className = "admin-product-error";
            alert.setAttribute("role", "alert");
            container.prepend(alert);
        }
        alert.textContent = message;
        alert.hidden = false;
        alert.scrollIntoView({ block: "nearest" });
    }

    async function readResponse(response) {
        let data;
        try {
            data = await response.json();
        } catch (_) {
            // CSRF, upload size and rate-limit errors can be HTML responses.
        }
        if (!response.ok || !data?.ok) {
            const key = {
                400: "admin.products.request_failed",
                401: "admin.products.session_expired",
                403: "admin.products.session_expired",
                413: "admin.products.upload_too_large",
                429: "admin.products.rate_limited",
            }[response.status] || "admin.products.unconfirmed";
            throw new Error(data?.error || t(key));
        }
        return data;
    }

    function updateCategory(category) {
        document.querySelectorAll(`[data-admin-category-id="${category.id}"]`).forEach(card => {
            const count = card.querySelector("[data-admin-category-card-count]");
            if (count) count.textContent = category.count_label;
            const link = card.querySelector("[data-admin-category-open]");
            if (link) link.dataset.categoryCount = category.product_count;
            const media = card.querySelector(".admin-category-media");
            if (media && category.cover_image) {
                let img = media.querySelector("img");
                if (!img) {
                    img = document.createElement("img");
                    media.replaceChildren(img);
                }
                img.src = buildStaticImageUrl(category.cover_image);
                img.alt = category.name;
            } else if (media && media.querySelector("img")) {
                const fallback = document.createElement("div");
                fallback.className = "category-fallback";
                fallback.textContent = category.name.slice(0, 1).toUpperCase();
                media.replaceChildren(fallback);
            }
        });
        document.querySelectorAll(`[data-admin-products-count="${category.id}"]`).forEach(count => {
            count.textContent = category.subtitle;
        });
        const dialog = document.querySelector("[data-admin-category-modal]");
        if (dialog?.dataset.categoryId === String(category.id)) {
            dialog.querySelector("[data-admin-category-count]").textContent = category.subtitle;
        }
    }

    function updateProducts(data) {
        // Validate the response before changing any visible card.
        if (!Number.isInteger(data.product_id) || !Array.isArray(data.categories) || !data.stats) {
            throw new Error(t("admin.products.unconfirmed"));
        }
        const template = document.createElement("template");
        template.innerHTML = data.product_html || "";
        const replacement = template.content.querySelector("[data-admin-product-id]");
        if (data.product && replacement?.dataset.adminProductId !== String(data.product_id)) {
            throw new Error(t("admin.products.unconfirmed"));
        }

        const scrollPositions = [...document.querySelectorAll(
            "[data-admin-category-content], [data-admin-category-modal]"
        )].map(element => [element, element.scrollTop]);
        const pagePosition = [window.scrollX, window.scrollY];

        document.querySelectorAll("[data-admin-products-category]").forEach(list => {
            const current = list.querySelector(`[data-admin-product-id="${data.product_id}"]`);
            const belongs = data.product && String(data.product.category_id) === list.dataset.adminProductsCategory;
            if (belongs) {
                const card = replacement.cloneNode(true);
                if (current) current.replaceWith(card);
                else list.prepend(card);
            } else {
                current?.remove();
            }
            const empty = list.querySelector("[data-admin-products-empty]");
            if (list.querySelector("[data-admin-product-id]")) {
                empty?.remove();
            } else if (!empty) {
                const emptyTemplate = document.querySelector("[data-admin-products-empty-template]");
                if (emptyTemplate) list.append(emptyTemplate.content.cloneNode(true));
            }
            // Keep the current search, including newly added or renamed products.
            list.parentElement.querySelector("[data-admin-realtime-search]")
                ?.dispatchEvent(new Event("input", { bubbles: true }));
        });
        data.categories.forEach(updateCategory);
        document.querySelectorAll("[data-admin-stat]").forEach(stat => {
            const value = data.stats[stat.dataset.adminStat];
            if (Number.isInteger(value)) stat.textContent = value;
        });
        scrollPositions.forEach(([element, top]) => { element.scrollTop = top; });
        if (window.scrollX !== pagePosition[0] || window.scrollY !== pagePosition[1]) {
            window.scrollTo({ left: pagePosition[0], top: pagePosition[1], behavior: "instant" });
        }
    }

    async function submit(form) {
        // Serialize mutations so a slower response cannot overwrite newer counts.
        if (mutationPending || !form.reportValidity()) return null;
        mutationPending = true;
        form.dataset.pending = "true";
        form.setAttribute("aria-busy", "true");
        const alert = form.querySelector("[data-admin-product-error]");
        if (alert) alert.hidden = true;
        const formData = new FormData(form);
        const scope = form.closest("[data-admin-product-id]") || form;
        scope.setAttribute("aria-busy", "true");
        const controls = [...scope.querySelectorAll("input, select, textarea, button")]
            .map(control => [control, control.disabled]);
        controls.forEach(([control]) => { control.disabled = true; });
        const button = form.querySelector('button[type="submit"]');
        const buttonHtml = button?.innerHTML;
        if (button) button.textContent = t("admin.products.saving");
        try {
            const response = await fetch(form.getAttribute("action"), {
                method: "POST", body: formData, headers, redirect: "error",
            });
            const data = await readResponse(response);
            updateProducts(data);
            if (data.message) announce(data.message);
            return data;
        } catch (error) {
            showError(form, error instanceof TypeError ? t("admin.products.unconfirmed") : error.message);
            return null;
        } finally {
            mutationPending = false;
            delete form.dataset.pending;
            form.removeAttribute("aria-busy");
            scope.removeAttribute("aria-busy");
            controls.forEach(([control, disabled]) => { control.disabled = disabled; });
            if (button) button.innerHTML = buttonHtml;
        }
    }

    window.AdminProducts = { submit };

    document.addEventListener("DOMContentLoaded", () => {
        const dialog = document.querySelector("[data-admin-edit-product-modal]");
        const content = dialog?.querySelector("[data-admin-edit-product-content]");
        let loadRequest = null;
        let opener = null;
        let productId = null;
        let previousOverflow = "";
        let modalActive = false;

        function closeEditor() {
            if (dialog?.querySelector('[data-pending="true"]')) return;
            dialog?.close();
        }

        if (dialog && typeof dialog.showModal === "function") {
            dialog.addEventListener("close", () => {
                if (dialog.open || !modalActive) return;
                modalActive = false;
                loadRequest?.abort();
                document.body.style.overflow = previousOverflow;
                const focusTarget = opener?.isConnected ? opener
                    : document.querySelector(`[data-admin-product-id="${productId}"] [data-admin-product-edit]`)
                    || document.querySelector("[data-admin-category-modal][open] [data-admin-realtime-search]");
                focusTarget?.focus({ preventScroll: true });
            });
            dialog.addEventListener("cancel", event => {
                if (dialog.querySelector('[data-pending="true"]')) event.preventDefault();
            });
            dialog.addEventListener("click", event => {
                if (event.target.closest("[data-admin-edit-product-close]")) {
                    event.preventDefault();
                    closeEditor();
                } else if (event.target === dialog) {
                    const rect = dialog.getBoundingClientRect();
                    if (event.clientX < rect.left || event.clientX > rect.right
                        || event.clientY < rect.top || event.clientY > rect.bottom) closeEditor();
                }
            });
            document.addEventListener("click", async event => {
                if (event.defaultPrevented || event.button !== 0 || event.ctrlKey || event.metaKey
                    || event.shiftKey || event.altKey || !(event.target instanceof Element)) return;
                const link = event.target.closest("[data-admin-product-edit]");
                if (!link) return;
                event.preventDefault();
                if (mutationPending) return;
                opener = link;
                productId = link.closest("[data-admin-product-id]").dataset.adminProductId;
                loadRequest?.abort();
                const request = new AbortController();
                loadRequest = request;
                content.innerHTML = `<p class="admin-category-modal-message" role="status">${escapeHtml(t("category_modal.loading"))}</p>`;
                if (!modalActive) previousOverflow = document.body.style.overflow;
                modalActive = true;
                dialog.showModal();
                document.body.style.overflow = "hidden";
                try {
                    const data = await readResponse(await fetch(link.href, {
                        headers, signal: request.signal, redirect: "error",
                    }));
                    if (request.signal.aborted || !dialog.open) return;
                    const template = document.createElement("template");
                    template.innerHTML = data.form_html || "";
                    const form = template.content.querySelector("[data-admin-edit-product-form]");
                    if (!form) throw new Error(t("admin.products.load_error"));
                    content.replaceChildren(form);
                    bindWeightOptionsEditors(content);
                    form.elements.namedItem("name")?.focus({ preventScroll: true });
                } catch (error) {
                    if (request.signal.aborted || !dialog.open) return;
                    content.replaceChildren();
                    showError(content, error instanceof TypeError ? t("admin.products.load_error") : error.message);
                }
            });
        }

        document.addEventListener("submit", async event => {
            const form = event.target;
            if (!(form instanceof HTMLFormElement)
                || !form.matches("[data-admin-product-action], [data-admin-edit-product-form]")) return;
            event.preventDefault();
            const card = form.closest("[data-admin-product-id]");
            const list = card?.parentElement;
            const action = form.dataset.adminProductAction;
            const data = await submit(form);
            if (data && dialog?.contains(form)) closeEditor();
            else if (data?.form_html && form.matches("[data-admin-edit-product-form]")) {
                const template = document.createElement("template");
                template.innerHTML = data.form_html;
                const updated = template.content.querySelector("[data-admin-edit-product-form]");
                if (updated) {
                    const parent = form.parentElement;
                    form.replaceWith(updated);
                    bindWeightOptionsEditors(parent);
                    const back = document.querySelector("[data-admin-edit-product-return]");
                    if (back) back.href = updated.querySelector("[data-admin-edit-product-close]").href;
                    updated.querySelector('button[type="submit"]')?.focus({ preventScroll: true });
                }
            }
            else if (data && list) {
                const target = action === "toggle"
                    ? list.querySelector(`[data-admin-product-id="${data.product_id}"] [data-admin-product-action="toggle"] button`)
                    : list.parentElement.querySelector("[data-admin-realtime-search]");
                target?.focus({ preventScroll: true });
            }
        });
    });
})();
