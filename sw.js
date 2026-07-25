// おかいものメモ Service Worker
// 方針: ページ本体はネットワーク優先（更新が自動で届く）、
//       アイコン等の静的資産はキャッシュ優先、APIは対象外
const CACHE = "okaimono-v1";
const CORE = ["./index.html", "./manifest.webmanifest", "./icon-192.png", "./icon-512.png"];

self.addEventListener("install", (e) => {
  e.waitUntil(caches.open(CACHE).then((c) => c.addAll(CORE)).then(() => self.skipWaiting()));
});
self.addEventListener("activate", (e) => {
  e.waitUntil(
    caches.keys().then((keys) => Promise.all(keys.filter((k) => k !== CACHE).map((k) => caches.delete(k))))
      .then(() => self.clients.claim())
  );
});
self.addEventListener("fetch", (e) => {
  const url = new URL(e.request.url);
  if (e.request.method !== "GET") return;
  if (url.hostname === "api.anthropic.com") return; // APIはキャッシュしない

  // ページ遷移（index.html）: ネットワーク優先 → 失敗時のみキャッシュ
  if (e.request.mode === "navigate") {
    e.respondWith(
      fetch(e.request)
        .then((res) => {
          const copy = res.clone();
          caches.open(CACHE).then((c) => c.put("./index.html", copy));
          return res;
        })
        .catch(() => caches.match("./index.html"))
    );
    return;
  }

  // その他（アイコン・フォント等）: キャッシュ優先 → 無ければ取得してキャッシュ
  e.respondWith(
    caches.match(e.request).then(
      (hit) =>
        hit ||
        fetch(e.request).then((res) => {
          if (res.ok) {
            const copy = res.clone();
            caches.open(CACHE).then((c) => c.put(e.request, copy));
          }
          return res;
        })
      // 取得失敗時はそのままエラーにする（誤ったフォールバックはしない）
    )
  );
});
