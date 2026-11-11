// holodomor.html?tune: place the page's blocks by hand (local only, not published).
// Every block is outlined with its name tag; click a tag (or the block: the smallest one under the cursor, Shift: the whole part) to select it.
// Drag it up/down: the gap above it (Alt while dragging: also sideways). The bar on its right edge: width; on its bottom edge: height.
// Pictures: dragging moves them between the parts with the page below staying put, the bottom bar sets their height,
// Alt+wheel sets where they fade at the bottom, Alt+Shift+wheel at the top. Esc: deselect. The panel lists every change.
(() => {
  const css = document.createElement('style');
  // body > … beats the page's «body > *:not(.wall) { position: relative }»
  css.textContent = `
    body.tune { user-select: none; -webkit-user-select: none; }
    body.tune * { cursor: default; }
    body.tune .scene img, body.tune .reveal, body.tune .card, body.tune .kids-head, body.tune .wait { opacity: 1 !important; transform: none !important; transition: none !important; }
    body > .tune-hover, body > .tune-box { position: absolute; z-index: 40; pointer-events: none; outline: 1px dashed rgba(240,207,134,.6); }
    .tune-box { outline: 2px solid #f0cf86; }
    .tune-box b { position: absolute; background: rgba(240,207,134,.75); pointer-events: auto; }
    .tune-box .r { top: 0; bottom: 0; right: -7px; width: 14px; cursor: ew-resize; }
    .tune-box .d { left: 0; right: 0; bottom: -7px; height: 14px; cursor: ns-resize; }
    .tune-box span { position: absolute; left: 0; top: -22px; font: 12px/1.3 ui-monospace, monospace; background: rgba(0,0,0,.85); color: #f0cf86; padding: 3px 6px; white-space: nowrap; }
    body > .tune-mark { position: absolute; z-index: 39; pointer-events: none; outline: 1px dashed rgba(240,207,134,.28); }
    .tune-mark.block { outline-color: rgba(255,255,255,.22); }
    .tune-mark i { position: absolute; left: 0; top: 0; pointer-events: auto; cursor: pointer; font: normal 10px/1.2 ui-monospace, monospace;
      background: rgba(40,32,18,.85); color: #f0cf86; padding: 1px 4px; white-space: nowrap; }
    .tune-mark.block i { left: auto; right: 0; background: rgba(60,60,60,.85); color: #fff; }
    .tune-mark i:hover, .tune-mark.on i { background: #f0cf86; color: #1d1406; }
    body > .tune-panel { position: fixed; z-index: 50; right: 12px; bottom: 12px; width: min(600px, calc(100vw - 24px)); max-height: 40vh; overflow: auto;
      background: rgba(14,12,8,.94); border: 1px solid #d8b265; color: #eee; font: 12px/1.45 ui-monospace, monospace; padding: 10px; }
    .tune-panel pre { margin: 0 0 8px; white-space: pre-wrap; }
    .tune-panel button { font: inherit; background: #d8b265; color: #1d1406; border: 0; padding: 5px 10px; margin-right: 6px; cursor: pointer; }`;
  document.head.appendChild(css);
  document.body.classList.add('tune');
  document.querySelectorAll('.scene, .reveal').forEach(el => el.classList.add('shown'));

  const BLOCKS = 'body > :is(header, section, figure, footer)';
  const TUNABLE = `${BLOCKS}, body > :is(header, section, footer) > .wrap > *, .chapter-head > *, .kids > *, .mapframe > *`;
  const r = n => +(+n).toFixed(3);
  const base = () => Math.min(600, Math.max(240, innerWidth * .42));  // the clamp() in .scene
  const name = el => {
    const block = el.closest(BLOCKS), b = block.id ? '#' + block.id : '.' + block.classList[0] +
      (block.matches('.scene') ? `(${block.querySelector('img').getAttribute('src').replace(/^holodomor-|\.webp$/g, '')})` : '');
    if (el === block) return b;
    const own = el.id ? '#' + el.id : el.classList[0] ? '.' + el.classList[0] : el.tagName.toLowerCase();
    const sibs = [...el.parentElement.children];
    return `${b} ${own}${sibs.filter(x => x.matches(own)).length > 1 ? `:nth-child(${sibs.indexOf(el) + 1})` : ''}`;
  };

  const state = new Map();  // element -> what was changed
  const get = el => {
    if (!state.has(el)) {
      const cs = getComputedStyle(el), v = n => cs.getPropertyValue('--' + n).trim();
      state.set(el, el.matches('.scene')
        ? { scene: true, orig: el.getAttribute('style'), k: +v('k') || 1, up: +v('up') || 0, down: +v('down') || 0,
            x: parseFloat(v('pos')) || 50, a: parseFloat(v('a')) || 25, b: parseFloat(v('b')) || 60 }
        : { mt0: parseFloat(cs.marginTop) || 0, dy: 0, dx: 0, w: null, h: null });
      const s = state.get(el);
      if (s.scene) s.first = sceneStyle(s);
    }
    return state.get(el);
  };
  const sceneStyle = s => `--k:${r(s.k)};--up:${r(s.up)};--down:${r(s.down)};--pos:${r(s.x)}% 50%;--a:${r(s.a)}%;--b:${r(s.b)}%`;
  const rules = s => [s.dy && `margin-top: ${Math.round(s.mt0 + s.dy)}px`, s.dx && `translate: ${Math.round(s.dx)}px 0`,
    s.w != null && `width: ${Math.round(s.w)}px; max-width: none`, s.h != null && `min-height: ${Math.round(s.h)}px`].filter(Boolean).join('; ');
  const changed = s => s.scene ? sceneStyle(s) !== s.first : !!rules(s);
  const apply = el => {
    const s = get(el);
    if (s.scene) el.setAttribute('style', sceneStyle(s));
    else {
      el.style.marginTop = s.dy ? s.mt0 + s.dy + 'px' : '';
      el.style.translate = s.dx ? s.dx + 'px 0' : '';
      if (s.w != null) Object.assign(el.style, { width: s.w + 'px', maxWidth: 'none' });
      if (s.h != null) el.style.minHeight = s.h + 'px';
    }
    report();
  };

  const panel = Object.assign(document.createElement('div'), { className: 'tune-panel' });
  panel.innerHTML = '<pre></pre><button type="button" data-copy>Копіювати</button><button type="button" data-reset>Скинути вибраний</button>';
  document.body.appendChild(panel);
  const lines = () => [...state].filter(([, s]) => changed(s))
    .map(([el, s]) => s.scene ? `${name(el)}: style="${sceneStyle(s)}"` : `${name(el)} { ${rules(s)} }`);
  const report = () => { panel.querySelector('pre').textContent = lines().join('\n') || 'Клацніть блок, щоб вибрати (Shift+клік: увесь розділ), і тягніть.'; place(); };
  window.tuneValues = lines;

  const hover = Object.assign(document.createElement('div'), { className: 'tune-hover' });
  const box = Object.assign(document.createElement('div'), { className: 'tune-box' });
  box.innerHTML = '<span></span><b class="r"></b><b class="d"></b>';
  document.body.append(hover, box);
  let sel = null, drag = null;
  // a permanent outline and name tag on every block, so it is clear what can be moved and what a click takes
  const marks = [...document.querySelectorAll(TUNABLE)].map(el => {
    const m = Object.assign(document.createElement('div'), { className: 'tune-mark' + (el.matches(BLOCKS) ? ' block' : '') });
    const tag = document.createElement('i');
    tag.textContent = el.matches(BLOCKS) ? name(el) : name(el).split(' ').slice(1).join(' ');
    tag.tune = el;
    m.append(tag);
    document.body.append(m);
    return [el, m];
  });
  const frame = (div, el) => {
    if (!el) { div.hidden = true; return; }
    const b = el.getBoundingClientRect();
    if (!b.width || !b.height) { div.hidden = true; return; }  // hidden blocks (search results before a search)
    Object.assign(div.style, { left: b.left + scrollX + 'px', top: b.top + scrollY + 'px', width: b.width + 'px', height: b.height + 'px' });
    div.hidden = false;
  };
  function place() {
    marks.forEach(([el, m]) => { frame(m, el); m.classList.toggle('on', el === sel); });
    frame(box, sel);
    if (!sel) return;
    const s = get(sel);
    box.querySelector('.r').hidden = !!s.scene;
    box.querySelector('span').textContent = name(sel) + (s.scene ? `  висота ${r(s.k)}  верх ${r(s.up)}  низ ${r(s.down)}  згасання ${Math.round(s.a)}–${Math.round(s.b)}%`
      : `  ${sel.offsetWidth}×${sel.offsetHeight}`);
  }
  addEventListener('scroll', place, { passive: true });
  addEventListener('resize', place);

  const pick = (x, y, whole) => {
    const area = el => el.offsetWidth * el.offsetHeight;
    const all = document.elementsFromPoint(x, y).filter(el => el.matches(TUNABLE));
    return all.sort((a, b) => whole ? area(b) - area(a) : area(a) - area(b))[0] || null;
  };
  document.addEventListener('mousemove', e => { if (!drag) frame(hover, e.target.closest('.tune-panel') ? null : e.target.tune || pick(e.clientX, e.clientY, e.shiftKey)); });
  ['click', 'dblclick', 'submit'].forEach(t => document.addEventListener(t, e => { if (!e.target.closest('.tune-panel')) { e.preventDefault(); e.stopPropagation(); } }, true));

  document.addEventListener('pointerdown', e => {
    if (e.target.closest('.tune-panel')) return;
    e.preventDefault(); e.stopPropagation();
    const handle = e.target.closest('.tune-box b');
    if (!handle) { const el = e.target.tune || pick(e.clientX, e.clientY, e.shiftKey); if (el !== sel) { sel = el; place(); } }
    if (!sel) return;
    const s = get(sel);
    drag = { mode: handle ? (handle.classList.contains('r') ? 'w' : 'h') : 'move', x0: e.clientX, y0: e.clientY, s0: { ...s },
      w0: sel.offsetWidth, h0: sel.offsetHeight, H0: (s.k || 1) * base() };
  }, true);
  document.addEventListener('pointermove', e => {
    if (!drag || !sel) return;
    const s = get(sel), dx = e.clientX - drag.x0, dy = e.clientY - drag.y0, { s0, H0 } = drag;
    if (s.scene) {
      if (drag.mode === 'h') { const H = Math.max(120, H0 + dy); Object.assign(s, { k: H / base(), up: s0.up * H0 / H, down: s0.down * H0 / H }); }
      else Object.assign(s, { up: s0.up - dy / H0, down: s0.down + dy / H0, x: Math.min(100, Math.max(0, s0.x - dx / 8)) });
    } else if (drag.mode === 'w') s.w = Math.max(40, drag.w0 + dx * 2);  // centred blocks grow on both sides
    else if (drag.mode === 'h') s.h = Math.max(10, drag.h0 + dy);
    else Object.assign(s, { dy: s0.dy + dy, dx: e.altKey ? s0.dx + dx : s0.dx });
    apply(sel);
  });
  addEventListener('pointerup', () => { drag = null; });
  addEventListener('keydown', e => { if (e.key === 'Escape') { sel = null; place(); } });
  addEventListener('wheel', e => {
    if (!e.altKey || !sel || !get(sel).scene) return;
    e.preventDefault();
    const s = get(sel), d = e.deltaY > 0 ? 2 : -2;
    if (e.shiftKey) s.a = Math.min(s.b - 5, Math.max(0, s.a + d)); else s.b = Math.min(100, Math.max(s.a + 5, s.b + d));
    apply(sel);
  }, { passive: false });

  panel.querySelector('[data-copy]').onclick = () => navigator.clipboard.writeText(lines().join('\n'));
  panel.querySelector('[data-reset]').onclick = () => {
    if (!sel) return;
    const s = get(sel);
    if (s.scene) sel.setAttribute('style', s.orig || ''); else ['marginTop', 'translate', 'width', 'maxWidth', 'minHeight'].forEach(p => sel.style[p] = '');
    state.delete(sel);
    report();
  };
  report();
})();
