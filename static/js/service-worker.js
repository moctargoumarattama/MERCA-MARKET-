// ─── Version du cache ────────────────────────────────────────────────────────
// À synchroniser avec ASSET_VERSION dans config.py à chaque déploiement.
// Changer cette valeur invalide automatiquement tout l'ancien cache.
const CACHE_NAME = "merca-fruit-sec-v21-category-requests";

// ─── Ressources statiques à pré-cacher (app shell) ───────────────────────────
const APP_SHELL = [
    "/static/manifest.webmanifest",
    "/static/css/style.css",
    "/static/css/modern.css",
    "/static/css/responsive.css",
    "/static/js/app.js",
    "/static/images/icon-192.png",
    "/static/images/icon-512.png",
    "/static/images/LOGO.png",
    "/static/images/3.png",
];

// ─── Installation : pré-cache l'app shell ────────────────────────────────────
self.addEventListener("install", (event) => {
    event.waitUntil(
        caches.open(CACHE_NAME).then((cache) => cache.addAll(APP_SHELL))
    );
    self.skipWaiting();
});

// ─── Activation : supprime les vieux caches et force la recharge ─────────────
self.addEventListener("activate", (event) => {
    event.waitUntil(
        caches.keys().then((keys) =>
            Promise.all(
                keys
                    .filter((key) => key !== CACHE_NAME)
                    .map((key) => caches.delete(key))
            )
        )
    );
    self.clients.claim().then(() => {
        self.clients.matchAll({ type: "window" }).then((clients) => {
            clients.forEach((client) => {
                if ("navigate" in client) {
                    client.navigate(client.url);
                }
            });
        });
    });
});

// ─── Interception des requêtes ───────────────────────────────────────────────
self.addEventListener("fetch", (event) => {
    // Ignorer les méthodes non-GET (POST, etc.)
    if (event.request.method !== "GET") return;

    const requestUrl = new URL(event.request.url);
    const isSameOrigin = requestUrl.origin === self.location.origin;

    // Changer de langue doit mettre à jour la session avant d'afficher la page.
    if (isSameOrigin && requestUrl.pathname.startsWith("/language/")) {
        event.respondWith(fetch(event.request));
        return;
    }

    // ── Admin : toujours réseau direct, jamais de cache ──────────────────────
    if (isSameOrigin && requestUrl.pathname.startsWith("/admin")) {
        event.respondWith(fetch(event.request));
        return;
    }

    // ── API : toujours réseau direct (données en temps réel) ─────────────────
    if (isSameOrigin && requestUrl.pathname.startsWith("/api/")) {
        event.respondWith(fetch(event.request));
        return;
    }

    // ── Navigation : réseau d'abord, cache uniquement hors connexion ────────
    // Les pages dépendent de la langue enregistrée dans la session.
    if (event.request.mode === "navigate") {
        event.respondWith(
            fetch(event.request)
                .then((response) => {
                    if (response && response.status === 200) {
                        const copy = response.clone();
                        event.waitUntil(
                            caches.open(CACHE_NAME).then((cache) => cache.put(event.request, copy))
                        );
                    }
                    return response;
                })
                .catch(async () => {
                    const cached = await caches.match(event.request)
                        || await caches.match("/");
                    return cached || new Response(
                        "<html><body style='font-family:sans-serif;text-align:center;padding:40px'>" +
                        "<h2>MERCA FRUIT SEC</h2><p>Connexion en cours...</p></body></html>",
                        { status: 503, headers: { "Content-Type": "text/html; charset=utf-8" } }
                    );
                })
        );
        return;
    }

    // ── Fichiers statiques CSS/JS : réseau d'abord, cache en fallback ─────────
    // (ils ont un ?v= versioned donc le cache est toujours frais)
    if (
        isSameOrigin &&
        (requestUrl.pathname.endsWith(".js") || requestUrl.pathname.endsWith(".css"))
    ) {
        event.respondWith(
            fetch(event.request)
                .then((response) => {
                    if (response && response.status === 200) {
                        const copy = response.clone();
                        caches.open(CACHE_NAME).then((cache) => cache.put(event.request, copy));
                    }
                    return response;
                })
                .catch(() => caches.match(event.request))
        );
        return;
    }

    // ── Images et autres ressources statiques : cache first ──────────────────
    if (isSameOrigin) {
        event.respondWith(
            caches.match(event.request).then(
                (cachedResponse) => cachedResponse || fetch(event.request).then((response) => {
                    if (response && response.status === 200) {
                        const copy = response.clone();
                        caches.open(CACHE_NAME).then((cache) => cache.put(event.request, copy));
                    }
                    return response;
                })
            )
        );
    }
});
