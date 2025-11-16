

/* ================== CONSTANTS ================== */
const PROGRAM_MAX = 18;
const RE_PHONE_HYPHEN = /^\+63\s\d{3}-\d{3}-\d{4}$/;
const RE_TUPC_ID = /^TUPC-\d{2}-[A-Za-z0-9]{4,15}$/; // TUPC-YY-<4–15 alnum>
const RE_NAME = /^(?! )(?!.* {2,})(?!.* $)[A-Za-zÑñ.'-]+(?: [A-Za-zÑñ.'-]+)*$/;
const RE_ALLOWED_EMAIL = /^[^\s@]+@(?:gmail\.com|gsfe\.tupcavite\.edu\.ph|tup\.edu\.ph)$/i;

/* ================== HELPERS ================== */
function digitsOnly(s){ return (s||"").replace(/\D+/g,""); }
function formatPhMobileHyphenated(raw){
  const d = digitsOnly(raw); const rest = d.startsWith("63") ? d.slice(2) : d;
  const ten = rest.slice(0,10); if (!ten) return "+63 ";
  const a = ten.slice(0,3), b = ten.slice(3,6), c = ten.slice(6,10);
  return `+63 ${a}${b?'-'+b:''}${c?'-'+c:''}`;
}
function setClasses(el, valid){ el.classList.toggle('is-valid',valid); el.classList.toggle('is-invalid',!valid); }
function setStatusIcon(el, valid){
  const icon = document.getElementById(el.id + '_status'); if (!icon) return;
  icon.classList.remove('d-none','bi-check-circle-fill','bi-x-circle-fill','text-success','text-danger');
  icon.classList.add(valid ? 'bi-check-circle-fill' : 'bi-x-circle-fill', valid ? 'text-success' : 'text-danger');
}
function mark(el, ok){ setClasses(el, ok); setStatusIcon(el, ok); return ok; }

/* ================== ELEMENTS ================== */
const form       = document.getElementById('acsoform');
const openBtn    = document.getElementById('openConfirmModal');
const confirmBtn = document.getElementById('confirmSubmitBtn');
const formAlert  = document.getElementById('formAlert');

const fullName = document.getElementById('full_name') || document.getElementById('first_name');
const ageEl    = document.getElementById('age');
const sexEl    = document.getElementById('sex');
const idEl     = document.getElementById('id');
const program  = document.getElementById('program');
const phone    = document.getElementById('contact');
const address  = document.getElementById('address');
const emailEl  = document.getElementById('contact_email');
const acsoEl = document.getElementById('acso');
const clientTypeSel = document.getElementById('client_type');

/* Stakeholder + Year Level */
const stTupc   = document.getElementById('st_tupc');
const yrSel    = document.getElementById('year_level');
const stRadios = [...document.querySelectorAll('input[name="stakeholder"]')];

/* ================== FIELD VALIDATORS ================== */
function validateEmail(){
  if (!emailEl) return true;
  const v = (emailEl.value || "").trim();
  const ok = RE_ALLOWED_EMAIL.test(v);
  emailEl.setCustomValidity(ok ? "" : "Email must end with @gmail.com, @gsfe.tupcavite.edu.ph, or @tup.edu.ph.");
  emailEl.classList.toggle('is-valid', ok);
  emailEl.classList.toggle('is-invalid', !ok);
  return ok;
}

function validateFullName(){
  if (!fullName) return true;
  let v = fullName.value;
  if (v.endsWith(' ')) {
    fullName.setCustomValidity('No trailing space allowed.');
    return mark(fullName, false);
  }
  v = v.trim();
  fullName.value = v;
  const ok = v.length >= 2 && v.length <= 100 && RE_NAME.test(v);
  fullName.setCustomValidity(ok ? '' :
    "Letters, period (.), apostrophe ('), hyphen (-); single spaces between words; no trailing space."
  );
  return mark(fullName, ok);
}

function validateAge(){
  if (!ageEl) return true;
  const n = Number((ageEl.value||'').trim());
  const ok = Number.isInteger(n) && n >= 16 && n <= 121;
  ageEl.setCustomValidity(ok ? '' : 'Age must be 16–121.');
  return mark(ageEl, ok);
}

function validateSex(){
  if (!sexEl) return true;
  const ok = !!sexEl.value;
  sexEl.setCustomValidity(ok ? '' : 'Please select sex.');
  return mark(sexEl, ok);
}

function validatePhone(){
  if (!phone) return true;
  const ok = RE_PHONE_HYPHEN.test(phone.value);
  phone.setCustomValidity(ok ? '' : 'Use +63 XXX-XXX-XXXX.');
  return mark(phone, ok);
}

function validateAddress(){
  if (!address) return true;
  const v = address.value.trim();
  const ok = v.length >= 5 && v.length <= 255;
  address.setCustomValidity(ok ? '' : 'Address must be 5–255 characters.');
  return mark(address, ok);
}

function validateID(){
  if (!idEl) return true;
  idEl.value = idEl.value.toUpperCase().replace(/\s+/g,'');
  const ok = RE_TUPC_ID.test(idEl.value);
  idEl.setCustomValidity(ok ? '' : 'Format: TUPC-XX-<4–15 letters/numbers>.');
  return mark(idEl, ok);
}

function validateProgram(){
  if (!program) return true;
  const v = program.value.trim();
  const ok = v.length >= 1 && v.length <= PROGRAM_MAX;
  program.setCustomValidity(ok ? '' : `Program must be 1–${PROGRAM_MAX} characters.`);
  return mark(program, ok);
}

/* Stakeholder group + year level */
function toggleYearLevel(){
  if (!stTupc || !yrSel) return;
  const show = stTupc.checked;
  yrSel.classList.toggle('d-none', !show);
  yrSel.required = show;
  if (!show){
    yrSel.value = '';
    yrSel.classList.remove('is-valid','is-invalid');
    yrSel.setCustomValidity('');
  }
}
function validateStakeholderGroup(){
  if (!stRadios.length) return true;
  const anyChecked = stRadios.some(r => r.checked);
  stRadios.forEach(r => r.setCustomValidity(''));
  if (!anyChecked){
    (document.activeElement && stRadios.includes(document.activeElement) ? document.activeElement : stRadios[0])
      .setCustomValidity('Please choose one.');
  }
  return anyChecked;
}
function validateYearLevel(){
  if (!yrSel || !stTupc) return true;
  if (!stTupc.checked) return true; // not applicable
  const ok = !!yrSel.value;
  yrSel.setCustomValidity(ok ? '' : 'Please select your year level.');
  yrSel.classList.toggle('is-valid', ok);
  yrSel.classList.toggle('is-invalid', !ok);
  return ok;
}

function validateClientType(){
  if (!clientTypeSel) return true;
  const ok = !!clientTypeSel.value;
  clientTypeSel.setCustomValidity(ok ? '' : 'Please select a client type.');
  clientTypeSel.classList.toggle('is-valid', ok);
  clientTypeSel.classList.toggle('is-invalid', !ok);
  return ok;
}

function validateAcso(){
  if (!acsoEl) return true;
  const v = (acsoEl.value || '').trim();
  const ok = v.length >= 1 && v.length <= 100;
  acsoEl.setCustomValidity(ok ? '' : 'Please enter the ACSO (max 100 characters).');
  acsoEl.value = v;
  return mark(acsoEl, ok);
}
/* ================== FORM VALIDATOR ================== */
function validateForm(){
  let ok = true;
  ok = validateEmail()              && ok;
  ok = validateFullName()           && ok;
  ok = validateAge()                && ok;
  ok = validateSex()                && ok;
  ok = validatePhone()              && ok;
  ok = validateAddress()            && ok;
  ok = validateID()                 && ok;
  ok = validateProgram()            && ok;
  ok = validateClientType()         && ok;
  ok = validateStakeholderGroup()   && ok;
  ok = validateYearLevel()          && ok;
  ok = validateAcso()               && ok;

  ok = form.checkValidity() && ok;
  openBtn.disabled = !ok;
  if (ok) formAlert.classList.add('d-none');
  return ok;
}

/* ================== LISTENERS ================== */
if (phone){
  if (!phone.value.trim() || phone.value.trim() === '+63') phone.value = '+63 ';
  const syncPhone = () => { phone.value = formatPhMobileHyphenated(phone.value); validatePhone(); validateForm(); };
  phone.addEventListener('input', syncPhone);
  phone.addEventListener('blur',  syncPhone);
  phone.addEventListener('focus', () => {
    if (!phone.value.startsWith('+63')) phone.value = '+63 ';
    setTimeout(() => phone.setSelectionRange(phone.value.length, phone.value.length), 0);
  });
}
if (fullName){ fullName.addEventListener('input', () => { validateFullName(); validateForm(); }); }
if (ageEl){    ageEl.addEventListener('input', () => { validateAge(); validateForm(); }); }
if (sexEl){    sexEl.addEventListener('change', () => { validateSex(); validateForm(); }); }
if (address){  address.addEventListener('input', () => { validateAddress(); validateForm(); }); }
if (idEl){
  idEl.addEventListener('input', () => { validateID(); validateForm(); });
  idEl.addEventListener('blur',  () => { validateID(); validateForm(); });
}
if (program){
  program.setAttribute('maxlength', String(PROGRAM_MAX));
  program.addEventListener('input', () => { validateProgram(); validateForm(); });
  program.addEventListener('blur',  () => { validateProgram(); validateForm(); });
}
stRadios.forEach(r => r.addEventListener('change', () => {
  toggleYearLevel(); validateStakeholderGroup(); validateYearLevel(); validateForm();
}));
if (yrSel){ yrSel.addEventListener('change', () => { validateYearLevel(); validateForm(); }); }
if (clientTypeSel){
  clientTypeSel.addEventListener('change', () => { validateClientType(); validateForm(); });
}
if (acsoEl){
  acsoEl.addEventListener('input', () => { validateAcso(); validateForm(); });
  acsoEl.addEventListener('blur',  () => { validateAcso(); validateForm(); });
}
/* ================== OPEN BUTTON GUARD ================== */
document.getElementById('openConfirmModal').addEventListener('click', () => {
  if (openBtn.disabled){
    formAlert.classList.remove('d-none');
    validateForm();
    const firstInvalid = form.querySelector('.is-invalid');
    if (firstInvalid) firstInvalid.scrollIntoView({behavior:'smooth', block:'center'});
  }
});

/* ================== SUBMIT FLOW ================== */
const redirectModal = new bootstrap.Modal(document.getElementById('redirectModal'));
const confirmModal  = new bootstrap.Modal(document.getElementById('confirmSubmitModal'));
const countSpan     = document.getElementById('countModal');
const errorBox      = document.getElementById('submitError');
let countdownTimer  = null;

function startCountdown(seconds, redirectUrl){
  let n = seconds; countSpan.textContent = n;
  clearInterval(countdownTimer);
  countdownTimer = setInterval(() => {
    n -= 1; countSpan.textContent = n;
    if (n <= 0){ clearInterval(countdownTimer); window.location.href = redirectUrl; }
  }, 1000);
}
function getCsrfToken(){
  const inp = form.querySelector('input[name=csrfmiddlewaretoken]');
  return inp ? inp.value : '';
}

confirmBtn.addEventListener('click', async function(){
  if (!validateForm()){
    formAlert.classList.remove('d-none');
    const firstInvalid = form.querySelector('.is-invalid');
    if (firstInvalid) firstInvalid.scrollIntoView({behavior:'smooth', block:'center'});
    return;
  }

  confirmModal.hide();
  redirectModal.show();

  const fd = new FormData(form);
  Array.from(form.elements).forEach(el => el.disabled = true);
  confirmBtn.disabled = true; openBtn.disabled = true; errorBox.classList.add('d-none');

  try{
    const resp = await fetch(form.action, {
      method: 'POST',
      headers: { 'X-CSRFToken': getCsrfToken(), 'X-Requested-With': 'XMLHttpRequest' },
      body: fd, credentials: 'same-origin'
    });
    const isJson = (resp.headers.get('content-type')||'').includes('application/json');
    const data = isJson ? await resp.json() : null;

    if (resp.ok && (!isJson || (data && data.ok))){
      startCountdown(5, "{% url 'client_home' %}");
      return;
    }
    if (data && data.errors){
      Object.keys(data.errors).forEach(name => {
        const el = form.querySelector(`[name="${name}"]`);
        if (el){ el.classList.add('is-invalid'); }
      });
    }
    clearInterval(countdownTimer);
    errorBox.classList.remove('d-none');
  } catch(e){
    clearInterval(countdownTimer);
    errorBox.textContent = 'Network error. Please try again.';
    errorBox.classList.remove('d-none');
  } finally {
    Array.from(form.elements).forEach(el => el.disabled = false);
    confirmBtn.disabled = false; openBtn.disabled = false;
  }
});

/* ================== INIT ================== */
document.addEventListener('DOMContentLoaded', () => {
  if (phone && (phone.value === '' || phone.value === '+63')) phone.value = '+63 ';
  toggleYearLevel();          // ✅ existing function
  validateForm();             // run once to set initial button state
});
