/* fatsecret-proxy — Cloudflare Worker for DishLog's chain-menu lookups
 *
 * FatSecret wants token requests to come from a server, not a phone, so the client secret
 * lives here. This Worker keeps NO nutrition data: nothing is written to KV, D1 or the
 * cache, and every reply is marked no-store. (FatSecret's rule for servers is a 24-hour
 * limit on raw nutrition; this stores none at all.) Only the OAuth token is kept, in memory.
 *
 * Setup (Cloudflare dashboard → this Worker → Settings → Variables and Secrets):
 *   FATSECRET_CLIENT_ID      secret
 *   FATSECRET_CLIENT_SECRET  secret
 *   PROXY_TOKEN              secret — any long random string; paste the same one into
 *                            DishLog → Log a dish → Lookup sources
 * Then, in FatSecret's dashboard (Manage API keys), add this Worker's outgoing IP range
 * to the key's allowed IPs if token requests are refused (see the "token" error below).
 *
 * GET /search?q=crunchwrap&brand=Taco%20Bell  → {results:[{id,name,brand,serving,calories,protein_g,carbs_g,fat_g}]}
 * GET /food?id=12345                          → {id,serving,calories,protein_g,carbs_g,fat_g}
 */

const ALLOWED_ORIGINS = ["https://frostie4life9.github.io"];
const API = "https://platform.fatsecret.com/rest";
const TOKEN_URL = "https://oauth.fatsecret.com/connect/token";

let tokenCache = { value: null, exp: 0 };   // OAuth token only — never nutrition

const norm = s => String(s || "").toLowerCase().replace(/[’']/g, "").replace(/[^a-z0-9]+/g, " ").trim();
const num = v => { const n = parseFloat(v); return Number.isFinite(n) ? n : null; };
const asArray = x => (x == null ? [] : Array.isArray(x) ? x : [x]);

async function getToken(env, force) {
  if (!force && tokenCache.value && Date.now() < tokenCache.exp - 60000) return tokenCache.value;
  const res = await fetch(TOKEN_URL, {
    method: "POST",
    headers: {
      Authorization: "Basic " + btoa(env.FATSECRET_CLIENT_ID + ":" + env.FATSECRET_CLIENT_SECRET),
      "Content-Type": "application/x-www-form-urlencoded",
    },
    body: "grant_type=client_credentials",   // no scope: FatSecret sends every scope the account has
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok || !data.access_token) {
    const e = new Error("token");
    e.detail = String(data.error_description || data.error || res.status).slice(0, 200);
    throw e;
  }
  tokenCache = { value: data.access_token, exp: Date.now() + (Number(data.expires_in) || 3600) * 1000 };
  return tokenCache.value;
}

async function fsGet(env, path, params) {
  const url = API + path + "?" + new URLSearchParams({ ...params, format: "json" });
  for (let attempt = 0; attempt < 2; attempt++) {
    const token = await getToken(env, attempt > 0);
    const res = await fetch(url, { headers: { Authorization: "Bearer " + token } });
    if (res.status === 401 && attempt === 0) continue;   // expired early — fetch a fresh token once
    const data = await res.json().catch(() => null);
    if (!res.ok) { const e = new Error("upstream"); e.detail = res.status; throw e; }
    if (data && data.error) { const e = new Error("upstream"); e.detail = String(data.error.message || data.error.code || "error").slice(0, 200); throw e; }
    return data;
  }
}

// "Per 1 item - Calories: 530kcal | Fat: 21.00g | Carbs: 71.00g | Protein: 16.00g"
function parseDescription(d) {
  d = String(d || "");
  const pick = re => { const m = d.match(re); return m ? num(m[1]) : null; };
  const s = d.match(/^Per\s+(.+?)\s+-\s/i);
  return {
    serving: s ? s[1] : "",
    calories: pick(/Calories:\s*([\d.]+)\s*kcal/i),
    fat_g: pick(/Fat:\s*([\d.]+)\s*g/i),
    carbs_g: pick(/Carbs:\s*([\d.]+)\s*g/i),
    protein_g: pick(/Protein:\s*([\d.]+)\s*g/i),
  };
}

async function search(env, q, brand) {
  const data = await fsGet(env, "/foods/search/v1", { search_expression: (brand + " " + q).trim(), max_results: "30", page_number: "0" });
  const rb = norm(brand);
  return asArray(data && data.foods && data.foods.food)
    .filter(f => f.food_type === "Brand" && (!rb || norm(f.brand_name).includes(rb) || rb.includes(norm(f.brand_name))))
    .slice(0, 8)
    .map(f => ({ id: String(f.food_id), name: f.food_name, brand: f.brand_name || "", ...parseDescription(f.food_description) }));
}

async function food(env, id) {
  const data = await fsGet(env, "/food/v6", { food_id: id });
  const servings = asArray(data && data.food && data.food.servings && data.food.servings.serving);
  const s = servings.find(x => x.is_default === "1") || servings[0];
  if (!s) return null;
  return {
    id: String(id), serving: s.serving_description || "", calories: num(s.calories),
    protein_g: num(s.protein), carbs_g: num(s.carbohydrate), fat_g: num(s.fat),
  };
}

export default {
  async fetch(req, env) {
    const origin = req.headers.get("Origin") || "";
    const cors = {
      "Access-Control-Allow-Origin": ALLOWED_ORIGINS.includes(origin) ? origin : ALLOWED_ORIGINS[0],
      "Access-Control-Allow-Methods": "GET, OPTIONS",
      "Access-Control-Allow-Headers": "Authorization",
      "Access-Control-Max-Age": "86400",
      "Vary": "Origin",
    };
    const json = (obj, status = 200) =>
      new Response(JSON.stringify(obj), { status, headers: { ...cors, "Content-Type": "application/json", "Cache-Control": "no-store" } });

    if (req.method === "OPTIONS") return new Response(null, { status: 204, headers: cors });
    if (req.method !== "GET") return json({ error: "use GET" }, 405);

    const auth = req.headers.get("Authorization") || "";
    if (!env.PROXY_TOKEN || auth !== "Bearer " + env.PROXY_TOKEN) return json({ error: "unauthorized" }, 401);
    if (!env.FATSECRET_CLIENT_ID || !env.FATSECRET_CLIENT_SECRET) return json({ error: "not configured" }, 500);

    const url = new URL(req.url);
    try {
      if (url.pathname === "/search") {
        const q = (url.searchParams.get("q") || "").trim().slice(0, 100);
        if (!q) return json({ error: "missing q" }, 400);
        return json({ results: await search(env, q, (url.searchParams.get("brand") || "").trim().slice(0, 60)) });
      }
      if (url.pathname === "/food") {
        const id = (url.searchParams.get("id") || "").trim();
        if (!/^\d{1,15}$/.test(id)) return json({ error: "bad id" }, 400);
        const f = await food(env, id);
        return f ? json(f) : json({ error: "not found" }, 404);
      }
      return json({ error: "not found" }, 404);
    } catch (e) {
      // "token" = FatSecret refused the token request (wrong keys, or this Worker's IP isn't allowed yet)
      return json({ error: e.message === "token" ? "token" : "upstream", detail: e.detail || "" }, 502);
    }
  },
};
