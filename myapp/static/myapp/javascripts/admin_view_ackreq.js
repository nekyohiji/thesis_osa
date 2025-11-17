

/* Generate PDF handler (unchanged; safe if elements missing) */
(function () {
  const modalEl = document.getElementById('generateModal');
  const btn     = document.getElementById('generateReceiptBtn');
  if (!modalEl || !btn) return;

  const modal = bootstrap.Modal.getOrCreateInstance(modalEl);

  // URL is rendered by Django into data-url in the HTML
  const url = btn.dataset.url;

  btn.addEventListener('click', () => {
    btn.blur();
    modal.hide();
  });

  modalEl.addEventListener('hidden.bs.modal', () => {
    if (url) {
      window.open(url, '_blank', 'noopener');
    }
  });
})();

/* Accept / Decline via AJAX with instant feedback */
(function () {
  function getCsrf(form) {
    const inp = form.querySelector('input[name="csrfmiddlewaretoken"]');
    return inp ? inp.value : '';
  }
  function disableModalControls(form, on) {
    const modal = form.closest('.modal');
    if (!modal) return;
    modal.querySelectorAll('button, a, textarea, select, input:not([type="hidden"])')
      .forEach(el => {
        el.disabled = on;
        el.setAttribute('aria-disabled', on ? 'true' : 'false');
      });
  }
  function showStatus(text, spinning = true) {
    const el = document.getElementById('actionStatusModal');
    const modal = bootstrap.Modal.getOrCreateInstance(el);
    document.getElementById('actionText').textContent = text;
    document.getElementById('actionSpinner').style.display = spinning ? '' : 'none';
    modal.show();
    return modal;
  }

  function ajaxSubmit(formId, submitBtnId, successText) {
    const form = document.getElementById(formId);
    const btn  = document.getElementById(submitBtnId);
    if (!form || !btn) return;

    form.addEventListener('submit', function (e) {
      e.preventDefault();

      // 1) client-side required check (because we prevented native submit)
      const requiredField = form.querySelector('[required]');
      if (requiredField && !requiredField.value.trim()) {
        // show inline bootstrap alert inside the modal body
        const body = form.querySelector('.modal-body');
        if (body && !body.querySelector('.alert')) {
          const al = document.createElement('div');
          al.className = 'alert alert-light text-center border mb-3';
          al.textContent = 'A reason/message is required to decline.';
          body.prepend(al);
          setTimeout(() => al.remove(), 2000);
        }
        requiredField.focus();
        return;
      }

      // 2) build payload BEFORE disabling elements
      const payload = new FormData(form);

      // 3) now lock UI and show processing
      disableModalControls(form, true);
      btn.disabled = true;
      btn.innerHTML = '<span class="spinner-border spinner-border-sm me-2"></span>Processing…';
      const statusModal = showStatus('Processing…', true);

      // 4) send
      fetch(form.action, {
        method: 'POST',
        headers: {
          'X-Requested-With': 'XMLHttpRequest',
          'X-CSRFToken': getCsrf(form),
        },
        body: payload,
        redirect: 'follow'
      })
      .then(async (r) => {
        const ct = (r.headers.get('Content-Type') || '').toLowerCase();
        if (ct.includes('application/json')) {
          const data = await r.json();
          if (!r.ok || data.ok === false) throw new Error(data.error || 'Server error.');
        } else {
          if (!r.ok) throw new Error(`Server error (${r.status})`);
        }
        document.getElementById('actionSpinner').style.display = 'none';
        document.getElementById('actionText').textContent = successText;
        setTimeout(() => {
          statusModal.hide();
          window.location.reload();
        }, 900);
      })
      .catch(err => {
        document.getElementById('actionSpinner').style.display = 'none';
        document.getElementById('actionText').textContent = err.message || 'Something went wrong.';
        // re-enable so user can retry
        disableModalControls(form, false);
        btn.disabled = false;
        btn.textContent = (submitBtnId === 'acceptSubmitBtn') ? 'Accept' : 'Decline Request';
      });
    });
  }

  ajaxSubmit('acceptForm',  'acceptSubmitBtn',  'Accepted! Email sent.');
  ajaxSubmit('declineForm', 'declineSubmitBtn', 'Declined. Email sent.');
})();


//////////////////////////////////////////////////////////////////////
  window.addEventListener('pageshow', function (e) {
    if (e.persisted) location.reload();
  });
/////////////////////////////////////////////////////////////////////

/* One-click guard tied to the actual submit event (safe with your AJAX + CSRF) */
(() => {
  const PAIRS = [
    ['acceptForm',  'acceptSubmitBtn'],
    ['declineForm', 'declineSubmitBtn']
  ];
  const inFlight = new Set();
  let safetyTimer = null;

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
      inFlight.clear();
      document.querySelectorAll('.modal-footer .disabled').forEach(b => {
        b.classList.remove('disabled');
        b.removeAttribute('aria-disabled');
        b.style.pointerEvents = '';
        b.style.opacity = '';
        b.style.cursor = '';
      });
    }, 15000);
  }

  function wire(formId, submitBtnId) {
    const form = document.getElementById(formId);
    if (!form) return;

    form.addEventListener('submit', (e) => {
      // If already in-flight, block duplicates
      if (inFlight.has(form)) { e.preventDefault(); e.stopPropagation(); return false; }

      // Respect your required validation (e.g., decline reason)
      const must = form.querySelector('[required]');
      if (must && !String(must.value).trim()) {
        // Let your existing code show the inline alert; do NOT lock
        return;
      }

      // First valid submit → lock this form
      inFlight.add(form);

      // Prefer the actual submitter button (mouse or Enter key)
      const clicked = e.submitter || document.getElementById(submitBtnId)
                     || form.querySelector('.modal-footer button[type="submit"]');
      if (clicked) lockFooterButtons(clicked);

      // Do NOT disable inputs; your AJAX handler will build FormData and disable controls.
      armSafetyReset();
      // Allow your existing AJAX submit handler to run normally.
    }, true);
  }

  PAIRS.forEach(([formId, btnId]) => wire(formId, btnId));

  // Clear on navigation/back-forward cache restore
  window.addEventListener('pageshow', () => {
    inFlight.clear();
    clearTimeout(safetyTimer);
  });
})();
