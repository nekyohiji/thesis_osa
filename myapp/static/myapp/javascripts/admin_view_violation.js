

  document.addEventListener('DOMContentLoaded', function () {
    const modalEl = document.getElementById('evidenceModal');
    const imgEl   = document.getElementById('evidenceModalImg');
    const titleEl = document.getElementById('evidenceModalLabel');
    const openEl  = document.getElementById('evidenceOpenNew');
    const dlEl    = document.getElementById('evidenceDownload');

    modalEl.addEventListener('show.bs.modal', function (event) {
      const trigger = event.relatedTarget; 
      const url     = trigger.getAttribute('data-evidence-url');
      const label   = trigger.getAttribute('data-evidence-label') || 'Evidence';
      imgEl.src = '';
      imgEl.alt = label;
      titleEl.textContent = label;
      openEl.href = url;
      dlEl.href   = url;
      setTimeout(() => { imgEl.src = url; }, 10);
    });
  });


//////////////////////////////////////////////////////////////////////////////
  window.addEventListener('pageshow', function (e) {
    if (e.persisted) location.reload();
  });

///////////////////////////////////////////////////////////////////////
/* One-click-only for any anchor/button marked data-safe-nav */
(() => {
  if (typeof window.__navClicking === 'undefined') window.__navClicking = false;

  function lockOne(a) {
    a.classList.add('disabled');
    a.setAttribute('aria-disabled', 'true');
    a.style.pointerEvents = 'none';
    a.style.opacity = '0.7';
    const label = a.textContent.trim() || 'Working';
    a.innerHTML =
      '<span class="spinner-border spinner-border-sm me-1" role="status" aria-hidden="true"></span>' +
      label;
  }

  document.addEventListener('click', (e) => {
    const a = e.target.closest('a[data-safe-nav],button[data-safe-nav]');
    if (!a) return;

    // already in-flight? ignore further clicks
    if (window.__navClicking || a.dataset.locked === '1') {
      e.preventDefault(); e.stopPropagation(); return false;
    }

    a.dataset.locked = '1';
    window.__navClicking = true;
    lockOne(a);

    // Safety reset in case navigation doesn’t occur
    setTimeout(() => { window.__navClicking = false; }, 12000);
  });

  // Clear the lock when the page finishes navigating / bfcache restore
  window.addEventListener('pageshow', () => { window.__navClicking = false; });
})();
