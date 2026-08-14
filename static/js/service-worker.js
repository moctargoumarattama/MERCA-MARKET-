const CACHE_NAME = "merca-fruit-sec-v1";
const APP_SHELL = [
    "/static/manifest.webmanifest",
    "/static/css/style.css",
    "/static/js/app.js",
    "/static/images/icon-192.png",
    "/static/images/icon-512.png"
];

self.addEventListener("install", (event) => {
    event.waitUntil(caches.open(CACHE_NAME).then((cache) => cache.addAll(APP_SHELL)));
    self.skipWaiting();
});

self.addEventListener("activate", (event) => {
    event.waitUntil(
        caches.keys().then((keys) => Promise.all(
            keys
                .filter((key) => key !== CACHE_NAME)
                .map((key) => caches.delete(key))
        ))
    );
    self.clients.claim();
});

self.addEventListener("fetch", (event) => {
    if (event.request.method !== "GET") {
        return;
    }

    const requestUrl = new URL(event.request.url);
    const isAdminRequest = requestUrl.origin === self.location.origin
        && requestUrl.pathname.startsWith("/admin");

    if (isAdminRequest) {
        event.respondWith(fetch(event.request));
        return;
    }

    if (event.request.mode === "navigate") {
        event.respondWith(
            fetch(event.request)
                .then((response) => {
                    const copy = response.clone();
                    caches.open(CACHE_NAME).then((cache) => cache.put(event.request, copy));
                    return response;
                })
                .catch(async () => {
                    const cachedPage = await caches.match(event.request);
                    return cachedPage || caches.match("/") || new Response("Hors ligne", { status: 503 });
                })
        );
        return;
    }

    if (requestUrl.origin === self.location.origin && !requestUrl.pathname.startsWith("/api/")) {
        event.respondWith(
            caches.match(event.request).then((cachedResponse) => cachedResponse || fetch(event.request))
        );
    }
});
