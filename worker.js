// The site is static files; this only takes readers' corrections (POST /api/fix) into the D1 table `fixes`
// (feedback.sql), article views, and memories and dreams for the map (POST /api/memory into `memories`, GET
// /api/memories: the approved ones). Everything else is served from the assets as before. Review: see README / ask Claude.
const LIMIT = 20;         // corrections per visitor per day: enough for a careful reader, too few for a flood
const MEMORY_LIMIT = 10;  // memories per visitor per day
const DAY_LIMIT = 300;    // corrections or memories from everyone in a day: a flood from many addresses stops here too
const MAX_BODY = 16384;   // bytes: the longest form is ~7 000 characters of Cyrillic

export default {
  async fetch(request, env) {
    const url = new URL(request.url);
    const api = { '/api/view': view, '/api/memory': memory, '/api/fix': fix }[url.pathname];
    if (url.pathname === '/api/memories') return memories(env);
    if (url.pathname === '/admin' || url.pathname.startsWith('/admin/')) return admin(request, env, url);
    if (!api) return env.ASSETS.fetch(request);
    if (request.method !== 'POST') return json({ error: 'method' }, 405);
    // only our own pages send these: another site can't make its visitors' browsers post here
    if (request.headers.get('origin') !== url.origin) return json({ error: 'origin' }, 403);
    const text = await request.text();
    if (text.length > MAX_BODY) return json({ error: 'size' }, 413);
    return api(text, request, env, url);
  },
};

const s = (v, max) => String(v ?? '').trim().slice(0, max);
const parse = text => { try { const d = JSON.parse(text); return d && typeof d === 'object' ? d : null; } catch { return null; } };

// a reader's correction; applied by hand after review
async function fix(text, request, env, url) {
  const d = parse(text);
  if (!d) return json({ error: 'format' }, 400);
  if (d.website) return json({ ok: true });  // the hidden field only bots fill in
  const fix = s(d.fix, 4000), fragment = s(d.fragment, 2000), comment = s(d.comment, 2000);
  if (!fix) return json({ error: 'empty' }, 400);
  if (!await human(d, request, env, url, 'fix')) return json({ error: 'human' }, 403);
  const visitor = await visitorOf(request, env);
  if (await over(env, 'fixes', visitor, LIMIT)) return json({ error: 'limit' }, 429);
  const article = /^[0-9a-f]{10}$/.test(d.article || '') ? d.article : '';
  const page = s(d.page, 300).startsWith(url.origin) ? s(d.page, 300) : '';
  await env.DB.prepare('INSERT INTO fixes (article, page, fragment, fix, comment, visitor) VALUES (?, ?, ?, ?, ?, ?)')
    .bind(article, page, fragment, fix, comment, visitor).run();
  return json({ ok: true });
}

// Cloudflare Turnstile (timeline/human.js): the form's one-time token must be a real one, for this form and this site.
// No TURNSTILE_SECRET (tests, a fresh copy): no check. Any doubt, a timeout included, is a no
async function human(d, request, env, url, action) {
  if (!env.TURNSTILE_SECRET) return true;
  const token = d.token;
  if (typeof token !== 'string' || !token || token.length > 2048) return false;
  try {
    const r = await fetch('https://challenges.cloudflare.com/turnstile/v0/siteverify', { method: 'POST', signal: AbortSignal.timeout(10000),
      body: new URLSearchParams({ secret: env.TURNSTILE_SECRET, response: token, remoteip: request.headers.get('cf-connecting-ip') || '' }) });
    const v = r.ok ? await r.json() : {};
    return v.success === true && v.action === action && v.hostname === url.hostname;
  } catch { return false; }
}

// over the visitor's or everyone's limit for today (`table` is one of ours, never from the request)
async function over(env, table, visitor, limit) {
  const r = await env.DB.prepare(`SELECT count(*) AS n, sum(visitor = ?) AS mine FROM ${table} WHERE created >= date('now')`).bind(visitor).first();
  return r.n >= DAY_LIMIT || (r.mine || 0) >= limit;
}

// a daily hash of the address: enough to stop floods. The salt is a secret of the worker (wrangler secret put SALT),
// so the hash can't be turned back into an address by trying them all; nothing that identifies a person is stored
async function visitorOf(request, env) {
  const day = new Date().toISOString().slice(0, 10);
  const raw = new TextEncoder().encode(`${request.headers.get('cf-connecting-ip') || ''}|${day}|${env.SALT || 'prym'}`);
  return [...new Uint8Array(await crypto.subtle.digest('SHA-256', raw))].slice(0, 8).map(b => b.toString(16).padStart(2, '0')).join('');
}

// «Ірина Дмитренко» -> «Ірина Д.»: the portal never shows a private person's surname (the page does it too)
const short = full => { const w = full.trim().split(/\s+/).filter(Boolean); return !w.length ? '' : w.length === 1 ? w[0] : `${w[0]} ${w.at(-1)[0].toUpperCase()}.`; };

// the villages the map knows (memories-map.json): a memory from anywhere else would never be shown
let VILLAGES;
const villages = async (env, url) => VILLAGES ??= env.ASSETS.fetch(new URL('/memories-map.json', url))
  .then(r => r.json()).then(m => new Set(m.villages.map(v => v.name))).catch(() => { VILLAGES = undefined; return null; });

// a memory or a dream from the map's form; it waits for the author's approval (status 'new')
async function memory(text, request, env, url) {
  const d = parse(text);
  if (!d) return json({ error: 'format' }, 400);
  if (d.website) return json({ ok: true });  // the hidden field only bots fill in
  const kind = d.kind === 'dream' ? 'dream' : 'memory', village = s(d.village, 80), body = s(d.text, 800), name = short(s(d.name, 60)).slice(0, 40);
  const year = kind === 'memory' && /^(19|20)\d\d$/.test(String(d.year)) ? +d.year : null;
  if (!village || body.length < 3) return json({ error: 'empty' }, 400);
  const known = await villages(env, url);
  if (known && !known.has(village)) return json({ error: 'village' }, 400);
  if (!await human(d, request, env, url, 'memory')) return json({ error: 'human' }, 403);
  const visitor = await visitorOf(request, env);
  if (await over(env, 'memories', visitor, MEMORY_LIMIT)) return json({ error: 'limit' }, 429);
  await env.DB.prepare('INSERT INTO memories (kind, village, text, name, year, visitor) VALUES (?, ?, ?, ?, ?, ?)').bind(kind, village, body, name, year, visitor).run();
  return json({ ok: true });
}

// the approved memories and dreams, for the map (cached for a minute at the edge)
async function memories(env) {
  const { results } = await env.DB.prepare("SELECT id, kind, village, text, name, year FROM memories WHERE status = 'approved' ORDER BY id").all();
  return new Response(JSON.stringify(results), { headers: { 'content-type': 'application/json; charset=utf-8', 'cache-control': 'public, max-age=60' } });
}

// one more view of an article: its id and the day, nothing else (the page sends it once per article per browser session);
// only an article that exists counts, and at most 30 a minute from one address (the VIEWS rate limit in wrangler.jsonc;
// the address is not stored)
async function view(text, request, env, url) {
  const n = text.trim();
  if (!/^[0-9a-f]{10}$/.test(n)) return json({ error: 'id' }, 400);
  if (env.VIEWS && !(await env.VIEWS.limit({ key: request.headers.get('cf-connecting-ip') || '' })).success) return json({ error: 'limit' }, 429);
  const page = await env.ASSETS.fetch(new Request(new URL(`/p/${n}`, url), { method: 'HEAD' }));
  if (!page.ok) return json({ error: 'id' }, 404);
  await env.DB.prepare("INSERT INTO views (article, day, n) VALUES (?, date('now'), 1) ON CONFLICT (article, day) DO UPDATE SET n = n + 1").bind(n).run();
  return new Response(null, { status: 204 });
}

const json = (body, status = 200) => new Response(JSON.stringify(body), { status, headers: { 'content-type': 'application/json; charset=utf-8' } });

// ── /admin: the author's moderation page (HTTP Basic, password = the worker secret ADMIN_KEY; no key, no page) ──────────
const same = (a, b) => a.length === b.length && [...a].reduce((d, c, i) => d | (c.charCodeAt(0) ^ b.charCodeAt(i)), 0) === 0;
const authorised = (request, env) => {
  const m = (request.headers.get('authorization') || '').match(/^Basic (.+)$/);
  if (!m || !env.ADMIN_KEY) return false;
  try { return same(atob(m[1]).split(':').slice(1).join(':'), env.ADMIN_KEY); } catch { return false; }
};
const esc = v => String(v ?? '').replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' })[c]);

async function admin(request, env, url) {
  if (!env.ADMIN_KEY) return env.ASSETS.fetch(new Request(new URL('/404', url)));
  if (!authorised(request, env)) return new Response('Потрібен пароль', { status: 401, headers: { 'www-authenticate': 'Basic realm="prym admin", charset="UTF-8"' } });
  if (request.method === 'POST') {
    if (request.headers.get('origin') !== url.origin) return json({ error: 'origin' }, 403);
    const f = await request.formData();
    const id = +f.get('id'), table = f.get('table'), status = f.get('status');
    const allowed = { memories: ['approved', 'rejected'], fixes: ['applied', 'rejected'] };
    if (!allowed[table]?.includes(status) || !id) return json({ error: 'bad' }, 400);
    if (table === 'memories') {
      const name = short(String(f.get('name') ?? '').slice(0, 60)).slice(0, 40), text = String(f.get('text') ?? '').trim().slice(0, 800);
      await env.DB.prepare("UPDATE memories SET status = ?, name = ?, text = CASE WHEN ? = '' THEN text ELSE ? END WHERE id = ?").bind(status, name, text, text, id).run();
    } else {
      await env.DB.prepare('UPDATE fixes SET status = ? WHERE id = ?').bind(status, id).run();
    }
    return Response.redirect(new URL('/admin', url), 303);
  }
  const mem = (await env.DB.prepare("SELECT id, created, kind, village, text, name, year FROM memories WHERE status = 'new' ORDER BY id").all()).results;
  const fx = (await env.DB.prepare("SELECT id, created, article, page, fragment, fix, comment FROM fixes WHERE status = 'new' ORDER BY id").all()).results;
  const btn = (status, label) => `<button name="status" value="${status}" formaction="/admin" class="${status}">${label}</button>`;
  const memRow = r => `<form method="post" class="card"><input type="hidden" name="table" value="memories"><input type="hidden" name="id" value="${r.id}">
    <p class="meta">${r.kind === 'dream' ? 'Мрія' : 'Спогад'} · ${esc(r.village)}${r.year ? ' · ' + r.year : ''} · надіслано ${esc(r.created)} UTC</p>
    <label>Текст<textarea name="text" rows="5">${esc(r.text)}</textarea></label>
    <label>Підпис (скорочується до «Ім'я П.»)<input name="name" value="${esc(r.name)}"></label>
    <p>${btn('approved', 'Схвалити й показати на мапі')} ${btn('rejected', 'Відхилити')}</p></form>`;
  const fixRow = r => `<form method="post" class="card"><input type="hidden" name="table" value="fixes"><input type="hidden" name="id" value="${r.id}">
    <p class="meta">${r.article ? `<a href="/p/${esc(r.article)}" target="_blank">стаття ${esc(r.article)}</a>` : esc(r.page) || 'без статті'} · ${esc(r.created)} UTC</p>
    ${r.fragment ? `<p><b>Було:</b> ${esc(r.fragment)}</p>` : ''}<p><b>Має бути:</b> ${esc(r.fix)}</p>${r.comment ? `<p><b>Коментар:</b> ${esc(r.comment)}</p>` : ''}
    <p>${btn('applied', 'Внесено')} ${btn('rejected', 'Відхилити')}</p></form>`;
  const page = `<!doctype html><html lang="uk"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="robots" content="noindex"><title>Модерація · Приморськ</title><style>
body { margin: 0; padding: 16px; font: 16px/1.5 system-ui, sans-serif; background: #f5efe4; color: #10261f; } main { max-width: 760px; margin: 0 auto; }
h1 { font-size: 24px; } h2 { font-size: 19px; margin-top: 32px; } .card { background: #fffaf2; border-radius: 14px; padding: 14px 16px; margin: 12px 0; box-shadow: 0 1px 3px #0001; }
.meta { color: #5d6a6c; font-size: 14px; margin: 0 0 8px; } label { display: block; font-size: 14px; color: #5d6a6c; margin: 8px 0; }
textarea, input { display: block; width: 100%; box-sizing: border-box; font: 16px/1.5 system-ui, sans-serif; padding: 8px; border: 1px solid #d8ccb5; border-radius: 8px; margin-top: 4px; }
button { font: 600 15px system-ui, sans-serif; padding: 10px 16px; min-height: 44px; border: 0; border-radius: 10px; cursor: pointer; }
.approved, .applied { background: #174f3e; color: #fff; } .rejected { background: #e9dfcc; color: #10261f; } .empty { color: #5d6a6c; }
</style></head><body><main><h1>Модерація</h1>
<p class="meta">Спогад з'являється на мапі за хвилину після схвалення. Текст і підпис можна виправити перед схваленням.</p>
<h2>Спогади й мрії: ${mem.length}</h2>${mem.map(memRow).join('') || '<p class="empty">Нових немає.</p>'}
<h2>Правки читачів: ${fx.length}</h2>${fx.map(fixRow).join('') || '<p class="empty">Нових немає.</p>'}
</main></body></html>`;
  return new Response(page, { headers: { 'content-type': 'text/html; charset=utf-8', 'cache-control': 'no-store', 'x-frame-options': 'DENY' } });
}
