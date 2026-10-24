/* =========================================================
   Ideas sync — one Cloudflare Worker + D1 for every app's "Ideas" list.

   What it does: each app's Ideas panel sends that app's whole list here,
   the Worker merges it into one table (newest edit wins, deletions are
   remembered so they don't come back from another device) and sends the
   merged list back. Claude reads and updates the same table directly.

   SETUP (dashboard, no command line)
   1. Compute > Workers & Pages > Create > Start with Hello World
        name it:  ideas-sync   -> Deploy
   2. Edit code -> delete everything -> paste this file -> Deploy
   3. Settings > Bindings > Add > D1 database
        Variable name: DB
        D1 database:   app-ideas   (already created)
   4. Settings > Variables and Secrets > Add
        Type:  Secret
        Name:  WRITE_KEY
        Value: the IDEAS_KEY value from tools/suite.py
   5. Deploy again. The Worker's address should be
        https://ideas-sync.skyfro04.workers.dev
      (it must match IDEAS_WORKER in tools/suite.py).

   Verify: open that address in a browser. {"ok":true,"service":"ideas-sync"}
   means it is live. Anything under /sync/ is refused without the key.

   The key sits in each app's page, so it only keeps strangers' scanners
   out; it is not a lock for secrets. This holds nothing but a wish list.
   ========================================================= */

const APPS = ['kitchen', 'grocery', 'lift', 'dishlog', 'protocol', 'rail', 'gamelog', 'playback'];
const MAX_BODY = 128 * 1024;
const MAX_ITEMS = 500;
const MAX_TEXT = 280;
const TOMBSTONE_MS = 30 * 24 * 60 * 60 * 1000;

const CORS = {
  'Access-Control-Allow-Origin': '*',
  'Access-Control-Allow-Methods': 'POST, GET, OPTIONS',
  'Access-Control-Allow-Headers': 'content-type, x-ideas-key',
  'Access-Control-Max-Age': '86400'
};

function reply(body, status) {
  return new Response(JSON.stringify(body), {
    status: status || 200,
    headers: Object.assign({ 'content-type': 'application/json', 'cache-control': 'no-store' }, CORS)
  });
}

/* length-independent compare, so response timing leaks nothing */
function keyMatches(given, want) {
  let ok = given.length === want.length;
  for (let i = 0; i < Math.max(given.length, want.length); i++) {
    if (given.charCodeAt(i) !== want.charCodeAt(i)) ok = false;
  }
  return ok;
}

function clean(raw) {
  if (!raw || typeof raw !== 'object') return null;
  const id = typeof raw.id === 'string' ? raw.id : '';
  if (!/^[A-Za-z0-9_-]{1,40}$/.test(id)) return null;
  const deleted = raw.deleted ? 1 : 0;
  const text = typeof raw.text === 'string' ? raw.text : '';
  if (text.length > MAX_TEXT) return null;
  if (!deleted && !text.trim()) return null;
  const t = Number(raw.t), u = Number(raw.u);
  if (!Number.isFinite(t) || !Number.isFinite(u) || t < 0 || u < 0) return null;
  return { id, text: deleted ? '' : text, done: raw.done ? 1 : 0, deleted, t: Math.round(t), u: Math.round(u) };
}

export default {
  async fetch(request, env) {
    if (request.method === 'OPTIONS') return new Response(null, { status: 204, headers: CORS });

    const url = new URL(request.url);
    if (url.pathname === '/' || url.pathname === '') {
      return reply({ ok: true, service: 'ideas-sync' });
    }

    const m = url.pathname.match(/^\/sync\/([a-z]+)$/);
    if (!m) return reply({ error: 'not found' }, 404);
    if (!env.DB) return reply({ error: 'server not configured: missing DB binding' }, 500);
    if (!env.WRITE_KEY) return reply({ error: 'server not configured: missing WRITE_KEY' }, 500);
    if (request.method !== 'POST') return reply({ error: 'method not allowed' }, 405);

    const given = (request.headers.get('x-ideas-key') || '').trim();
    if (!keyMatches(given, String(env.WRITE_KEY).trim())) return reply({ error: 'unauthorized' }, 401);

    const app = m[1];
    if (APPS.indexOf(app) < 0) return reply({ error: 'unknown app' }, 404);

    const body = await request.text();
    if (body.length > MAX_BODY) return reply({ error: 'payload too large' }, 413);
    let parsed;
    try { parsed = JSON.parse(body); } catch (e) { return reply({ error: 'body is not valid JSON' }, 400); }
    if (!parsed || !Array.isArray(parsed.items)) return reply({ error: 'expected {"items":[...]}' }, 400);
    if (parsed.items.length > MAX_ITEMS) return reply({ error: 'too many items' }, 413);

    const items = [];
    for (const raw of parsed.items) {
      const it = clean(raw);
      if (!it) return reply({ error: 'bad item' }, 400);
      items.push(it);
    }

    /* newest edit wins: an older copy never overwrites a newer one */
    const up = env.DB.prepare(
      'INSERT INTO ideas (app, id, text, done, deleted, t, u) VALUES (?, ?, ?, ?, ?, ?, ?) ' +
      'ON CONFLICT(app, id) DO UPDATE SET text = excluded.text, done = excluded.done, deleted = excluded.deleted, t = excluded.t, u = excluded.u ' +
      'WHERE excluded.u > ideas.u');
    const stmts = items.map(it => up.bind(app, it.id, it.text, it.done, it.deleted, it.t, it.u));
    stmts.push(env.DB.prepare('DELETE FROM ideas WHERE app = ? AND deleted = 1 AND u < ?').bind(app, Date.now() - TOMBSTONE_MS));
    await env.DB.batch(stmts);

    const rows = await env.DB.prepare(
      'SELECT id, text, done, deleted, t, u FROM ideas WHERE app = ? ORDER BY t DESC LIMIT ' + (MAX_ITEMS * 2)).bind(app).all();
    return reply({ ok: true, items: rows.results || [] });
  }
};
