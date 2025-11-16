
  const RE_PHONE_HYPHEN = /^\+63\s\d{3}-\d{3}-\d{4}$/;
  const RE_PHONE_PLAIN  = /^\+63\s\d{10}$/;

  function digitsOnly(s){ return (s||"").replace(/\D+/g,""); }

  function formatPhMobileHyphenated(raw){
    const d = digitsOnly(raw);
    const rest = d.startsWith("63") ? d.slice(2) : d;
    const ten  = rest.slice(0,10);
    if (!ten) return "+63 ";
    const a = ten.slice(0,3), b = ten.slice(3,6), c = ten.slice(6,10);
    return `+63 ${a}${b?'-'+b:''}${c?'-'+c:''}`;
  }
  // ===== Utilities =====
  function rtrimInput(el) {
   el.value = el.value
     .replace(/\p{Zs}+/gu, ' ')     
     .replace(/^\s+|\s+$/g, '');    
  }
  function setClasses(el, valid) {
    el.classList.toggle('is-valid',  valid);
    el.classList.toggle('is-invalid', !valid);
  }
  function setStatusIcon(el, valid) {
    const icon = document.getElementById(el.id + '_status');
    if (!icon) return;
    icon.classList.remove('d-none','bi-check-circle-fill','bi-x-circle-fill','text-success','text-danger');
    if (valid) { icon.classList.add('bi-check-circle-fill','text-success'); }
    else       { icon.classList.add('bi-x-circle-fill','text-danger'); }
  }
  function mark(el, valid) { setClasses(el, valid); setStatusIcon(el, valid); return valid; }
  function isSelect(el){ return el && el.tagName === 'SELECT'; }

  // ===== Elements =====
  const form       = document.getElementById("clearanceForm");
  const openBtn    = document.getElementById("openConfirmModal");
  const confirmBtn = document.getElementById("confirmSubmitBtn");
  const formAlert  = document.getElementById("formAlert");

  const extYes = document.getElementById("extYes");
  const extNo  = document.getElementById("extNo");
  const extWrap= document.getElementById("extensionField");
  const extInp = document.getElementById("extension");

  const phone   = document.getElementById("contact_surrender");
  const student = document.getElementById("student_number");
  const program = document.getElementById("program");
  const ageEl  = document.getElementById("age");
  const sexEl  = document.getElementById("sex");
  const lyEl   = document.getElementById("last_year_in_tupc");
  

  const trimIds   = ["first_name","last_name","extension","email_surrender","student_number","address"];
  const baseIds   = ["first_name","last_name","email_surrender","contact_surrender","student_number","age","address","last_year_in_tupc"];
  const selectIds = ["program","year_level","client_type","stakeholder","purpose","sex"];
  

  // ===== CSV Programs (now with "Other") =====
  (async function loadPrograms() {
    try {
      const resp = await fetch("{% static 'myapp/data/programs.csv' %}", {cache:'no-store'});
      if (!resp.ok) return;
      const text = await resp.text();
      const lines = text.split(/\r?\n/).map(l => l.replace(/\s+$/,'')).filter(Boolean);
      for (const line of lines) {
        if (!line) continue;
        if (line.toLowerCase() === 'program') continue;
        const opt = document.createElement('option');
        opt.value = line; opt.textContent = line;
        program.appendChild(opt);
      }
      const otherOpt = document.createElement('option');
      otherOpt.value = '__OTHER__';
      otherOpt.textContent = 'Other';
      program.appendChild(otherOpt);

      initProgramOther();
      validateField(program);
      validateForm();
    } catch(e) {
      console.warn('Failed to load programs:', e);
    }
  })();

  // ===== Add a typable "Other" input without changing field IDs/names =====
  let programOtherInput = null;
  function initProgramOther() {
    if (!program) return;
    const wrap = program.closest('.status-wrap') || program.parentElement;
    programOtherInput = document.createElement('input');
    programOtherInput.type = 'text';
    programOtherInput.id = 'program_other';
    programOtherInput.className = 'form-control mt-2 d-none';
    programOtherInput.placeholder = 'Type your program';
    programOtherInput.setAttribute('minlength', '2');
    programOtherInput.setAttribute('maxlength', '100');
    wrap.insertAdjacentElement('afterend', programOtherInput);
    program.addEventListener('change', handleProgramChange);
    programOtherInput.addEventListener('input', () => { validateProgramOther(); validateForm(); });
    programOtherInput.addEventListener('blur',  () => { validateProgramOther(); validateForm(); });
    handleProgramChange();
  }

  function handleProgramChange() {
    if (!programOtherInput) return;
    if (program.value === '__OTHER__') {
      programOtherInput.classList.remove('d-none');
      programOtherInput.required = true;
      programOtherInput.focus();
      validateProgramOther();
      setClasses(program, validateProgramOther());
    } else {
      programOtherInput.required = false;
      programOtherInput.value = '';
      programOtherInput.classList.add('d-none');
      setClasses(programOtherInput, true);
      setClasses(program, !!program.value);
    }
  }

  function validateProgramOther() {
    if (!programOtherInput) return true;
    if (program.value !== '__OTHER__') return true;
    programOtherInput.value = programOtherInput.value.replace(/\s+$/, '');
    const len = programOtherInput.value.length;
    const ok = len >= 2 && len <= 100;
    setClasses(programOtherInput, ok);
    return ok;
  }

  // ===== Extension toggle =====
  function refreshExtension() {
    if (extYes.checked) {
      extWrap.classList.remove("d-none");
      extInp.required = true;
    } else {
      extWrap.classList.add("d-none");
      extInp.required = false;
      extInp.value = "";
      extInp.setCustomValidity("");
      setClasses(extInp, true);
      const ic = document.getElementById('extension_status');
      if (ic) ic.classList.add('d-none');
    }
    validateForm();
  }
  extYes.addEventListener("change", refreshExtension);
  extNo .addEventListener("change", refreshExtension);

  // ===== Field validators =====
  function validateField(el) {
    if (!el) return true;
    const isTyping = el === document.activeElement;
    if (!isTyping && (el.type === 'text' || el.type === 'email') && el !== phone) {
      rtrimInput(el);
     }
    if (el === phone) {
      const ok = RE_PHONE_HYPHEN.test(el.value);
      el.setCustomValidity(ok ? "" : "Use +63 XXX-XXX-XXXX.");
      return mark(el, ok);
    }

    if (el === student) {
      el.value = el.value.toUpperCase();
      const ok = el.checkValidity();
      return mark(el, ok);
    }

    if (el && el.id === "sex") {
      const ok = !!el.value;   
      el.setCustomValidity(ok ? "" : "Please select sex.");
      return mark(el, ok);
    }

    if (el.id === "last_year_in_tupc") {
      const v = el.value.trim();
      const MIN_YEAR = 1979;
      const CURRENT_YEAR = new Date().getFullYear();

      // required
      if (!v) {
        el.setCustomValidity("Please enter a year.");
        return mark(el, false);
      }

      const n = Number(v);
      const ok = Number.isInteger(n) && n >= MIN_YEAR && n <= CURRENT_YEAR;
      el.setCustomValidity(ok ? "" : `Enter a valid year (${MIN_YEAR}–${CURRENT_YEAR}).`);
      return mark(el, ok);
    }

    if (el.id === "age") {
      const v = el.value.trim();
      const n = Number(v);
      const ok = v !== "" && Number.isInteger(n) && n >= 16 && n <= 120;
      el.setCustomValidity(ok ? "" : "Out of allowed range.");
      return mark(el, ok);
    }

    if (el.id === "address") {
      rtrimInput(el);
      const len = el.value.length;
      const ok = len >= 5 && len <= 255;
      el.setCustomValidity(ok ? "" : "Address must be 5–255 characters.");
      return mark(el, ok);
    }
    if (el === program) {
      const ok = (program.value === '__OTHER__') ? validateProgramOther() : !!program.value;
      return mark(program, ok);
    }

    if (el === extInp) {
      const ok = extYes.checked ? el.checkValidity() : true;
      return mark(el, ok);
    }

    if (isSelect(el)) {
      const ok = !!el.value;
      return mark(el, ok);
    }

    const ok = el.checkValidity();
    return mark(el, ok);
  }

  function validateForm() {
    let ok = true;
    for (const id of baseIds) {
      const el = document.getElementById(id);
      if (el) ok = validateField(el) && ok;
    }
    ok = validateField(program) && ok;
    ok = validateField(extInp) && ok;

  for (const id of selectIds) {
    const el = document.getElementById(id);
    if (el) ok = validateField(el) && ok;
  }
    ok = form.checkValidity() && ok;
    openBtn.disabled = !ok;
    if (ok) formAlert.classList.add('d-none');
    return ok;
  }

  // Live listeners
  trimIds.forEach(id => {
    const el = document.getElementById(id);
    if (!el) return;
    el.addEventListener("input", () => { validateField(el); validateForm(); });
    el.addEventListener("blur",  () => { validateField(el); validateForm(); });
  });
  if (lyEl) {
    lyEl.addEventListener("input", () => { validateField(lyEl); validateForm(); });
    lyEl.addEventListener("blur",  () => { validateField(lyEl); validateForm(); });
  }
  if (phone) {
  // initialize pretty mask
  if (!phone.value.trim() || phone.value.trim() === "+63") phone.value = "+63 ";

  const validateContact = () => {
    const ok = RE_PHONE_HYPHEN.test(phone.value);
    phone.setCustomValidity(ok ? "" : "Invalid");
    validateField(phone);
    validateForm();
  };

  phone.addEventListener("input", () => {
    phone.value = formatPhMobileHyphenated(phone.value);
    phone.selectionStart = phone.selectionEnd = phone.value.length;
    validateContact();
  });

  phone.addEventListener("blur", () => {
    phone.value = formatPhMobileHyphenated(phone.value);
    validateContact();
  });

  phone.addEventListener("focus", () => {
    if (!phone.value.startsWith("+63")) phone.value = "+63 ";
    setTimeout(() => phone.setSelectionRange(phone.value.length, phone.value.length), 0);
  });
}
  student.addEventListener("input", () => { validateField(student); validateForm(); });
  student.addEventListener("blur",  () => { validateField(student); validateForm(); });
  if (ageEl) {
    ageEl.addEventListener("input", () => { validateField(ageEl); validateForm(); });
    ageEl.addEventListener("blur",  () => { validateField(ageEl); validateForm(); });
  }
  selectIds.forEach(id => {
    const el = document.getElementById(id);
    if (el) el.addEventListener("change", () => { validateField(el); validateForm(); });
  });

  document.addEventListener("DOMContentLoaded", () => {
    const yEl = document.getElementById("last_year_in_tupc");
    if (yEl) yEl.setAttribute("max", String(new Date().getFullYear()));
    if (phone && (phone.value === "" || phone.value === "+63")) phone.value = "+63 ";
    refreshExtension();
    validateForm();
  });

  // If user clicks open while invalid
  document.getElementById('openConfirmModal').addEventListener('click', () => {
    if (openBtn.disabled) {
      formAlert.classList.remove('d-none');
      validateForm();
      const firstInvalid = form.querySelector('.is-invalid');
      if (firstInvalid) firstInvalid.scrollIntoView({behavior:'smooth', block:'center'});
    }
  });

  // ===== Submit flow (countdown starts ONLY on real success) =====
  const redirectModal = new bootstrap.Modal(document.getElementById('redirectModal'));
  const confirmModal  = new bootstrap.Modal(document.getElementById('confirmSubmitModal'));
  const countSpan     = document.getElementById('countModal');
  const errorBox      = document.getElementById('submitError');
  let   countdownTimer = null;

  function startCountdown(seconds, redirectUrl) {
    let n = seconds;
    countSpan.textContent = n;
    if (countdownTimer) clearInterval(countdownTimer);
    countdownTimer = setInterval(() => {
      n -= 1; countSpan.textContent = n;
      if (n <= 0) { clearInterval(countdownTimer); window.location.href = redirectUrl; }
    }, 1000);
  }
  function getCsrfToken() {
    const inp = form.querySelector('input[name=csrfmiddlewaretoken]');
    return inp ? inp.value : '';
  }
  function applyServerErrors(errors) {
    // errors: { field_name: ["msg",...], "__all__": [...] }
    let any = false;
    for (const [name, msgs] of Object.entries(errors || {})) {
      const el = form.querySelector(`[name="${name}"]`);
      if (el) {
        el.classList.add('is-invalid');
        any = true;
      }
    }
    if (any) {
      formAlert.classList.remove('d-none');
      const firstInvalid = form.querySelector('.is-invalid');
      if (firstInvalid) firstInvalid.scrollIntoView({behavior:'smooth', block:'center'});
    }
  }
  function reenableForm() {
    Array.from(form.elements).forEach(el => el.disabled = false);
    confirmBtn.disabled = false;
    openBtn.disabled = false;
  }

  confirmBtn.addEventListener("click", async function () {
    if (!validateForm()) {
      formAlert.classList.remove('d-none');
      const firstInvalid = form.querySelector('.is-invalid');
      if (firstInvalid) firstInvalid.scrollIntoView({behavior:'smooth', block:'center'});
      return;
    }

    confirmModal.hide();
    redirectModal.show();
    const fd = new FormData(form);
    if (program && program.value === '__OTHER__' && programOtherInput) {
      fd.set('program', programOtherInput.value.replace(/\s+$/, ''));
    }
    Array.from(form.elements).forEach(el => el.disabled = true);
    confirmBtn.disabled = true;
    openBtn.disabled = true;
    errorBox.classList.add('d-none');

    try {
      const resp = await fetch(form.action, {
        method: "POST",
        headers: {
          "X-CSRFToken": getCsrfToken(),
          "X-Requested-With": "XMLHttpRequest"
        },
        body: fd,
        credentials: "same-origin",
      });

      const isJson = resp.headers.get("content-type") && resp.headers.get("content-type").includes("application/json");
      let data = null;
      if (isJson) {
        data = await resp.json();
      }

      if (resp.ok && (!isJson || (data && data.ok))) {
        startCountdown(5, "{% url 'client_home' %}");
        return; // keep modal open until countdown ends
      }
      if (isJson && data && data.errors) {
        applyServerErrors(data.errors);
      }
      if (countdownTimer) clearInterval(countdownTimer);
      errorBox.classList.remove('d-none');
      reenableForm();

    } catch (e) {
      if (countdownTimer) clearInterval(countdownTimer);
      errorBox.textContent = "Network error. Please check your connection and try again.";
      errorBox.classList.remove('d-none');
      reenableForm();
    }
  });

