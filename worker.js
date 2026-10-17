// The site is static files; this only takes readers' corrections (POST /api/fix) into the D1 table `fixes`
// (feedback.sql). Everything else is served from the assets as before. Review: see README / ask Claude.
const LIMIT = 20;  // corrections per visitor per day: enough for a careful reader, too few for a flood

export default {
  async fetch(request, env) {
    const url = new URL(request.url);
    if (url.pathname === '/api/view') return view(request, env);
    if (url.pathname !== '/api/fix') return env.ASSETS.fetch(request);
    if (request.method !== 'POST') return json({ error: 'method' }, 405);
    let d;
    try { d = await request.json(); } catch { return json({ error: 'format' }, 400); }
    const s = (v, max) => String(v ?? '').trim().slice(0, max);
    const fix = s(d.fix, 4000), fragment = s(d.fragment, 2000), comment = s(d.comment, 2000);
    if (d.website) return json({ ok: true });  // the hidden field only bots fill in
    if (!fix) return json({ error: 'empty' }, 400);
    // a daily hash of the address: enough to stop floods, nothing that identifies a person is stored
    const day = new Date().toISOString().slice(0, 10);
    const raw = new TextEncoder().encode(`${request.headers.get('cf-connecting-ip') || ''}|${day}|prym`);
    const visitor = [...new Uint8Array(await crypto.subtle.digest('SHA-256', raw))].slice(0, 8).map(b => b.toString(16).padStart(2, '0')).join('');
    const { n } = await env.DB.prepare("SELECT count(*) AS n FROM fixes WHERE visitor = ? AND created >= date('now')").bind(visitor).first();
    if (n >= LIMIT) return json({ error: 'limit' }, 429);
    const article = /^[0-9a-f]{10}$/.test(d.article || '') ? d.article : '';
    const page = s(d.page, 300).startsWith(url.origin) ? s(d.page, 300) : '';
    await env.DB.prepare('INSERT INTO fixes (article, page, fragment, fix, comment, visitor) VALUES (?, ?, ?, ?, ?, ?)')
      .bind(article, page, fragment, fix, comment, visitor).run();
    return json({ ok: true });
  },
};

// one more view of an article: its id and the day, nothing else (the page sends it once per article per browser session)
async function view(request, env) {
  if (request.method !== 'POST') return json({ error: 'method' }, 405);
  const n = (await request.text()).trim();
  if (!/^[0-9a-f]{10}$/.test(n)) return json({ error: 'id' }, 400);
  await env.DB.prepare("INSERT INTO views (article, day, n) VALUES (?, date('now'), 1) ON CONFLICT (article, day) DO UPDATE SET n = n + 1").bind(n).run();
  return new Response(null, { status: 204 });
}

const json = (body, status = 200) => new Response(JSON.stringify(body), { status, headers: { 'content-type': 'application/json; charset=utf-8' } });
