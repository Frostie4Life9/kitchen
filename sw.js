/* Offline support for the kitchen apps (Kitchen, Grocery, Lift, DishLog).

   Pages: network first, but give up after a couple of seconds and use the
   saved copy, so a weak signal in a store never leaves you staring at a blank
   page. Every successful load refreshes the saved copy.
   Fonts and icons: saved copy first (they never change), refreshed quietly.
   The new-version check (?_=…) and anything that isn't a GET always go
   straight to the network, so updates and sync behave exactly as before. */
const CACHE = "kitchen-2026.10.21-b";
const PAGES = ["./", "index.html", "grocery.html", "workout.html", "dishlog.html"];
const ASSETS = ["kitchen", "grocery", "lift", "dishlog"].flatMap(a => [
  "icons/" + a + "-32.png", "icons/" + a + "-180.png", "icons/" + a + "-192.png", a + ".webmanifest"]);

self.addEventListener("install", e => {
  e.waitUntil(caches.open(CACHE).then(c => Promise.all(PAGES.concat(ASSETS).map(u =>
    c.add(new Request(u, {cache: "reload"})).catch(() => {})))).then(() => self.skipWaiting()));
});
self.addEventListener("activate", e => {
  e.waitUntil(caches.keys().then(keys => Promise.all(keys.filter(k => k.startsWith("kitchen-") && k !== CACHE).map(k => caches.delete(k))))
    .then(() => self.clients.claim()));
});

function timeout(ms) { return new Promise((_, rej) => setTimeout(() => rej(new Error("slow")), ms)); }

self.addEventListener("fetch", e => {
  const req = e.request;
  if (req.method !== "GET") return;
  const url = new URL(req.url);
  if (url.searchParams.has("_")) return;                       // the update check: always live

  const isFont = /fonts\.(googleapis|gstatic)\.com$/.test(url.hostname);
  if (url.origin !== location.origin && !isFont) return;       // sync Worker, other sites: untouched

  const isPage = req.mode === "navigate" || /\.html?$/.test(url.pathname) || url.pathname.endsWith("/");
  if (isPage) {
    e.respondWith((async () => {
      const cache = await caches.open(CACHE);
      /* no-cache: always ask GitHub whether the page changed, so the browser's
         own cache can't hand back an older copy */
      const net = fetch(url.href, {cache: "no-cache", credentials: "same-origin"}).then(res => {
        if (res.ok) cache.put(url.pathname, res.clone());
        return res;
      });
      /* tapping Reload on the update bar (?v=…): wait for the fresh page,
         only fall back to the saved copy if there's no connection at all */
      if (url.searchParams.has("v")) {
        try { return await net; }
        catch (err) { return (await cache.match(url.pathname, {ignoreSearch: true})) || Response.error(); }
      }
      try { return await Promise.race([net, timeout(2500)]); }
      catch (err) {
        const saved = await cache.match(url.pathname, {ignoreSearch: true}) || await cache.match(req, {ignoreSearch: true});
        if (saved) { net.catch(() => {}); return saved; }
        return net;                                            // nothing saved yet: wait for the network
      }
    })());
    return;
  }

  // fonts, icons, manifests: saved copy first, refresh in the background
  e.respondWith((async () => {
    const cache = await caches.open(CACHE);
    const saved = await cache.match(req);
    const net = fetch(req).then(res => { if (res.ok || res.type === "opaque") cache.put(req, res.clone()); return res; }).catch(() => saved);
    return saved || net;
  })());
});
