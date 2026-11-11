// node test_worker.mjs — worker.js against a fake D1 and fake assets: origin, size, bait field, villages, limits, views
import assert from 'node:assert/strict';
import worker from './worker.js';

const rows = { fixes: [], memories: [], views: 0, updates: [] };
const DB = {
  prepare(sql) {
    let args = [];
    const st = {
      bind(...a) { args = a; return st; },
      async first() {
        const t = rows[sql.match(/FROM (\w+)/)[1]];
        return { n: t.length, mine: t.filter(r => r.visitor === args[0]).length };
      },
      async run() {
        if (sql.startsWith('UPDATE')) rows.updates.push(args);
        else if (sql.startsWith('INSERT INTO views')) rows.views++;
        else rows[sql.match(/INTO (\w+)/)[1]].push({ visitor: args.at(-1) });
      },
      async all() { return { results: sql.includes('FROM memories') ? [{ id: 7, kind: 'memory', village: 'Приморськ', text: '<b>море</b>', name: 'Ірина Д.', created: 'x' }] : [] }; },
    };
    return st;
  },
};
const ASSETS = {
  async fetch(req) {
    const path = new URL(req.url ?? req).pathname;
    if (path === '/memories-map.json') return new Response(JSON.stringify({ villages: [{ name: 'Приморськ' }] }));
    return new Response(null, { status: path === '/p/0123456789' ? 200 : 404 });
  },
};
const env = { DB, ASSETS, SALT: 'test' };
const O = 'https://prym.mydom.website';
const post = (path, body, { origin = O, ip = '1.1.1.1' } = {}) => worker.fetch(new Request(O + path, {
  method: 'POST', body: typeof body === 'string' ? body : JSON.stringify(body), headers: { origin, 'cf-connecting-ip': ip } }), env);

assert.equal((await post('/api/fix', { fix: 'x' }, { origin: 'https://evil.example' })).status, 403);
assert.equal((await post('/api/fix', 'x'.repeat(20000))).status, 413);
assert.equal((await post('/api/fix', 'not json')).status, 400);
assert.equal((await post('/api/fix', { fix: 'x', website: 'bot' })).status, 200);
assert.equal(rows.fixes.length, 0, 'the bait field stores nothing');
assert.equal((await post('/api/memory', { village: 'Москва', text: 'спогад' })).status, 400);
for (let i = 0; i < 10; i++) assert.equal((await post('/api/memory', { village: 'Приморськ', text: 'спогад' })).status, 200);
assert.equal((await post('/api/memory', { village: 'Приморськ', text: 'спогад' })).status, 429, 'per visitor');
for (let i = 0; i < 290; i++) await post('/api/memory', { village: 'Приморськ', text: 'спогад' }, { ip: `2.2.${i >> 8}.${i & 255}` });
assert.equal((await post('/api/memory', { village: 'Приморськ', text: 'спогад' }, { ip: '9.9.9.9' })).status, 429, 'for everyone in a day');
assert.equal((await post('/api/view', 'ffffffffff')).status, 404, 'no such article');
assert.equal((await post('/api/view', '0123456789')).status, 204);
assert.equal(rows.views, 1);
let left = 2;  // the VIEWS rate limit: two more views pass, the third does not
const envV = { ...env, VIEWS: { async limit({ key }) { assert.equal(key, '1.1.1.1'); return { success: left-- > 0 }; } } };
const viewV = () => worker.fetch(new Request(O + '/api/view', { method: 'POST', body: '0123456789', headers: { origin: O, 'cf-connecting-ip': '1.1.1.1' } }), envV);
assert.deepEqual([(await viewV()).status, (await viewV()).status, (await viewV()).status], [204, 204, 429]);
assert.equal(rows.views, 3);
assert.equal((await worker.fetch(new Request(O + '/api/fix'), env)).status, 405);
// Turnstile: with a secret set, a form needs a token that Cloudflare confirms for this form and this site; any doubt is a no
const envT = { ...env, TURNSTILE_SECRET: 's' };
let verdict = { success: true, action: 'fix', hostname: 'prym.mydom.website' }, asked;
const realFetch = globalThis.fetch;
globalThis.fetch = async (u, init) => { asked = [String(u), Object.fromEntries(init.body)]; if (!verdict) throw new Error('down'); return new Response(JSON.stringify(verdict)); };
const fixT = body => worker.fetch(new Request(O + '/api/fix', { method: 'POST', body: JSON.stringify(body), headers: { origin: O, 'cf-connecting-ip': '7.7.7.7' } }), envT);
const before = rows.fixes.length;
assert.equal((await fixT({ fix: 'x' })).status, 403, 'no token');
assert.equal((await fixT({ fix: 'x', token: 't' })).status, 200);
assert.deepEqual(asked, ['https://challenges.cloudflare.com/turnstile/v0/siteverify', { secret: 's', response: 't', remoteip: '7.7.7.7' }]);
for (const bad of [{ success: false }, { success: true, action: 'memory', hostname: 'prym.mydom.website' }, { success: true, action: 'fix', hostname: 'evil.example' }, null]) {
  verdict = bad;
  assert.equal((await fixT({ fix: 'x', token: 't' })).status, 403, JSON.stringify(bad));
}
assert.equal(rows.fixes.length, before + 1, 'only the confirmed one is stored');
globalThis.fetch = realFetch;
// the moderation page: no key, no page; a password; no foreign forms; the text is escaped; an approval updates one row
const get = (path, auth, e = env) => worker.fetch(new Request(O + path, { headers: auth ? { authorization: 'Basic ' + btoa('a:' + auth) } : {} }), e);
assert.equal((await get('/admin', 'k', { ...env })).status, 404, 'no ADMIN_KEY: no page');
const envA = { ...env, ADMIN_KEY: 'secret' };
assert.equal((await get('/admin', null, envA)).status, 401);
assert.equal((await get('/admin', 'wrong', envA)).status, 401);
const page = await (await get('/admin', 'secret', envA)).text();
assert.ok(page.includes('&lt;b&gt;море') && !page.includes('<b>море'), 'texts are escaped');
const form = (origin, fields) => worker.fetch(new Request(O + '/admin', { method: 'POST', body: new URLSearchParams(fields),
  headers: { origin, authorization: 'Basic ' + btoa('a:secret') } }), envA);
assert.equal((await form('https://evil.example', { table: 'memories', id: '7', status: 'approved' })).status, 403);
assert.equal((await form(O, { table: 'views', id: '7', status: 'approved' })).status, 400);
assert.equal((await form(O, { table: 'memories', id: '7', status: 'approved', name: 'Оксана Гончар', text: '' })).status, 303);
assert.deepEqual(rows.updates.at(-1), ['approved', 'Оксана Г.', '', '', 7]);
console.log('ok');
