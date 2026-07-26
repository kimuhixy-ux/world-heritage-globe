// sw.js: オフライン閲覧のためのService Worker(キャッシュファースト)
// CACHE_VERSION を上げると古いキャッシュが破棄され、新しいファイルに置き換わります。
const CACHE_VERSION = "world-heritage-globe-v6";

// 同一オリジンの必須ファイル
const PRECACHE_URLS = [
  "./",
  "./index.html",
  "./manifest.json",
  "./css/style.css",
  "./js/app.js",
  "./data/heritage.json",
  "./icons/icon-192.png",
  "./icons/icon-512.png",
  "./img/earth-day.jpg",
  "./img/earth-bump.jpg",
  "./img/night-sky.png",
];

// Globe.gl本体(unpkgのCDN)。オフライン起動のため事前キャッシュする
const EXTERNAL_URLS = [
  "https://unpkg.com/globe.gl",
];

self.addEventListener("install", (event) => {
  event.waitUntil(
    caches.open(CACHE_VERSION).then(async (cache) => {
      await cache.addAll(PRECACHE_URLS);
      await Promise.all(
        EXTERNAL_URLS.map((url) =>
          fetch(url, { mode: "no-cors" })
            .then((res) => cache.put(url, res))
            .catch(() => {})
        )
      );
    })
  );
  self.skipWaiting();
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches.keys().then((keys) =>
      Promise.all(keys.filter((k) => k !== CACHE_VERSION).map((k) => caches.delete(k)))
    )
  );
  self.clients.claim();
});

self.addEventListener("fetch", (event) => {
  const { request } = event;
  if (request.method !== "GET") return;

  event.respondWith(
    caches.match(request).then((cached) => {
      if (cached) return cached;
      return fetch(request)
        .then((response) => {
          const clone = response.clone();
          caches.open(CACHE_VERSION).then((cache) => cache.put(request, clone));
          return response;
        })
        .catch(() => cached);
    })
  );
});
