

  // Make MEDIA_URL available to JS (works even if the context processor is missing)
  const MEDIA_URL = "{{ MEDIA_URL|default:'/media/' }}";

  /* ---------------------------
     Accept / Decline handlers
     --------------------------- */
  document.getElementById('acceptSubmitBtn')?.addEventListener('click', function () {
    const msg = (document.getElementById('acceptMessage').value || '').trim();
    document.getElementById('acceptMessageInput').value = msg;
    document.getElementById('acceptForm').submit();
  });

  document.getElementById('declineSubmitBtn')?.addEventListener('click', function () {
    const reasonEl = document.getElementById('declineMessage');
    const reason = (reasonEl.value || '').trim();
    if (!reason) {
      reasonEl.classList.add('is-invalid');
      reasonEl.focus();
      return;
    }
    reasonEl.classList.remove('is-invalid');
    document.getElementById('declineMessageInput').value = reason;
    document.getElementById('declineForm').submit();
  });

  document.getElementById('declineModal')?.addEventListener('hidden.bs.modal', function () {
    const reasonEl = document.getElementById('declineMessage');
    if (reasonEl) {
      reasonEl.value = '';
      reasonEl.classList.remove('is-invalid');
    }
  });

  document.getElementById('acceptModal')?.addEventListener('hidden.bs.modal', function () {
    const msgEl = document.getElementById('acceptMessage');
    if (msgEl) msgEl.value = '';
  });

  // Buttons that should navigate only after the modal closes
  document.querySelectorAll('.navigate-after-close').forEach(function (link) {
    link.addEventListener('click', function (e) {
      e.preventDefault();
      const url = this.getAttribute('href');
      const modalEl = this.closest('.modal');

      if (modalEl) {
        const modal = bootstrap.Modal.getInstance(modalEl) || new bootstrap.Modal(modalEl);
        const go = function () {
          modalEl.removeEventListener('hidden.bs.modal', go);
          window.open(url, '_blank', 'noopener');
          // If you prefer same tab: window.location.href = url;
        };
        modalEl.addEventListener('hidden.bs.modal', go, { once: true });
        modal.hide();
      } else {
        window.open(url, '_blank', 'noopener');
      }
    });
  });

  // Clean up if you come back via Back/Forward cache
  window.addEventListener('pageshow', function () {
    document.querySelectorAll('.modal.show').forEach(function (el) {
      (bootstrap.Modal.getInstance(el) || new bootstrap.Modal(el)).hide();
    });
    document.body.classList.remove('modal-open');
    document.querySelectorAll('.modal-backdrop').forEach(function (bd) { bd.remove(); });
  });

   /* ---------------------------
     File preview (image / PDF)
     --------------------------- */
  function ensureAbsoluteMediaUrl(url) {
    if (!url) return '';
    if (/^https?:\/\//i.test(url)) return url;
    if (url.startsWith('//')) return window.location.protocol + url;
    if (url.startsWith('/')) return window.location.origin + url;
    if (url.startsWith('media/')) return window.location.origin + '/' + url;
    return url;
  }

  (function () {
    const modalEl   = document.getElementById('filePreviewModal');
    const container = document.getElementById('previewContainer');
    if (!modalEl || !container) return;

    function isImage(url) {
      return /\.(png|jpe?g|gif|webp)$/i.test(url.split('?')[0]);
    }
    function isPdf(url) {
      return /\.pdf$/i.test(url.split('?')[0]);
    }

    // Use relatedTarget from the button that opened the modal
    modalEl.addEventListener('show.bs.modal', function (ev) {
      const btn  = ev.relatedTarget;
      const raw  = btn?.getAttribute('data-file-url') || '';
      const name = btn?.getAttribute('data-file-name') || 'file';
      const url  = ensureAbsoluteMediaUrl(raw);

      container.innerHTML = '';

      if (!url) {
        container.innerHTML = '<div class="p-4 text-danger">No file URL found.</div>';
        return;
      }

      if (isImage(url)) {
        const img = new Image();
        img.src = url;
        img.alt = name;
        img.className = 'img-fluid';
        img.style.maxHeight = '82vh';
        container.appendChild(img);
      } else if (isPdf(url)) {
        const iframe = document.createElement('iframe');
        iframe.src = url + (url.includes('#') ? '' : '#zoom=page-width');
        iframe.style.width = '100%';
        iframe.style.height = '82vh';
        iframe.setAttribute('title', name);
        iframe.setAttribute('loading', 'lazy');
        container.appendChild(iframe);
      } else {
        const div = document.createElement('div');
        div.className = 'p-4 text-center';
        const filename = name.split('/').pop();
        div.innerHTML = `
          <p class="mb-3">Preview not available for this file type.</p>
          <a class="btn btn-dark" href="${url}" download>
            <i class="bi bi-download"></i> Download ${filename}
          </a>`;
        container.appendChild(div);
      }
    });

    modalEl.addEventListener('hidden.bs.modal', function () {
      container.innerHTML = '';
    });
  })();

///////////////////////////////////////////////////////////////////////////////////////////
  window.addEventListener('pageshow', function (e) {
    if (e.persisted) location.reload();
  });
///////////////////////////////////////////////////////////////////////////////////////////

/* One-click-only for modal Accept / Decline in admin_view_goodmoral.html (additive, safe) */
(() => {
  // If you have specific IDs, set them here (optional):
  const IDS = {
    acceptModal:  'acceptModal',     // modal id for Accept
    declineModal: 'declineModal',    // modal id for Decline
    acceptForm:   'acceptForm',      // form id inside Accept modal (optional)
    declineForm:  'declineForm',     // form id inside Decline modal (optional)
    acceptBtn:    'acceptSubmitBtn', // submit button id in Accept modal (optional)
    declineBtn:   'declineSubmitBtn' // submit button id in Decline modal (optional)
  };

  let inFlight = false;
  let safetyTimer = null;

  function findForm(modalEl, explicitId) {
    if (explicitId) {
      const f = document.getElementById(explicitId);
      if (f) return f;
    }
    return modalEl ? modalEl.querySelector('form') : null;
  }

  function findSubmitBtn(modalEl, explicitId) {
    if (explicitId) {
      const b = document.getElementById(explicitId);
      if (b) return b;
    }
    // Common fallbacks: a .btn in footer with type=submit or obvious classes
    return modalEl
      ? (modalEl.querySelector('.modal-footer button[type="submit"]')
        || modalEl.querySelector('.modal-footer .btn-success')
        || modalEl.querySelector('.modal-footer .btn-danger'))
      : null;
  }

  function lockFooterButtons(clickedBtn) {
    const footer = clickedBtn?.closest('.modal-footer');
    if (!footer) return;
    footer.querySelectorAll('button').forEach(b => {
      b.classList.add('disabled');
      b.setAttribute('aria-disabled', 'true');
      b.style.pointerEvents = 'none';
      b.style.opacity = '0.7';
      b.style.cursor = 'not-allowed';
    });
    const label = clickedBtn.textContent.trim() || 'Working';
    clickedBtn.innerHTML =
      '<span class="spinner-border spinner-border-sm me-1" role="status" aria-hidden="true"></span>' + label;
  }

  function armSafetyReset() {
    clearTimeout(safetyTimer);
    safetyTimer = setTimeout(() => {
      inFlight = false;
      document.querySelectorAll('.modal-footer .disabled').forEach(b => {
        b.classList.remove('disabled');
        b.removeAttribute('aria-disabled');
        b.style.pointerEvents = '';
        b.style.opacity = '';
        b.style.cursor = '';
      });
    }, 15000); // 15s fallback if we stayed on the same page
  }

  function wireModal(modalId, formId, btnId) {
    const modalEl = document.getElementById(modalId);
    if (!modalEl) return;

    const form = findForm(modalEl, formId);
    const submitBtn = findSubmitBtn(modalEl, btnId);

    // Guard rapid clicks on the submit button
    submitBtn?.addEventListener('click', (e) => {
      if (inFlight) { e.preventDefault(); e.stopPropagation(); return false; }
      // First click: lock UI and allow the submit to proceed
      inFlight = true;
      lockFooterButtons(submitBtn);
      armSafetyReset();
    }, true);

    // Guard at the form level as well (covers Enter key)
    form?.addEventListener('submit', (e) => {
      if (inFlight) { e.preventDefault(); e.stopPropagation(); return false; }
      inFlight = true;
      if (submitBtn) lockFooterButtons(submitBtn);
      armSafetyReset();
      // DO NOT disable inputs → CSRF & fields remain posted
      // Let the native submit proceed
    }, true);

    // When modal is fully hidden, clear local UI state (just cosmetic)
    modalEl.addEventListener('hidden.bs.modal', () => {
      // If you programmatically reopen without navigating, make sure buttons look normal again
      document.querySelectorAll(`#${modalId} .modal-footer .disabled`).forEach(b => {
        b.classList.remove('disabled');
        b.removeAttribute('aria-disabled');
        b.style.pointerEvents = '';
        b.style.opacity = '';
        b.style.cursor = '';
      });
    });
  }

  // Wire both modals (update IDs above if yours differ)
  wireModal(IDS.acceptModal,  IDS.acceptForm,  IDS.acceptBtn);
  wireModal(IDS.declineModal, IDS.declineForm, IDS.declineBtn);

  // Reset the in-flight flag when we navigate or return via bfcache
  window.addEventListener('pageshow', () => {
    inFlight = false;
    clearTimeout(safetyTimer);
  });
})();
////////////////////////////////////////////////////////////////////////////


(function () {
  const REQUEST_ID = "{{ r.pk }}";
  const KEY = `gm:formFirst:${REQUEST_ID}`;

  const certBtn = document.getElementById('btnGenCert');
  const formGenerateLink = document.querySelector('[data-gm-role="gen-form"]');

  // Only applies when Approved (btnGenCert exists)
  if (!certBtn) return;

  function setCertEnabled(enabled) {
    if (enabled) {
      certBtn.disabled = false;
      certBtn.style.opacity = '';
      certBtn.style.cursor = '';
      certBtn.setAttribute('data-bs-toggle', 'modal');
      certBtn.setAttribute('data-bs-target', '#generateModal');
      certBtn.title = '';
    } else {
      certBtn.disabled = true;
      certBtn.style.opacity = '.65';
      certBtn.style.cursor = 'not-allowed';
      certBtn.removeAttribute('data-bs-toggle');
      certBtn.removeAttribute('data-bs-target');
      certBtn.title = 'Please generate the Request Form first.';
    }
  }

  // Init from localStorage
  const alreadyDone = localStorage.getItem(KEY) === '1';
  setCertEnabled(alreadyDone);

  // When the Request Form "Generate" is clicked, mark done and enable Certificate
  formGenerateLink?.addEventListener('click', () => {
    localStorage.setItem(KEY, '1');
    setCertEnabled(true);
  });

  // Optional: small toast if user clicks disabled cert button
  certBtn.addEventListener('click', (e) => {
    if (certBtn.disabled) {
      e.preventDefault();
      const tip = document.createElement('div');
      tip.className = 'position-fixed bottom-0 start-50 translate-middle-x bg-dark text-white px-3 py-2 rounded shadow';
      tip.style.zIndex = 1080;
      tip.textContent = 'Generate the Request Form first.';
      document.body.appendChild(tip);
      setTimeout(() => tip.remove(), 1400);
    }
  });
})();
