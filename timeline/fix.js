// Readers' corrections: select a fragment of an article, press "✎ Запропонувати правку", write how it should read.
// The note goes to /api/fix (worker.js -> D1 prym-feedback); the archive text itself changes only after review.
(() => {
  const style = document.createElement('style');
  style.textContent = `
    .fix-btn { position: fixed; z-index: 2147483000; padding: 8px 12px; border: 0; border-radius: 10px; background: #efb544; color: #174f3e;
      font: 600 14px system-ui, sans-serif; box-shadow: 0 6px 18px rgba(0,0,0,.18); cursor: pointer; }
    .fix-dlg { width: min(520px, calc(100vw - 32px)); border: 0; border-radius: 18px; padding: 22px; color: #0f222b; background: #fffaf2;
      font: 15px/1.5 system-ui, sans-serif; box-shadow: 0 20px 60px rgba(0,0,0,.3); }
    .fix-dlg::backdrop { background: rgba(8, 26, 34, .45); }
    .fix-dlg b { font-size: 18px; }
    .fix-dlg p { margin: 6px 0 12px; color: #5d6a6c; font-size: 14px; }
    .fix-dlg label { display: block; margin: 10px 0 0; font-weight: 600; font-size: 14px; }
    .fix-dlg label span { color: #b8322a; }
    .fix-dlg textarea, .fix-dlg input { display: block; width: 100%; box-sizing: border-box; margin-top: 4px; padding: 9px 11px;
      border: 1px solid #e4d7bf; border-radius: 10px; font: 15px/1.45 system-ui, sans-serif; background: #fff; color: inherit; }
    .fix-dlg .fix-hp { position: absolute; left: -9999px; }
    .fix-dlg .fix-status { min-height: 1.4em; margin: 10px 0 0; color: #174f3e; }
    .fix-dlg .fix-actions { display: flex; justify-content: flex-end; gap: 8px; margin-top: 8px; }
    .fix-dlg button { padding: 9px 16px; border-radius: 10px; border: 1px solid #e4d7bf; background: #fff; font: 600 14px system-ui, sans-serif; cursor: pointer; color: inherit; }
    .fix-dlg button.go { background: #174f3e; border-color: #174f3e; color: #fff; }
    .fix-line { position: relative; margin: 22px 0 0; padding: 14px 16px 14px 46px; border-radius: 14px; border-left: 4px solid #efb544;
      background: rgba(239, 181, 68, .14); color: inherit; font-size: 14px; line-height: 1.55; }
    .fix-line::before { content: '✎'; position: absolute; left: 16px; top: 13px; font-size: 18px; color: #c8901f; }
    .fix-link { border: 0; padding: 1px 8px; margin: 0 1px; border-radius: 7px; background: #efb544; color: #174f3e;
      font: 600 13px/1.6 system-ui, sans-serif; cursor: pointer; }
    .fix-link:hover { background: #f2bf57; }`;
  document.head.append(style);

  const btn = Object.assign(document.createElement('button'), { type: 'button', className: 'fix-btn', textContent: '✎ Запропонувати правку', hidden: true });
  const dlg = document.createElement('dialog');
  dlg.className = 'fix-dlg';
  dlg.innerHTML = `<form method="dialog">
    <b>Запропонувати правку</b>
    <p>Тексти перенесено з архівів так, як їх було опубліковано. Напишіть, як має бути, — ми перевіримо й виправимо.</p>
    <label>Фрагмент<textarea name="fragment" rows="3" maxlength="2000"></textarea></label>
    <label>Як має бути <span>*</span><textarea name="fix" rows="3" maxlength="4000" required></textarea></label>
    <label>Коментар (необов'язково)<input name="comment" maxlength="2000"></label>
    <input class="fix-hp" name="website" tabindex="-1" autocomplete="off" aria-hidden="true">
    <p class="fix-status" role="status"></p>
    <div class="fix-actions"><button type="button" data-close>Скасувати</button><button class="go" type="submit">Надіслати</button></div>
  </form>`;
  const form = dlg.querySelector('form'), status = dlg.querySelector('.fix-status');

  const articleId = () => (location.pathname.match(/\/p\/([0-9a-f]{10})/) || location.hash.match(/^#([0-9a-f]{10})$/) || [])[1] || '';
  const inArticle = node => (node?.nodeType === 1 ? node : node?.parentElement)?.closest('.article');
  // a modal reader keeps everything outside it inert: the button and the form live in the top-most open dialog
  const host = node => (node?.nodeType === 1 ? node : node?.parentElement)?.closest('dialog[open]') || document.body;

  function openFix(fragment = '') {
    const sel = getSelection();
    (host(sel.anchorNode || document.body) === document.body ? document.body : host(sel.anchorNode)).append(dlg);
    form.reset();
    form.fragment.value = fragment;
    status.textContent = '';
    btn.hidden = true;
    dlg.showModal();
    (fragment ? form.fix : form.fragment).focus();
  }
  window.openFix = openFix;

  function place() {
    const sel = getSelection(), text = sel.toString().trim();
    if (!text || text.length > 2000 || !sel.rangeCount || !inArticle(sel.anchorNode) || dlg.open) { btn.hidden = true; return; }
    host(sel.anchorNode).append(btn);
    const r = sel.getRangeAt(0).getBoundingClientRect();
    btn.style.top = `${Math.min(r.bottom + 8, innerHeight - 52)}px`;
    btn.style.left = `${Math.max(8, Math.min(r.left, innerWidth - 230))}px`;
    btn.hidden = false;
  }
  document.addEventListener('mouseup', () => setTimeout(place));
  document.addEventListener('touchend', () => setTimeout(place, 300));
  document.addEventListener('selectionchange', () => { if (!getSelection().toString().trim()) btn.hidden = true; });
  btn.addEventListener('mousedown', e => e.preventDefault());  // keep the selection
  btn.addEventListener('click', () => openFix(getSelection().toString().trim()));
  dlg.querySelector('[data-close]').addEventListener('click', () => dlg.close());

  form.addEventListener('submit', async e => {
    e.preventDefault();
    const go = form.querySelector('.go');
    go.disabled = true;
    status.textContent = 'Надсилаємо…';
    try {
      const r = await fetch('/api/fix', { method: 'POST', headers: { 'content-type': 'application/json' }, body: JSON.stringify({
        article: articleId(), page: location.href, fragment: form.fragment.value, fix: form.fix.value,
        comment: form.comment.value, website: form.website.value }) });
      const d = await r.json().catch(() => ({}));
      if (!r.ok) throw new Error(d.error || r.status);
      status.textContent = 'Дякуємо! Правку надіслано, ми її перевіримо.';
      setTimeout(() => dlg.close(), 1600);
    } catch (err) {
      status.textContent = String(err.message) === 'limit' ? 'Сьогодні з вашої адреси вже надіслано багато правок. Спробуйте завтра.'
        : 'Не вдалося надіслати. Спробуйте трохи пізніше.';
    } finally {
      go.disabled = false;
    }
  });
})();
