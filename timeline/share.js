// Sharing (our own buttons instead of the system share sheet) and a back-to-top button, on the chronicle and the article pages.
(() => {
  const style = document.createElement('style');
  style.textContent = `
    .share-row { display: flex; flex-wrap: wrap; align-items: center; gap: 8px; margin: 24px 0 0; }
    .share-row .share-label { font: 600 14px system-ui, sans-serif; margin-right: 4px; }
    .share-row a, .share-row button { display: inline-flex; align-items: center; gap: 6px; padding: 8px 13px; border-radius: 10px; border: 0;
      font: 600 13px system-ui, sans-serif; color: #fff; text-decoration: none; cursor: pointer; }
    .share-row .fb { background: #1877f2; } .share-row .tg { background: #229ed9; } .share-row .vb { background: #7360f2; }
    .share-row .wa { background: #25d366; } .share-row .cp { background: #174f3e; }
    .portal-share { width: min(460px, calc(100vw - 32px)); border: 0; border-radius: 18px; padding: 22px; background: #fffaf2; color: #0f222b;
      font: 15px/1.5 system-ui, sans-serif; box-shadow: 0 20px 60px rgba(0,0,0,.3);
      height: fit-content; max-height: calc(100vh - 32px); margin: auto; }
    .portal-share::backdrop { background: rgba(8, 26, 34, .45); }
    .portal-share .share-row { margin-top: 14px; } .portal-share .share-label { display: none; }
    .portal-share .close { position: absolute; top: 12px; right: 14px; border: 0; background: none; font-size: 20px; cursor: pointer; color: inherit; }
    .to-top { position: fixed; right: 20px; bottom: 20px; z-index: 2147482000; width: 46px; height: 46px; border-radius: 50%; border: 0;
      background: #174f3e; color: #fff; font-size: 22px; line-height: 1; cursor: pointer; box-shadow: 0 6px 18px rgba(0,0,0,.22);
      opacity: 0; transform: translateY(12px); pointer-events: none; transition: opacity .2s, transform .2s; }
    .to-top.on { opacity: 1; transform: none; pointer-events: auto; }
    .to-top:hover { background: #1f6a52; }`;
  document.head.append(style);

  const enc = encodeURIComponent;
  function fillShare(el, url, title) {
    const t = title ? `${title} — ${url}` : url;
    el.innerHTML = `<span class="share-label">Поширити:</span>
      <a class="fb" target="_blank" rel="noopener" href="https://www.facebook.com/sharer/sharer.php?u=${enc(url)}">Facebook</a>
      <a class="tg" target="_blank" rel="noopener" href="https://t.me/share/url?url=${enc(url)}&text=${enc(title || '')}">Telegram</a>
      <a class="vb" href="viber://forward?text=${enc(t)}">Viber</a>
      <a class="wa" target="_blank" rel="noopener" href="https://wa.me/?text=${enc(t)}">WhatsApp</a>
      <button type="button" class="cp">Копіювати посилання</button>`;
    const cp = el.querySelector('.cp');
    cp.onclick = async () => {
      try { await navigator.clipboard.writeText(url); } catch { prompt('Скопіюйте посилання:', url); return; }
      cp.textContent = 'Скопійовано ✓';
      setTimeout(() => { cp.textContent = 'Копіювати посилання'; }, 2000);
    };
  }
  window.fillShare = fillShare;
  document.querySelectorAll('.share-row[data-share]').forEach(el => fillShare(el, location.href.split('#')[0], document.querySelector('h1')?.textContent.trim() || document.title));

  // the whole portal: a small window with the same buttons
  const dlg = document.createElement('dialog');
  dlg.className = 'portal-share';
  dlg.innerHTML = '<button class="close" type="button" aria-label="Закрити">✕</button><b>Поширити хроніку громади</b><div class="share-row"></div>';
  dlg.querySelector('.close').onclick = () => dlg.close();
  dlg.addEventListener('click', e => { if (e.target === dlg) dlg.close(); });
  window.openShare = (url = location.origin + '/', title = 'Приморськ. Хроніка громади') => {
    const open = [...document.querySelectorAll('dialog[open]')].filter(x => x !== dlg).pop();  // above an open reader, never inside itself
    (open || document.body).append(dlg);
    fillShare(dlg.querySelector('.share-row'), url, title);
    dlg.showModal();
  };

  // which articles people read: the id goes to /api/view once per article per session; no cookies, nothing about the reader
  window.countView = n => {
    if (!/^[0-9a-f]{10}$/.test(n) || /^(localhost|127\.0\.0\.1|192\.168\.)/.test(location.hostname)) return;
    try { if (sessionStorage.getItem('v' + n)) return; sessionStorage.setItem('v' + n, 1); } catch {}
    navigator.sendBeacon?.('/api/view', n);
  };
  const own = location.pathname.match(/\/p\/([0-9a-f]{10})/);
  if (own) countView(own[1]);

  // back to top: the page itself, or the open reader (it scrolls inside .r-scroll)
  const top = Object.assign(document.createElement('button'), { type: 'button', className: 'to-top', textContent: '↑' });
  top.setAttribute('aria-label', 'Вгору');
  const scroller = () => document.querySelector('dialog[open] .r-scroll');
  const sync = () => {
    const s = scroller(), y = s ? s.scrollTop : scrollY;
    (document.querySelector('dialog[open]:not(.portal-share):not(.fix-dlg)') || document.body).append(top);
    top.classList.toggle('on', y > 700);
  };
  top.onclick = () => (scroller() || window).scrollTo({ top: 0, behavior: 'smooth' });
  addEventListener('scroll', sync, { passive: true });
  document.addEventListener('scroll', e => { if (e.target.classList?.contains('r-scroll')) sync(); }, { capture: true, passive: true });
  new MutationObserver(sync).observe(document.body, { subtree: true, attributes: true, attributeFilter: ['open'] });
  sync();
})();
