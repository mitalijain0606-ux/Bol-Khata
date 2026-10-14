const CACHE = "bolkhata-v1";
const SHELL = ["/", "/index.html", "/manifest.webmanifest", "/icon-192.png", "/icon-512.png"];

self.addEventListener("install", (e) => {
  e.waitUntil(caches.open(CACHE).then((c) => c.addAll(SHELL)));
  self.skipWaiting();
});

self.addEventListener("fetch", (e) => {
  const url = new URL(e.request.url);
  if (url.pathname.startsWith("/api") || url.pathname.startsWith("/ws")) return; // never cache data
  e.respondWith(
    e.request.mode === "navigate"
      ? fetch(e.request).catch(() => caches.match("/index.html"))
      : caches.match(e.request).then((hit) => hit || fetch(e.request))
  );
});
