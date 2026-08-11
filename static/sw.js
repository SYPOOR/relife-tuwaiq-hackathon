const CACHE_NAME = "relife-shell-v28";
const APP_SHELL = [
    "/",
    "/community",
    "/impact",
    "/static/style.css",
    "/static/app.js",
    "/static/assets/logo.png",
    "/static/assets/onboarding-hero.webp",
    "/static/assets/welcome-illustration.png"
];

self.addEventListener("install", function (event) {
    event.waitUntil(
        caches.open(CACHE_NAME).then(function (cache) {
            return cache.addAll(APP_SHELL);
        })
    );
    self.skipWaiting();
});

self.addEventListener("activate", function (event) {
    event.waitUntil(
        caches.keys().then(function (names) {
            return Promise.all(
                names.filter(function (name) {
                    return name !== CACHE_NAME;
                }).map(function (name) {
                    return caches.delete(name);
                })
            );
        })
    );
    self.clients.claim();
});

self.addEventListener("fetch", function (event) {
    if (event.request.method !== "GET") return;

    const url = new URL(event.request.url);
    if (url.origin !== self.location.origin) return;

    if (url.pathname.startsWith("/static/")) {
        event.respondWith(
            caches.match(event.request).then(function (cached) {
                const update = fetch(event.request).then(function (response) {
                    if (response.ok) {
                        const copy = response.clone();
                        caches.open(CACHE_NAME).then(function (cache) {
                            cache.put(event.request, copy);
                        });
                    }
                    return response;
                }).catch(function () {
                    return cached;
                });
                return cached || update;
            })
        );
        return;
    }

    event.respondWith(
        fetch(event.request).catch(function () {
            return caches.match(event.request) || caches.match("/");
        })
    );
});
