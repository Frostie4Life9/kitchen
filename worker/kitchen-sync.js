/* kitchen-sync — Cloudflare Worker for Skyler's kitchen app
 *
 * Setup (Cloudflare dashboard):
 *   1. KV namespace named "kitchen", bound to this Worker as  KITCHEN
 *   2. Secret named  SYNC_TOKEN  = your sync password
 *
 * One endpoint: POST /sync   body {since, keys:{name:{v,t}}}
 *   - v is the raw localStorage string (null = deleted), t is when it changed
 *   - each key is merged separately: the newer t wins
 *   - the reply holds every key the server stored after `since`, plus `at`
 *     to send as `since` next time
 * Before each change, the previous state is kept as "state_prev".
 */

const ALLOWED_ORIGINS = ["https://frostie4life9.github.io"];

export default {
  async fetch(req, env) {
    const origin = req.headers.get("Origin") || "";
    const cors = {
      "Access-Control-Allow-Origin": ALLOWED_ORIGINS.includes(origin) ? origin : ALLOWED_ORIGINS[0],
      "Access-Control-Allow-Methods": "POST, OPTIONS",
      "Access-Control-Allow-Headers": "Authorization, Content-Type",
      "Access-Control-Max-Age": "86400",
      "Vary": "Origin",
    };
    const json = (obj, status = 200) =>
      new Response(JSON.stringify(obj), { status, headers: { ...cors, "Content-Type": "application/json" } });

    if (req.method === "OPTIONS") return new Response(null, { status: 204, headers: cors });

    const auth = req.headers.get("Authorization") || "";
    if (!env.SYNC_TOKEN || auth !== "Bearer " + env.SYNC_TOKEN) return json({ error: "unauthorized" }, 401);

    const url = new URL(req.url);
    if (url.pathname !== "/sync") return json({ error: "not found" }, 404);
    if (req.method !== "POST") return json({ error: "use POST" }, 405);

    let body;
    try { body = await req.json(); } catch (e) { return json({ error: "bad json" }, 400); }
    const incoming = (body && body.keys) || {};
    const since = Number(body && body.since) || 0;

    const raw = await env.KITCHEN.get("state");
    const stored = raw ? JSON.parse(raw) : { at: 0, keys: {} };
    const now = Math.max(Date.now(), (stored.at || 0) + 1);

    let changed = false;
    for (const k of Object.keys(incoming)) {
      const e = incoming[k];
      if (!e || typeof e.t !== "number" || (e.v !== null && typeof e.v !== "string")) continue;
      const cur = stored.keys[k];
      if (!cur || e.t > cur.t) { stored.keys[k] = { v: e.v, t: e.t, s: now }; changed = true; }
    }
    if (changed) {
      if (raw) await env.KITCHEN.put("state_prev", raw);
      stored.at = now;
      await env.KITCHEN.put("state", JSON.stringify(stored));
    }

    const out = {};
    for (const k of Object.keys(stored.keys)) {
      /* changed since the device last synced, or something it just sent (so it
         learns the outcome either way and stops resending it) */
      if ((stored.keys[k].s || 0) > since || k in incoming) out[k] = { v: stored.keys[k].v, t: stored.keys[k].t };
    }
    return json({ at: stored.at || 0, keys: out });
  },
};
