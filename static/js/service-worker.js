// ─── Version du cache ────────────────────────────────────────────────────────
// À synchroniser avec ASSET_VERSION dans config.py à chaque déploiement.
// Changer cette valeur invalide automatiquement tout l'ancien cache.
const CACHE_NAME = "merca-fruit-sec-v3";

// ─── Ressources statiques à pré-cacher (app shell) ───────────────────────────
const APP_SHELL = [
    "/static/manifest.webmanifest",
    "/static/css/style.css",
    "/static/js/app.js",
    "/static/images/icon-192.png",
    "/static/images/icon-512.png",
    "/static/images/LOGO.png",
];

// ─── Installation : pré-cache l'app shell ────────────────────────────────────
self.addEventListener("install", (event) => {
    event.waitUntil(
        caches.open(CACHE_NAME).then((cache) => cache.addAll(APP_SHELL))
    );
    self.skipWaiting();
});

// ─── Activation : supprime les vieux caches ──────────────────────────────────
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
    self.clients.claim();
});

// ─── Interception des requêtes ───────────────────────────────────────────────
self.addEventListener("fetch", (event) => {
    // Ignorer les méthodes non-GET (POST, etc.)
    if (event.request.method !== "GET") return;

    const requestUrl = new URL(event.request.url);
    const isSameOrigin = requestUrl.origin === self.location.origin;

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

    // ── Navigation (ouverture de page) : STALE-WHILE-REVALIDATE ──────────────
    // → Affiche instantanément la page en cache si disponible
    // → Met à jour en arrière-plan pour la prochaine visite
    // → Résout l'écran blanc dû au cold start de PythonAnywhere
    if (event.request.mode === "navigate") {
        event.respondWith(
            caches.open(CACHE_NAME).then(async (cache) => {
                // 1. Chercher dans le cache
                const cached = await cache.match(event.request)
                    || await cache.match("/");

                // 2. Lancer la requête réseau en parallèle (sans attendre)
                const networkPromise = fetch(event.request)
                    .then((response) => {
                        if (response && response.status === 200) {
                            cache.put(event.request, response.clone());
                        }
                        return response;
                    })
                    .catch(() => null);

                // 3. Si on a du cache → afficher immédiatement, réseau en fond
                //    Si pas de cache → attendre le réseau (premier accès)
                if (cached) {
                    // Mise à jour silencieuse en arrière-plan
                    event.waitUntil(networkPromise);
                    return cached;
                }
                // Pas encore en cache (première visite) → attendre le réseau
                return networkPromise || new Response(
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
