// Offline support for the top "pick a pictorial" page only.
// Each pictorial (train/, …) has its own service worker; its pages are left alone here.
const CACHE = "jaypictorial-top";
const FILES = ["./", "manifest.webmanifest", "assets/icon.png", "assets/icon.svg"];

self.addEventListener("install", (event) => {
  event.waitUntil(
    caches
      .open(CACHE)
      .then((c) => c.addAll(FILES.map((f) => new Request(f, { cache: "no-cache" }))))
      .then(() => self.skipWaiting())
  );
});

self.addEventListener("activate", (event) => event.waitUntil(self.clients.claim()));

self.addEventListener("fetch", (event) => {
  const req = event.request;
  if (req.method !== "GET") return;
  const scope = self.registration.scope;
  const path = req.url.startsWith(scope) ? req.url.slice(scope.length).split(/[?#]/)[0] : null;
  if (path === null || !FILES.includes(path || "./")) return; // not ours (a pictorial's file, fonts…)

  // Network first so changes show up; the saved copy when offline.
  event.respondWith(
    fetch(req)
      .then((res) => {
        if (res.ok) {
          const copy = res.clone();
          caches.open(CACHE).then((c) => c.put(req, copy));
        }
        return res;
      })
      .catch(() => caches.match(req, { ignoreSearch: true }))
  );
});
