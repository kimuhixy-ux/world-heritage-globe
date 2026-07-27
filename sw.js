// sw.js: オフライン閲覧のためのService Worker(キャッシュファースト)
// CACHE_VERSION を上げると古いキャッシュが破棄され、新しいファイルに置き換わります。
const CACHE_VERSION = "world-heritage-globe-v13-cmp";

// 同一オリジンの必須ファイル
const PRECACHE_URLS = [
  "./",
  "./index.html",
  "./manifest.json",
  "./css/style.css",
  "./css/page.css",
  "./about.html",
  "./privacy.html",
  "./js/i18n.js",
  "./js/strings.js",
  "./js/config.js",
  "./js/app.js",
  "./js/ui-info.js",
  "./js/donate.js",
  "./js/ads.js",
  "./data/heritage.json",
  "./icons/icon-192.png",
  "./icons/icon-512.png",
  "./img/earth-day.jpg",
  "./img/earth-bump.jpg",
  "./img/night-sky.png",
  "./en/index.html",
  "./en/about.html",
  "./en/privacy.html",
  "./en/manifest.json",
];

// Globe.gl本体(unpkgのCDN)。オフライン起動のため事前キャッシュする
const EXTERNAL_URLS = [
  "https://unpkg.com/globe.gl",
];

// Cloudflare Pagesは*.htmlパスを拡張子なしの正規URLへ308リダイレクトするため、
// リダイレクト後のレスポンス(response.redirected === true)はキャッシュしない。
// これをキャッシュすると、後続のナビゲーションリクエストにrespondWith()で
// 返した際にChromeがnet::ERR_FAILEDで拒否する。
async function precache(cache, urls) {
  await Promise.all(
    urls.map(async (url) => {
      try {
        const response = await fetch(url);
        if (response.ok && !response.redirected) {
          await cache.put(url, response);
        }
      } catch (e) {
        // オフライン等でプリキャッシュに失敗しても致命的ではない
      }
    })
  );
}

self.addEventListener("install", (event) => {
  event.waitUntil(
    caches.open(CACHE_VERSION).then(async (cache) => {
      await precache(cache, PRECACHE_URLS);
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
          // リダイレクト先のレスポンスはキャッシュしない(理由は上記precache参照)
          if (!response.redirected) {
            const clone = response.clone();
            caches.open(CACHE_VERSION).then((cache) => cache.put(request, clone));
          }
          return response;
        })
        .catch(() => cached);
    })
  );
});
