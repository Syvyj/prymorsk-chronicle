// Records the memories map in motion for the Facebook video: 1080x1350, captions and a soft cursor injected into the page.
// node record.mjs <url> <out.webm> <events.json>
import puppeteer from 'puppeteer-core';
import fs from 'fs';

const [url, out, evOut] = process.argv.slice(2);
const sleep = ms => new Promise(r => setTimeout(r, ms));
const browser = await puppeteer.launch({
  executablePath: '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome', headless: true,
  args: ['--hide-scrollbars', '--force-device-scale-factor=1'], defaultViewport: { width: 1080, height: 1350, deviceScaleFactor: 1 },
});
const page = await browser.newPage();
await page.goto(url, { waitUntil: 'networkidle0' });

// overlay: a full cream card for the opening and the ending, a caption pill, a soft cursor
await page.addStyleTag({ content: `
  #vo { position: fixed; inset: 0; z-index: 100; background: #f7efe0; display: grid; place-items: center; text-align: center; transition: opacity 1.2s ease; pointer-events: none; }
  #vo h2 { margin: 0; font: 600 108px/1 'Mak', serif; } #vo h2 .a { color: #e0962f } #vo h2 .b { color: #5d8fbd } #vo h2 .and { color: #b49d76; font-size: .62em; }
  #vo .quote { margin: 0 auto 54px; max-width: 900px; font: 600 64px/1.2 'Mak', serif; color: #6b5a45; }
  #vo .w { display: inline-block; opacity: 0; translate: 0 18px; transition: opacity 1s ease, translate 1.2s ease; }
  #vo .w.in { opacity: 1; translate: 0 0; }
  #vo p { margin: 26px auto 0; max-width: 820px; font: italic 400 40px/1.4 'Lora', serif; color: #5b4e3f; }
  #vo .url { margin-top: 40px; font: 600 34px 'Commissioner', sans-serif; color: #3a3127; font-style: normal; }
  #cap { position: fixed; z-index: 90; left: 50%; bottom: 70px; translate: -50% 0; max-width: 940px; padding: 22px 34px; border-radius: 22px; background: rgba(58,49,39,.88);
    color: #fdf6e8; font: italic 400 40px/1.35 'Lora', serif; text-align: center; opacity: 0; transition: opacity .7s ease, translate .7s ease; pointer-events: none; }
  #cap.on { opacity: 1; translate: -50% -8px; }
  #cur { position: fixed; z-index: 95; width: 30px; height: 30px; margin: -15px 0 0 -15px; border-radius: 50%; border: 3px solid rgba(58,49,39,.75); background: rgba(255,255,255,.35);
    pointer-events: none; transition: transform .15s ease; left: -100px; top: -100px; }
  #cur.down { transform: scale(.7); background: rgba(217,130,43,.45); }` });
await page.evaluate(() => {
  document.body.insertAdjacentHTML('beforeend', '<div id="vo"></div><div id="cap"></div><div id="cur"></div>');
  addEventListener('mousemove', e => { const c = document.getElementById('cur'); c.style.left = e.clientX + 'px'; c.style.top = e.clientY + 'px'; });
  addEventListener('mousedown', () => document.getElementById('cur').classList.add('down'));
  addEventListener('mouseup', () => document.getElementById('cur').classList.remove('down'));
});
const vo = (html, on = true) => page.evaluate((h, o) => { const v = document.getElementById('vo'); if (h !== null) v.innerHTML = h; v.style.opacity = o ? 1 : 0; }, html, on);
const cap = text => page.evaluate(t => { const c = document.getElementById('cap'); if (t) { c.textContent = t; c.classList.add('on'); } else c.classList.remove('on'); }, text);
let mx = 540, my = 700;
async function glide(x, y, ms = 900) {  // a human-ish cursor path with easing
  const x0 = mx, y0 = my, s0 = Date.now();
  for (;;) { const t = Math.min(1, (Date.now() - s0) / ms), e = t < .5 ? 2 * t * t : 1 - (-2 * t + 2) ** 2 / 2; await page.mouse.move(x0 + (x - x0) * e, y0 + (y - y0) * e); if (t >= 1) break; await sleep(10); }
  mx = x; my = y;
}
const center = sel => page.evaluate(s => { const b = eval(s).getBoundingClientRect(); return [b.left + b.width / 2, b.top + b.height / 2]; }, sel);
const villageAt = name => page.evaluate(n => { const v = M.villages.find(v => v.name === n); const p = new DOMPoint(v.x, v.y).matrixTransform(map.getScreenCTM()); return [p.x, p.y]; }, name);
async function closeCard() {
  const x = await center("document.querySelector('#card [data-close]')");
  await click(...x);
  await page.waitForFunction(() => !document.getElementById('card').classList.contains('on'), { timeout: 5000 }).catch(() => {});
  await page.evaluate(() => unpreview());
}
async function click(x, y) { await glide(x, y); await sleep(250); await page.mouse.down(); await sleep(120); await page.mouse.up(); }

// start on the opening card; reload the map under it so the lights come in one by one while it fades
await vo('<div><h2><span class="a">Спогади</span> <span class="and">та</span> <span class="b">мрії</span></h2><p>Нова сторінка хроніки Приморська</p></div>');
const events = [];
// frames straight from the compositor with their own timestamps (the recorder's fixed-rate output drifted)
fs.rmSync('frames', { recursive: true, force: true }); fs.mkdirSync('frames');
const client = await page.createCDPSession(), shots = [];
client.on('Page.screencastFrame', ({ data, metadata, sessionId }) => {
  const f = `frames/${String(shots.length).padStart(5, '0')}.jpg`;
  fs.writeFileSync(f, Buffer.from(data, 'base64')); shots.push([f, metadata.timestamp]);
  client.send('Page.screencastFrameAck', { sessionId }).catch(() => {});
});
await client.send('Page.startScreencast', { format: 'jpeg', quality: 92, maxWidth: 1080, maxHeight: 1350, everyNthFrame: 1 });
const t0 = Date.now(), ev = name => events.push([name, (Date.now() - t0) / 1000]);
ev('start');
await sleep(2600);
await page.evaluate(() => { records.forEach(r => r.node.remove()); records.length = 0; });
await page.evaluate(async () => {
  const list = await fetch('/api/memories').then(r => r.ok ? r.json() : []).catch(() => []);
  const real = list.filter(r => V(r.village)).map(r => ({ ...r, id: 'm' + r.id, name: r.name || 'Анонімно' }));
  const ex = real.length >= EXAMPLES_UNTIL ? [] : SAMPLE.map((r, i) => ({ ...r, id: 's' + i })).filter(r => !PICKED || PICKED.includes(r.id));
  load([...real, ...ex], true);
});
await page.addStyleTag({ content: `.head { transition: opacity .8s ease; } .vhide .head { opacity: 0; pointer-events: none; } .vhide .zoom-out { display: none; } .vhide .foot { display: none; }` });
await page.evaluate(() => {
  document.body.classList.add('vhide');
  const L = land(); base = [L.x0 - 24, L.y0 - 30, L.x1 - L.x0 + 120, L.y1 - L.y0 - 60]; setBox(base);
});
await page.evaluate(() => {  // a camera: glide the frame to a point at a given closeness (1 = the whole community)
  window.cam = (x, y, k, ms) => new Promise(done => {
    const from = map.getAttribute('viewBox').split(' ').map(Number), w = base[2] / k, h = base[3] / k, to = k === 1 ? base : [x - w / 2, y - h / 2, w, h];
    const t0 = performance.now(), id = ++zooming;
    const step = now => { if (id !== zooming) return done(); const p = Math.min(1, (now - t0) / ms), e = ease(p); setBox(from.map((a, i) => a + (to[i] - a) * e)); p < 1 ? requestAnimationFrame(step) : done(); };
    requestAnimationFrame(step);
  });
  window.camTo = (name, k, ms) => { const v = V(name); return cam(v.x, v.y, k, ms); };
});
const camTo = (name, k, ms) => page.evaluate((n, k, ms) => camTo(n, k, ms), name, k, ms);
const camHome = ms => page.evaluate(ms => cam(0, 0, 1, ms), ms);
const objAt = test => page.evaluate(t => { const r = records.find(new Function('r', 'return ' + t)); const b = r.node.getBoundingClientRect(); return [b.left + b.width / 2, b.top + b.height / 2]; }, test);

await vo(null, false); ev('reveal');
await sleep(1600);
// the opening flight: over the northern fields, down the river to the sea
await cap('Наша громада знову в кольорах: поля, море, села'); ev('cap1');
page.mouse.move(400, 500);
await camTo('Зеленівка', 1.8, 3200); ev('cam');
await camTo('Мар' + 'инівка', 1.9, 2600);
await camTo('Преслав', 2.0, 2600);
await cap(null);

// a light by Банівка: hover, open, leaf on
await camTo('Банівка', 2.3, 1800);
await cap('Кожен вогник — чийсь спогад'); ev('cap2');
const mem = await objAt("r.kind === 'memory' && r.village === 'Банівка'");
await glide(...mem, 1000); ev('hover'); await sleep(1400);
await click(...mem); ev('open'); await sleep(3200);
const next = await center("document.getElementById('next')");
await click(...next); ev('turn'); await sleep(2600);
await closeCard(); ev('close'); await cap(null);

// a dream up north
await camTo('Нельгівка', 2.3, 2600);
await cap('Повітряні змії — мрії про те, що зробимо вдома'); ev('cap3');
const dream = await objAt("r.kind === 'dream' && r.village === 'Нельгівка'");
await glide(...dream, 1000); await sleep(600);
await click(...dream); ev('open'); await sleep(3200);
await closeCard(); ev('close'); await cap(null);

await camHome(2200);

// the record of the day: the words come back for it
await page.evaluate(() => document.body.classList.remove('vhide')); await sleep(700);
await cap('Щодня — новий спогад'); ev('cap5');
for (let i = 0; i < 2; i++) {
  const other = await center("document.getElementById('daily-next')");
  await click(...other); ev('daily'); await sleep(1800);
}
await cap(null); await sleep(300);

// the form: write a memory (not sent)
await cap('Додайте свій — кожен вогник повертає нам дім'); ev('cap6');
const add = await center("document.getElementById('add')");
await click(...add); ev('form'); await sleep(1200);
await page.select('#f-village', 'Борисівка');
const ta = await center("document.getElementById('f-text')");
await click(...ta); await sleep(300);
ev('typing');
await page.keyboard.type('Пам’ятаю, як влітку ми всією вулицею ходили на море…', { delay: 45 }); ev('typed');
await sleep(1300);
await page.keyboard.press('Escape'); await cap(null); await sleep(900);

// the ending: the words come one by one, then the name, then the address
const quote = 'Поки ми не вдома, наша пам’ять тримає його живим.'.split(' ').map(w => `<span class="w q">${w}</span>`).join(' ');
await vo(`<div><div class="quote">${quote}</div><h2 class="w t"><span class="a">Спогади</span> <span class="and">та</span> <span class="b">мрії</span></h2><p class="url w u">prym.mydom.website/memories</p></div>`);
await sleep(1300); ev('quote');
await page.evaluate(() => document.querySelectorAll('#vo .q').forEach((w, i) => setTimeout(() => w.classList.add('in'), i * 260)));
await sleep(3400); ev('title');
await page.evaluate(() => document.querySelector('#vo .t').classList.add('in'));
await sleep(1800); ev('url');
await page.evaluate(() => document.querySelector('#vo .u').classList.add('in'));
await sleep(3800);
ev('end');
await client.send('Page.stopScreencast');
// a concat list: each frame lasts until the next one; times on the same clock as the events
const start = t0 / 1000;
const lines = shots.map(([f, ts], i) => `file '${f}'\nduration ${((shots[i + 1] ? shots[i + 1][1] : ts + .04) - ts).toFixed(4)}`);
const lead = Math.max(0, shots[0][1] - start);
fs.writeFileSync('frames.txt', `file '${shots[0][0]}'\nduration ${lead.toFixed(4)}\n` + lines.join('\n') + `\nfile '${shots.at(-1)[0]}'\n`);
fs.writeFileSync(evOut, JSON.stringify(events));
await browser.close();
