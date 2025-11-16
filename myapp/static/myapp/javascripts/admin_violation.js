

/* =========================
   OSA Violations — Scanner-Safe + Snap-to-ID + Robust Lookup
   Update: STRICT TUPC clamp → keeps ONLY "TUPC-##-####" and auto-cuts trailing letters/spaces
========================= */
(() => {
  const form    = document.getElementById('majorForm');
  if (!form) return;

  const sid       = document.getElementById('student_id');
  const fb        = document.getElementById('studentLookupFeedback');
  const saveBtn   = document.getElementById('saveBtn');
  const overlay   = document.getElementById('loadingOverlay');

  const minorWrapper = document.getElementById('minorWrapper');
  const majorWrapper = document.getElementById('majorWrapper');
  const btnMinor     = document.getElementById('btnMinor');
  const btnMajor     = document.getElementById('btnMajor');
  const minorSel     = form.querySelector('[name="minor_offense"]');
  const majorSel     = form.querySelector('[name="violation_type"]');
  const choiceError  = document.getElementById('violationChoiceError');
  const ev1          = form.querySelector('[name="evidence_1"]');
  const ev2          = form.querySelector('[name="evidence_2"]');
  const ev1Err       = document.getElementById('evidence1ClientError');
  const ev2Err       = document.getElementById('evidence2ClientError');

  // ⬇️ STRICT: exactly 2 digits, a dash, then exactly 4 digits
  const TUPC_FULL = /^TUPC-\d{2}-\d{4}$/;         // full, valid
  const TUPC_ANY  = /TUPC-\d{2}-\d{4}/i;          // first occurrence anywhere

  const SCAN_LOCK_MS = 250;
  let scanLockUntil = 0;

  function setFeedback(kind, text) {
    if (!fb) return;
    fb.className = 'small mt-1 ' + (kind==='ok' ? 'text-success' : kind==='warn' ? 'text-warning' : 'text-danger');
    fb.textContent = text || '';
  }

  // Uppercase, strip weird whitespace, keep ASCII letters/digits/dash/space
  function normalizeSoft(v) {
    return String(v||'')
      .toUpperCase()
      .replace(/[\r\n\t]/g, ' ')
      .replace(/[^A-Z0-9\- ]/g, '');
  }

  // NEW: clamp to first exact TUPC-##-####; auto-truncate anything after it
  function clampToTupc(v) {
    v = normalizeSoft(v).replace(/\s+/g, ''); // also drop spaces for scanners like "0374 RIBE"
    const m = v.match(TUPC_ANY);
    return m ? m[0] : v;
  }

  function extractFirstTupc(v) {
    const m = String(v||'').toUpperCase().match(TUPC_ANY);
    return m ? m[0] : '';
  }

  function getLookupPrefix() {
    const raw = sid?.dataset?.lookupPrefix || "";
    const beforePipe = raw.split('|')[0];
    const cleaned = beforePipe.replace(/TUPC-00-0000\/?$/i, '');
    return cleaned.endsWith('/') ? cleaned : cleaned + '/';
  }

  function fillIfEmpty(name, val) {
    const el = form.querySelector(`[name="${name}"]`);
    if (el && !el.value) el.value = val || '';
  }

  const ALLOWED = new Set(['image/jpeg','image/png','image/webp','image/gif']);
  const MAX_MB  = 5;
  function validateEvidence(input, errBox) {
    if (!input || !input.files || !input.files.length) { errBox?.classList.add('d-none'); return true; }
    const f = input.files[0];
    let msg = '';
    if (f.size > MAX_MB * 1024 * 1024) msg = `File too large. Max ${MAX_MB} MB.`;
    else if (f.type && !ALLOWED.has(f.type.toLowerCase())) msg = 'Unsupported image type.';
    if (errBox) {
      if (msg) { errBox.textContent = msg; errBox.classList.remove('d-none'); }
      else { errBox.textContent = ''; errBox.classList.add('d-none'); }
    }
    return !msg;
  }

  function validateRequiredFields() {
    const req = ['last_name','first_name','student_id','program_course','violation_date','violation_time'];
    let ok = true;
    req.forEach(n => {
      const el = form.querySelector(`[name="${n}"]`);
      if (!el) return;
      const has = String(el.value||'').trim() !== '';
      let valid = true;
      if (n === 'student_id') valid = TUPC_FULL.test(el.value);
      else if (el.type === 'date' || el.type === 'time') valid = has;
      else { try { valid = el.checkValidity(); } catch { valid = has; } }
      el.style.borderColor = has && valid ? '#28a745' : '#dc3545';
      if (!(has && valid)) ok = false;
    });
    return ok;
  }

  function validateOffenseChoice() {
    const a = !!(minorSel && minorSel.value.trim());
    const b = !!(majorSel && majorSel.value.trim());
    const ok = (a ^ b);
    if (choiceError) {
      choiceError.classList.toggle('d-none', ok);
      if (!ok) {
        choiceError.textContent = a && b
          ? 'Please select only one: Minor OR Major.'
          : 'Please select either a Minor offense OR a Major offense.';
      }
    }
    return ok;
  }

  function updateSaveState() {
    const ok = validateRequiredFields() &&
               validateOffenseChoice() &&
               validateEvidence(ev1, ev1Err) &&
               validateEvidence(ev2, ev2Err);
    if (saveBtn) {
      saveBtn.disabled = !ok;
      saveBtn.style.opacity = ok ? '1' : '0.65';
      saveBtn.style.cursor  = ok ? 'pointer' : 'not-allowed';
    }
  }

  async function doLookupNow() {
    const id = (sid.value || '').toUpperCase().trim();
    if (!TUPC_FULL.test(id)) return;

    const url = getLookupPrefix() + encodeURIComponent(id) + '/';
    setFeedback('warn', 'Looking up student…');

    try {
      const res = await fetch(url, { headers: { 'Accept': 'application/json' } });
      if (!res.ok) throw new Error('HTTP ' + res.status + ' for ' + url);
      const data = await res.json();

      if (data && data.success) {
        fillIfEmpty('last_name',      data.last_name);
        fillIfEmpty('first_name',     data.first_name);
        fillIfEmpty('middle_initial', data.middle_initial);
        fillIfEmpty('extension_name', data.extension);
        fillIfEmpty('program_course', data.program);
        setFeedback('ok', 'Student found. Fields filled (you can still edit).');
      } else {
        setFeedback('err', 'Student not found.');
      }
    } catch (err) {
      console.error('[TUPC lookup error]', err);
      setFeedback('err', 'Lookup failed. Check network/URL. See console.');
    } finally {
      updateSaveState();
    }
  }

  function setNowDefaults() {
    const d = form.querySelector('[name="violation_date"]');
    const t = form.querySelector('[name="violation_time"]');
    if (d && !d.value) d.value = new Date().toISOString().split('T')[0];
    if (t && !t.value) t.value = new Date().toLocaleTimeString('en-US',{hour12:false}).slice(0,5);
  }
  setNowDefaults();

  document.getElementById('majorOffenseModal')?.addEventListener('shown.bs.modal', () => sid?.focus());

  function showMinor(){ minorWrapper?.classList.remove('d-none'); majorWrapper?.classList.add('d-none'); btnMinor?.classList.add('active-offense'); btnMajor?.classList.remove('active-offense'); }
  function showMajor(){ majorWrapper?.classList.remove('d-none'); minorWrapper?.classList.add('d-none'); btnMajor?.classList.add('active-offense'); btnMinor?.classList.remove('active-offense'); }
  function hideBoth(){  minorWrapper?.classList.add('d-none');   majorWrapper?.classList.add('d-none');   btnMinor?.classList.remove('active-offense'); btnMajor?.classList.remove('active-offense'); }
  hideBoth();

  btnMinor?.addEventListener('click', () => { if (!minorWrapper?.classList.contains('d-none')) { hideBoth(); minorSel.value=''; } else { showMinor(); majorSel.value=''; } updateSaveState(); });
  btnMajor?.addEventListener('click', () => { if (!majorWrapper?.classList.contains('d-none')) { hideBoth(); majorSel.value=''; } else { showMajor(); minorSel.value=''; } updateSaveState(); });
  minorSel?.addEventListener('change', () => { if (minorSel.value) { majorSel.value=''; showMinor(); } updateSaveState(); });
  majorSel?.addEventListener('change', () => { if (majorSel.value) { minorSel.value=''; showMajor(); } updateSaveState(); });

  form.addEventListener('keydown', (e) => {
    if (e.key === 'Enter' && e.target.tagName !== 'TEXTAREA') e.preventDefault();
  });

  if (sid) {
    // Hard-cap: "TUPC-##-####" = 12 chars
    sid.setAttribute('maxlength', '12');
    sid.setAttribute('autocomplete', 'off');

    sid.addEventListener('input', () => {
      // normalize and clamp immediately; cut trailing letters like "RIBE"
      const v = clampToTupc(sid.value);
      // During fast scanner bursts, avoid flicker
      if (Date.now() < scanLockUntil) {
        sid.value = v;
        return;
      }
      sid.value = v;

      const found = extractFirstTupc(sid.value);
      if (found) {
        sid.value = found;                 // <-- trims to EXACT pattern
        scanLockUntil = Date.now() + SCAN_LOCK_MS;
        doLookupNow();
      }
    });

    ['change','blur'].forEach(ev => sid.addEventListener(ev, () => {
      sid.value = clampToTupc(sid.value);
      const found = extractFirstTupc(sid.value);
      if (found) sid.value = found;
      doLookupNow();
    }));

    sid.addEventListener('keydown', (e) => {
      if (e.key === 'Enter') {
        e.preventDefault();
        sid.value = clampToTupc(sid.value);
        const found = extractFirstTupc(sid.value);
        if (found) sid.value = found;
        doLookupNow();
      }
    });

    sid.addEventListener('paste', () => {
      setTimeout(() => {
        sid.value = clampToTupc(sid.value);
        const found = extractFirstTupc(sid.value);
        if (found) sid.value = found;
        doLookupNow();
      }, 0);
    });
  }

  form.addEventListener('submit', (e) => {
    sid && (sid.value = clampToTupc(sid.value));  // final guard
    updateSaveState();
    if (saveBtn && saveBtn.disabled) { e.preventDefault(); e.stopPropagation(); return; }
    overlay && (overlay.style.display = 'flex');
  });

  function clearFormVisuals() {
    form.querySelectorAll('input,select,textarea').forEach(el => el.style.borderColor = '');
    setFeedback('ok', '');
    ev1Err && (ev1Err.textContent = '', ev1Err.classList.add('d-none'));
    ev2Err && (ev2Err.textContent = '', ev2Err.classList.add('d-none'));
    choiceError?.classList.add('d-none');
  }
  function resetForm() {
    form.reset();
    clearFormVisuals();
    hideBoth();
    setNowDefaults();
    scanLockUntil = 0;
  }

  const majorModalEl = document.getElementById('majorOffenseModal');
  majorModalEl?.addEventListener('hidden.bs.modal', () => {
    overlay && (overlay.style.display = 'none');
    document.body.classList.remove('modal-open');
    document.querySelectorAll('.modal-backdrop').forEach(b => b.remove());
    resetForm();
  });
  document.querySelectorAll('[data-bs-dismiss="modal"]').forEach(btn => {
    btn.addEventListener('click', () => {
      overlay && (overlay.style.display = 'none');
      setTimeout(() => {
        document.body.classList.remove('modal-open');
        document.querySelectorAll('.modal-backdrop').forEach(b => b.remove());
      }, 300);
      resetForm();
    });
  });


  updateSaveState();
})();




////////////////////////////////////////////////////////////////////////////////////////
  window.addEventListener('pageshow', function (e) {
      if (e.persisted) location.reload();
  });
  function toggleSidebar() {
      document.getElementById('sidebar').classList.toggle('show');
    }

    function handleDropdown(id) {
      const icon = document.getElementById('icon-' + id);
      const target = document.getElementById(id);
      const bsTarget = bootstrap.Collapse.getOrCreateInstance(target);

      if (target.classList.contains('show')) {
        bsTarget.hide();
        icon.classList.remove('rotate');
      } else {
        bsTarget.show();
        icon.classList.add('rotate');
      }

      const allMenus = ['violationMenu', 'documentsMenu', 'postingsMenu'];
      allMenus.forEach(menu => {
        if (menu !== id) {
          const el = document.getElementById(menu);
          const ic = document.getElementById('icon-' + menu);
          const bs = bootstrap.Collapse.getInstance(el);
          if (bs) bs.hide();
          if (ic) ic.classList.remove('rotate');
        }
      });
    }

    // Smooth Highlighting Active Link
    document.addEventListener("DOMContentLoaded", function () {
      const currentUrl = window.location.href;
      const navLinks = document.querySelectorAll(".nav-link");

      navLinks.forEach(link => {
        if (link.href && currentUrl.includes(link.href)) {
          link.classList.add("active");
        }
      });
    });




// Para mawala blinking ng 
    document.addEventListener('DOMContentLoaded', () => {
    const table = document.getElementById('violations_pending_table');

    // Lock interaction during hover or click
    table.addEventListener('mouseenter', () => table.classList.add('interacting'));
    table.addEventListener('mouseleave', () => table.classList.remove('interacting'));
    table.addEventListener('click', () => {
      table.classList.add('interacting');
      setTimeout(() => table.classList.remove('interacting'), 4000); // resume after 4s
    });
  });

/////////////////////////////////////////////////////////////////////////////////////
/* One-click-only for Approve/Lift (anchors or buttons with data-safe-nav) */
(() => {
  if (typeof window.__navClicking === 'undefined') window.__navClicking = false;

  function lockRowButtons(anchor) {
    const row = anchor.closest('tr');
    if (!row) return;
    row.querySelectorAll('a[data-safe-nav],button[data-safe-nav]').forEach(btn => {
      btn.classList.add('disabled');
      btn.setAttribute('aria-disabled', 'true');
      btn.style.pointerEvents = 'none';
      btn.style.opacity = '0.6';
      const label = btn.textContent.trim() || 'Working';
      btn.innerHTML = '<span class="spinner-border spinner-border-sm me-1" role="status" aria-hidden="true"></span>' + label;
    });
  }
  const overlay = document.getElementById('loadingOverlay');
  const showOverlay = () => { if (overlay) overlay.style.display = 'flex'; };
  const hideOverlay = () => { if (overlay) overlay.style.display = 'none'; };

  document.addEventListener('click', (e) => {
    const a = e.target.closest('a[data-safe-nav],button[data-safe-nav]');
    if (!a) return;

    if (window.__navClicking) { // already in-flight → ignore
      e.preventDefault(); e.stopPropagation(); return false;
    }
    window.__navClicking = true;
    lockRowButtons(a);
    showOverlay();
    setTimeout(() => { window.__navClicking = false; hideOverlay(); }, 12000);
  });

  window.addEventListener('pageshow', () => {
    window.__navClicking = false;
    hideOverlay();
  });
})();


/////////////////////////////////////////////////////////////////////////////////////
// /* One-click-only for "Save" on #majorForm" — inputs stay enabled so POST includes CSRF + fields */
(() => {
  const form = document.getElementById('majorForm');
  if (!form) return;

  const saveBtn = document.getElementById('saveBtn');
  const overlay = document.getElementById('loadingOverlay');
  if (typeof window.__navClicking === 'undefined') window.__navClicking = false;

  let submitting = false, resetTimer = null;
  const showOverlay = () => { if (overlay) overlay.style.display = 'flex'; };
  const hideOverlay  = () => { if (overlay) overlay.style.display = 'none'; };

  function lockSubmitButtons() {
    // Lock only submit-type buttons; DO NOT disable inputs/CSRF fields.
    form.querySelectorAll('button[type="submit"]').forEach(btn => {
      btn.classList.add('disabled');
      btn.setAttribute('aria-disabled', 'true');
      btn.style.pointerEvents = 'none';
      btn.style.opacity = '0.7';
      btn.style.cursor  = 'not-allowed';
      if (btn === saveBtn) {
        const label = btn.textContent.trim() || 'Saving';
        btn.innerHTML = '<span class="spinner-border spinner-border-sm me-1" role="status" aria-hidden="true"></span>' + label;
      }
    });
  }

  function armSafetyReset() {
    clearTimeout(resetTimer);
    resetTimer = setTimeout(() => {
      submitting = false; window.__navClicking = false;
      form.querySelectorAll('button[type="submit"]').forEach(btn => {
        btn.classList.remove('disabled');
        btn.removeAttribute('aria-disabled');
        btn.style.pointerEvents = '';
        btn.style.opacity = '';
        btn.style.cursor  = '';
      });
      hideOverlay();
    }, 15000);
  }

  saveBtn?.addEventListener('click', (e) => {
    if (submitting) { e.preventDefault(); e.stopPropagation(); return false; }
  });

  form.addEventListener('submit', (e) => {
    if (submitting) { e.preventDefault(); e.stopPropagation(); return false; }
    if (saveBtn && saveBtn.disabled) { e.preventDefault(); return false; } // respect your existing validation

    submitting = true;
    window.__navClicking = true;     // keeps your HTMX list from swapping mid-submit
    lockSubmitButtons();              // <-- only buttons, not inputs
    showOverlay();
    armSafetyReset();
    // Let the native submit proceed normally.
  });

  window.addEventListener('pageshow', () => {
    submitting = false; window.__navClicking = false;
    clearTimeout(resetTimer); hideOverlay();
  });
})();

/////////////////////////////////////////////////////////////////////////////////////
(function () {
  var loginUrl = "{% url 'login' %}";
  function goLogin() {
    var next = encodeURIComponent(location.pathname + location.search + location.hash);
    location.replace(loginUrl + "?next=" + next);
  }

  if (window.htmx) {
    document.body.addEventListener("htmx:configRequest", function (e) {
      var evt = e.detail.triggeringEvent;
      var el = e.target;
      var trig = (el.getAttribute("hx-trigger") || "");
      var isPolling = trig.indexOf("every") !== -1;
      if (evt && !isPolling) e.detail.headers["X-User-Activity"] = "1";
    });

    document.body.addEventListener("htmx:responseError", function (e) {
      var s = e.detail && e.detail.xhr && e.detail.xhr.status;
      if (s === 401 || s === 440) goLogin();
    });

    document.addEventListener("visibilitychange", function () {
      if (document.hidden) {
        document.querySelectorAll('[hx-trigger*="every"]').forEach(function (el) {
          el.setAttribute("data-poll-off", "1");
          el.setAttribute("hx-trigger", (el.getAttribute("hx-trigger") || "") + " consume");
        });
      } else {
        document.querySelectorAll('[data-poll-off="1"]').forEach(function (el) {
          el.removeAttribute("data-poll-off");
          el.setAttribute("hx-trigger", (el.getAttribute("hx-trigger") || "").replace(/\s*consume\b/, ""));
          if (el.matches("[hx-get],[hx-post],[hx-put],[hx-patch]")) htmx.trigger(el, "refresh");
        });
      }
    });
  }

  if (!window.__fetchAuthWrapped) {
    var _fetch = window.fetch;
    window.fetch = function () {
      var args = Array.prototype.slice.call(arguments);
      var req = args[0];
      var init = args[1] || {};
      var method = (init.method || (req && req.method) || "GET").toUpperCase();
      var isWrite = method !== "GET";
      init.headers = new Headers(init.headers || (req && req.headers) || {});
      if (isWrite) init.headers.set("X-User-Activity", "1");
      args[1] = init;
      return _fetch.apply(this, args).then(function (res) {
        if (res && (res.status === 401 || res.status === 440)) { goLogin(); return new Promise(function () {}); }
        return res;
      });
    };
    window.__fetchAuthWrapped = true;
  }

  window.addEventListener("pageshow", function (e) {
    if (e.persisted) location.reload();
  });
})();
