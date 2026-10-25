document.documentElement.classList.add('js');
const toggle=document.querySelector('.menu-toggle');
const nav=document.querySelector('.nav');
toggle?.addEventListener('click',()=>{const open=toggle.getAttribute('aria-expanded')!=='true';toggle.setAttribute('aria-expanded',String(open));nav.classList.toggle('is-open',open);toggle.textContent=open?'Close':'Menu';});
document.addEventListener('keydown',event=>{if(event.key==='Escape'&&toggle?.getAttribute('aria-expanded')==='true'){toggle.click();toggle.focus();}});

// Watch completed builds only on the local preview. Hosted websites stay static.
(() => {
  if (location.protocol !== 'http:' || !['127.0.0.1', 'localhost', '[::1]'].includes(location.hostname)) return;
  const revision = document.querySelector('meta[name="tapas-preview-revision"]')?.content;
  if (!revision) return;
  let checking = false, navigating = false;
  async function checkPreview() {
    if (checking || navigating || document.visibilityState === 'hidden') return;
    checking = true;
    try {
      const response = await fetch('/assets/preview-version.json?t=' + Date.now(), {cache:'no-store'});
      if (!response.ok) return;
      const latest = await response.json();
      if (latest.format === 'tapas-local-preview-v1' && /^[a-f0-9]{24}$/.test(latest.revision) && latest.revision !== revision) {
        navigating = true;
        const next = new URL(location.href);
        next.searchParams.set('_preview', latest.revision);
        // Keep the current page and project anchor, and bypass old browser caches.
        location.replace(next.href);
      }
    } catch (_) {
      // A stopped local server must not interrupt reading the current page.
    } finally {
      checking = false;
    }
  }
  setInterval(checkPreview, 1500);
  window.addEventListener('focus', checkPreview);
  document.addEventListener('visibilitychange', checkPreview);
  checkPreview();
})();

// Keep animated covers still when the reader requests reduced motion.
if (typeof window.matchMedia === 'function') {
  const reducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)');
  const updateCoverMotion = () => document.querySelectorAll('video[data-cover-loop]').forEach(video => {
    if (reducedMotion.matches) video.pause();
    else video.play().catch(() => {});
  });
  reducedMotion.addEventListener('change', updateCoverMotion);
  updateCoverMotion();
}

