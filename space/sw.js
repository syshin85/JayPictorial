// Offline support. tools/build_web.py stamps VERSION, the file lists and HASHES at build time.
// Code and data live in a cache per VERSION, so a new deploy refreshes them (they are small).
// Photos live in one long-lived media cache keyed by their content hash, so a new
// deploy only downloads the photos that were added or changed, not every photo again.
const VERSION = "dev";
const CORE = ["./"]; // app shell, data and card thumbnails: needed before the app can open offline
const EXTRA = []; // every other photo: cached in the background after install
const HASHES = {}; // "assets/…" path -> short content hash

const CACHE = `jayspace-${VERSION}`;
const MEDIA = "jayspace-media";
const SCOPE = self.registration.scope;

const isMedia = (path) => path in HASHES;
// the media cache key carries the hash, so a changed file never matches its old copy
const mediaKey = (path) => `${SCOPE}${path}?h=${HASHES[path]}`;
const pathOf = (url) => (url.href.startsWith(SCOPE) ? url.href.slice(SCOPE.length).split(/[?#]/)[0] : null);

self.addEventListener("install", (event) => {
  event.waitUntil(
    (async () => {
      const cache = await caches.open(CACHE);
      // no-cache: ask the server, never take a stale copy from the browser's HTTP cache
      await cache.addAll(CORE.filter((p) => !isMedia(p)).map((p) => new Request(p, { cache: "no-cache" })));
      // keep photos saved by an older version (before the media cache existed): no re-download
      await adoptOldCopies([...CORE, ...EXTRA].filter(isMedia));
      await fetchMedia(CORE.filter(isMedia));
      await self.skipWaiting();
    })()
  );
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    (async () => {
      const keys = await caches.keys();
      await Promise.all(keys.filter((k) => k.startsWith("jayspace-") && k !== CACHE && k !== MEDIA).map((k) => caches.delete(k)));
      // drop media that was removed or replaced in this version
      const media = await caches.open(MEDIA);
      const wanted = new Set(Object.keys(HASHES).map(mediaKey));
      for (const req of await media.keys()) if (!wanted.has(req.url)) await media.delete(req);
      await self.clients.claim();
    })()
  );
  // Not awaited: the app is usable while the remaining photos download.
  fetchMedia(EXTRA.filter(isMedia));
});

async function adoptOldCopies(paths) {
  const keys = (await caches.keys()).filter((k) => k.startsWith("jayspace-") && k !== MEDIA);
  if (!keys.length) return;
  const media = await caches.open(MEDIA);
  for (const path of paths) {
    if (await media.match(mediaKey(path))) continue;
    for (const k of keys) {
      const old = await (await caches.open(k)).match(SCOPE + path);
      if (old) {
        await media.put(mediaKey(path), old);
        break;
      }
    }
  }
}

async function fetchMedia(paths) {
  const media = await caches.open(MEDIA);
  for (const path of paths) {
    if (await media.match(mediaKey(path))) continue;
    try {
      const res = await fetch(SCOPE + path, { cache: "no-cache" });
      if (res.ok) await media.put(mediaKey(path), res);
    } catch (_) {
      // offline or flaky network: it will be cached later when viewed
    }
  }
}

self.addEventListener("fetch", (event) => {
  const req = event.request;
  if (req.method !== "GET") return;
  const url = new URL(req.url);
  const path = pathOf(url);

  // Photos: the media cache first, then the network (and keep it).
  if (path && isMedia(path)) {
    event.respondWith(
      caches.open(MEDIA).then((media) =>
        media.match(mediaKey(path)).then(
          (hit) =>
            hit ||
            fetch(req).then((res) => {
              if (res.ok) media.put(mediaKey(path), res.clone());
              return res;
            })
        )
      )
    );
    return;
  }

  // Data: try the network first so edits show up, fall back to the cached copy offline.
  if (url.origin === location.origin && url.pathname.endsWith(".json")) {
    event.respondWith(
      fetch(req)
        .then((res) => {
          const copy = res.clone();
          caches.open(CACHE).then((c) => c.put(req, copy));
          return res;
        })
        .catch(() => caches.match(req))
    );
    return;
  }

  // Our own files and Google Fonts: cache first.
  if (url.origin === location.origin || url.hostname.endsWith("fonts.googleapis.com") || url.hostname.endsWith("fonts.gstatic.com")) {
    event.respondWith(
      caches.match(req, { ignoreSearch: url.origin === location.origin }).then(
        (hit) =>
          hit ||
          fetch(req).then((res) => {
            if (res.ok || res.type === "opaque") {
              const copy = res.clone();
              caches.open(CACHE).then((c) => c.put(req, copy));
            }
            return res;
          })
      )
    );
  }
  // Everything else goes straight to the network.
});
