// Cloudflare Turnstile: «are you a person» before a form goes to /api/fix or /api/memory (worker.js checks the token).
// Nothing loads until a form is sent; the check is invisible unless Cloudflare decides to ask for a click.
(() => {
  const SITEKEY = '0x4AAAAAAF8Eymq202NM7XEj';  // public by design; the secret is the worker's TURNSTILE_SECRET
  let api;
  const ids = new Map();
  // human('fix', element) -> a one-time token; rejects if the check can't run (no network, a blocker, a timeout)
  window.human = async (action, holder) => {
    api ??= new Promise((ok, fail) => {
      const s = Object.assign(document.createElement('script'), { src: 'https://challenges.cloudflare.com/turnstile/v0/api.js?render=explicit' });
      s.onload = ok;
      s.onerror = () => { api = null; fail(new Error('human')); };
      document.head.append(s);
    });
    await api;
    return new Promise((ok, fail) => {
      if (ids.has(holder)) turnstile.remove(ids.get(holder));  // a token works once: every sending gets a fresh one
      const no = () => { fail(new Error('human')); return true; };
      ids.set(holder, turnstile.render(holder, { sitekey: SITEKEY, action, appearance: 'interaction-only', language: 'uk',
        callback: ok, 'error-callback': no, 'timeout-callback': no }));
    });
  };
})();
