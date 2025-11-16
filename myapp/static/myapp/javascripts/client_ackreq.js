



document.addEventListener("DOMContentLoaded", function () {
    const extYes = document.getElementById("extYes");
    const extNo = document.getElementById("extNo");
    const extensionCol = document.getElementById("extensionCol");
    const extensionInput = document.getElementById("ex_surrender");

    function toggleExtension() {
        if (extYes.checked) {
            extensionCol.classList.remove("d-none");  // Show extension
            extensionInput.focus();
        } else {
            extensionCol.classList.add("d-none");     // Hide extension
            extensionInput.value = "";
        }
    }

    toggleExtension();
    extYes.addEventListener("change", toggleExtension);
    extNo.addEventListener("change", toggleExtension);
});


(function () {
  // ----- CONFIG -----
  const FIELD_IDS = [
    'doc_type',
    'fn_surrender','mn_surrender','sn_surrender','program_surrender','email_surrender',
    'address_surrender','age_surrender','sex_surrender','contact_surrender',
    'client_type_surrender','stakeholder_surrender',   
    'reason_surrender','studentID_surrender','yearlevel_surrender', 
    'stay_surrender','front_surrender','back_surrender'
  ];
  const MB = 1024 * 1024, LIMIT_MB = 10, ALLOWED_EXT = ['jpg','jpeg','png','pdf'];

  // ----- ELEMENTS -----
  const form = document.getElementById('surrender-form') || document.querySelector('form');
  const submitBtn = document.getElementById('submitBtn') || (form && form.querySelector('button[type="submit"]'));
  const alertBox = document.getElementById('formAlert');

  const modalEl = document.getElementById('submissionModal');
  const hasBootstrap = typeof bootstrap !== 'undefined' && modalEl;
  const modal = hasBootstrap ? new bootstrap.Modal(modalEl, { backdrop: 'static', keyboard: false }) : null;
  const titleEl = modalEl ? document.getElementById('submissionModalLabel') : null;
  const bodyEl  = modalEl ? document.getElementById('submissionModalBody') : null;
  const footer  = modalEl ? modalEl.querySelector('.modal-footer') : null;

  const docTypeSel = document.getElementById('doc_type');

  if (!form || !submitBtn) return;

  // ----- HELPERS -----
  function elById(id) { return document.getElementById(id); }

  function ensureFeedback(el) {
    if (!el.nextElementSibling || !el.nextElementSibling.classList.contains('invalid-feedback')) {
      const fb = document.createElement('div');
      fb.className = 'invalid-feedback';
      fb.textContent = 'This field is required.';
      el.after(fb);
    }
    return el.nextElementSibling;
  }

  function setInvalid(el, msg = 'This field is required.') {
    el.classList.add('is-invalid');
    el.classList.remove('is-valid');
    el.setCustomValidity(msg);
    ensureFeedback(el).textContent = msg;
  }

  function setValid(el) {
    el.classList.remove('is-invalid');
    el.classList.add('is-valid');
    el.setCustomValidity('');
  }

  function fileOk(input) {
    const f = input.files && input.files[0];
    if (!f) {
      if (input.required) { setInvalid(input, 'This file is required.'); return false; }
      setValid(input); return true;
    }
    const ext = f.name.split('.').pop().toLowerCase();
    if (!ALLOWED_EXT.includes(ext)) { setInvalid(input, `Allowed types: ${ALLOWED_EXT.join(', ')}`); return false; }
    if (f.size > LIMIT_MB * MB) { setInvalid(input, `Max file size is ${LIMIT_MB} MB.`); return false; }
    setValid(input); return true;
  }

  // UPDATED: validation (names allow internal spaces; email forbids any spaces)
  function textOk(input) {
    const raw = input.value || '';
    const val = raw.trim(); // validate against trimmed; don't rewrite while typing

    // Email: no spaces at all
    if (input.id === 'email_surrender') {
      if (/\s/.test(raw)) { setInvalid(input, 'Email cannot contain spaces.'); return false; }
      const ok = /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(raw);
      if (!ok) { setInvalid(input, 'Enter a valid email address.'); return false; }
      setValid(input); return true;
    }

    // First/Surname: allow internal spaces, disallow spaces-only
    if (input.id === 'fn_surrender' || input.id === 'sn_surrender') {
      if (!val) { setInvalid(input, 'Enter a name.'); return false; }
      setValid(input); return true;
    }

    if (!val) { setInvalid(input); return false; }

    const pattern = input.getAttribute('pattern');
    if (pattern) {
      try {
        const re = new RegExp(pattern);
        if (!re.test(val)) {
          if (input.id === 'studentID_surrender') setInvalid(input, 'Format: TUPC-XX-XXXX (last block 4–15 characters).');
          else if (input.id === 'stay_surrender') setInvalid(input, 'Use YYYY-YYYY (e.g., 2019-2023).');
          else setInvalid(input, 'Invalid format.');
          return false;
        }
      } catch(_) {}
    }
    setValid(input); return true;
  }

  function selectOk(sel) {
    if (!sel.value) { setInvalid(sel, 'Please choose an option.'); return false; }
    setValid(sel); return true;
  }

  function validateFieldById(id) {
    const el = elById(id);
    if (!el) return true;

    // --- Files still use your custom validator ---
    if (el.type === 'file') {
      return fileOk(el);
    }

    const raw = el.value || '';      // what the user actually typed
    const trimmed = raw.trim();      // for "is empty?" checks etc.

    // ------------------------------------------------
    // 1) First / Middle / Surname: letters + ñ + ' + - + spaces
    // ------------------------------------------------
    if (id === 'fn_surrender' || id === 'mn_surrender' || id === 'sn_surrender') {
      // First & surname: required
      if (!trimmed && (id === 'fn_surrender' || id === 'sn_surrender')) {
        setInvalid(el, 'This field is required.');
        return false;
      }

      // Middle name: optional, empty = NEUTRAL (no green, no red)
      if (!trimmed && id === 'mn_surrender') {
        el.classList.remove('is-valid', 'is-invalid');
        el.setCustomValidity('');
        return true; // don't block submit
      }

      // Allow letters, ñ/Ñ, apostrophe, hyphen, AND spaces
      const nameRe = /^[A-Za-zÑñ' -]+$/;
      if (!nameRe.test(raw)) {                 // use raw so spaces are allowed naturally
        setInvalid(el, "Only letters, spaces, ñ, apostrophe (') and hyphen (-) are allowed.");
        return false;
      }

      // DO NOT touch el.value here; let the user keep spaces while typing
      setValid(el);
      return true;
    }

    // ------------------------------------------------
    // 2) Student Number: required, TUPC-XX-XXXX…
    // ------------------------------------------------
    if (id === 'studentID_surrender') {
      if (!trimmed) {
        setInvalid(el, 'Student number is required.');
        return false;
      }

      const re = /^TUPC-\d{2}-[A-Za-z0-9]{4,15}$/;
      if (!re.test(trimmed)) {
        setInvalid(
          el,
          "Use TUPC-XX-XXXX up to TUPC-XX-XXXXXXXXXX (last block 4–15 letters/digits)."
        );
        return false;
      }

      setValid(el);
      return true;
    }

    // ------------------------------------------------
    // 3) Inclusive years of stay: YYYY-YYYY, 2014–current year
    // ------------------------------------------------
    if (id === 'stay_surrender') {
      if (!trimmed) {
        setInvalid(el, 'This field is required.');
        return false;
      }

      const m = /^(\d{4})-(\d{4})$/.exec(trimmed);
      if (!m) {
        setInvalid(el, 'Use YYYY-YYYY (e.g., 2019-2023).');
        return false;
      }

      const start = parseInt(m[1], 10);
      const end   = parseInt(m[2], 10);
      const currentYear = new Date().getFullYear();

      if (start > end) {
        setInvalid(el, 'End year cannot be earlier than start year.');
        return false;
      }
      if (start < 2014 || end < 2014 || start > currentYear || end > currentYear) {
        setInvalid(el, `Years must be between 2014 and ${currentYear}.`);
        return false;
      }

      setValid(el);
      return true;
    }

    // ------------------------------------------------
    // 4) Everything else: use built-in HTML5 validity (age, email, ADDRESS, etc.)
    //    IMPORTANT: do NOT overwrite el.value here, or you kill spaces.
    // ------------------------------------------------
    el.setCustomValidity('');  // clear any previous custom error

    if (!el.checkValidity()) {
      let msg = el.validationMessage || 'Invalid value.';

      // nicer messages for some special cases (if needed)
      if (id === 'stay_surrender') {
        msg = 'Use YYYY-YYYY (e.g., 2019-2023).';
      } else if (id === 'studentID_surrender') {
        msg = "Use TUPC-XX-XXXX up to TUPC-XX-XXXXXXXXXX (last block 4–15 letters/digits).";
      }

      setInvalid(el, msg);
      return false;
    }

    setValid(el);
    return true;
  }


  function firstInvalidEl() {
    for (const id of FIELD_IDS) {
      const el = elById(id);
      if (!el) continue;
      if (el.classList.contains('is-invalid')) return el;
      const ok = validateFieldById(id);
      if (!ok) return el;
    }
    return null;
  }

  function updateSubmitState(showAlert = true) {
    let allGood = true;
    FIELD_IDS.forEach(id => { if (!validateFieldById(id)) allGood = false; });
    submitBtn.disabled = !allGood;
    if (alertBox && showAlert) alertBox.classList.toggle('d-none', allGood);
    return allGood;
  }

  // UPDATED: show/hide upload fields based on selection + set requireds
  function setUploadMode(mode) {
    const front = document.getElementById('front_surrender');
    const back  = document.getElementById('back_surrender');
    const frontLabel = document.getElementById('frontLabel');
    const backLabel  = document.getElementById('backLabel');
    const frontGroup = document.getElementById('frontGroup');
    const backGroup  = document.getElementById('backGroup');
    if (!front || !back || !frontGroup || !backGroup) return;

    // reset visual state
    [front, back].forEach(el => {
      el.classList.remove('is-valid','is-invalid');
      el.setCustomValidity('');
    });

    if (mode === 'id') {
      front.required = true;  back.required = true;
      if (frontLabel) frontLabel.textContent = 'Upload ID (Front):';
      if (backLabel)  backLabel.textContent  = 'Upload ID (Back):';
      frontGroup.classList.remove('d-none');
      backGroup.classList.remove('d-none');
    } else if (mode === 'affidavit') {
      front.required = true;  back.required = false;
      if (frontLabel) frontLabel.textContent = 'Affidavit of Loss (First Page):';
      if (backLabel)  backLabel.textContent  = 'Affidavit of Loss (Second Page, optional):';
      frontGroup.classList.remove('d-none');
      backGroup.classList.remove('d-none'); // visible but optional
    } else {
      // no selection: hide both, clear requirements & values
      front.required = false; back.required = false;
      front.value = ''; back.value = '';
      frontGroup.classList.add('d-none');
      backGroup.classList.add('d-none');
      if (frontLabel) frontLabel.textContent = 'Upload ID (Front) / Affidavit First Page:';
      if (backLabel)  backLabel.textContent  = 'Upload ID (Back) / Affidavit Second Page:';
    }
  }

  // ----- INIT + LIVE -----
  setUploadMode(docTypeSel ? docTypeSel.value : '');
  FIELD_IDS.forEach(id => {
    const el = elById(id);
    if (!el) return;
    const evt = (el.type === 'file' || el.tagName === 'SELECT') ? 'change' : 'input';
    el.addEventListener(evt, () => updateSubmitState(true));
  });

  // Trim names on blur (allow internal spaces; strip ends only)
  ['fn_surrender','sn_surrender'].forEach(id => {
    const el = document.getElementById(id);
    if (el) el.addEventListener('blur', () => {
      el.value = (el.value || '').trim();
      updateSubmitState(true);
    });
  });

  // Remove spaces live from email
  const emailEl = document.getElementById('email_surrender');
  if (emailEl) emailEl.addEventListener('input', () => {
    const cleaned = emailEl.value.replace(/\s+/g, '');
    if (emailEl.value !== cleaned) emailEl.value = cleaned;
  });

  if (docTypeSel) {
    docTypeSel.addEventListener('change', () => {
      setUploadMode(docTypeSel.value);
      updateSubmitState(true);
    });
  }

  const contactEl = document.getElementById('contact_surrender');
  if (contactEl) {
    contactEl.addEventListener('input', () => {
      // Keep +63-XXX-XXX-XXXX shape without forcing cursor jumps
      let v = contactEl.value.replace(/[^\d+]/g, '');
      if (!v.startsWith('+63')) v = '+63' + v.replace(/^\+?63?/, '');
      v = v.replace(/^\+63/, '+63');
      // Strip +63, format the rest as XXX-XXX-XXXX if possible
      let rest = v.replace(/^\+63/, '');
      rest = rest.replace(/^(\d{0,3})(\d{0,3})(\d{0,4}).*$/, (_, a, b, c) =>
        [a, b, c].filter(Boolean).join('-')
      );
      const formatted = '+63' + (rest ? '-' + rest : '');
      if (contactEl.value !== formatted) contactEl.value = formatted;
      updateSubmitState(true);
    });
  }
  updateSubmitState(false);

  // ----- SUBMIT -----
  form.addEventListener('submit', (e) => {
    ['fn_surrender','sn_surrender'].forEach(id => {
      const el = document.getElementById(id);
      if (el) el.value = (el.value || '').trim();
    });

    const ok = updateSubmitState(true);
    if (!ok) {
      e.preventDefault();
      const bad = firstInvalidEl();
      if (bad) bad.scrollIntoView({ behavior: 'smooth', block: 'center' });
      return;
    }
    if (modal) {
      if (titleEl) titleEl.textContent = 'Submitting Request…';
      if (bodyEl) {
        bodyEl.innerHTML = `
          <div class="d-flex align-items-center">
            <div class="spinner-border me-3" role="status" aria-hidden="true"></div>
            <div>Please wait while we submit your request…</div>
          </div>`;
      }
      if (footer) footer.classList.add('d-none');
      modal.show();
    }
  });
})();

