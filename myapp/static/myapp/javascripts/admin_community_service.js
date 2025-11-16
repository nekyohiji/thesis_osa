
/* Community Service — hard-trim to first TUPC + freeze to block trailing scanner chars */
(() => {
  const modal = document.getElementById('csCreateAdjustModal')
             || document.getElementById('createCommunityServiceModal');
  const form  = modal?.querySelector('form');
  if (!form) return;

  const sid = document.getElementById('cs_student_id');
  const fb  = document.getElementById('csLookupFeedback');

  const TUPC_FULL    = /^TUPC-\d{2}-\d{4,8}$/;
  const TUPC_CAPTURE = /(TUPC-\d{2}-\d{4,8})/i;

  let freezeUntil = 0;     // while frozen, ignore any inserted characters
  let lockedId    = '';    // the ID we keep during freeze

  const setFeedback = (kind, text) => {
    if (!fb) return;
    fb.className = 'small mt-1 ' + (kind==='ok' ? 'text-success' : kind==='warn' ? 'text-warning' : 'text-danger');
    fb.textContent = text || '';
  };

  const normalize = v => String(v||'')
    .toUpperCase()
    .replace(/[\r\n\t]/g, ' ')
    .replace(/[^A-Z0-9\- ]/g, '');

  const firstId = v => {
    const m = String(v||'').toUpperCase().match(TUPC_CAPTURE);
    return m ? m[1] : '';
  };

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

  async function doLookup() {
    const id = sid.value.toUpperCase().trim();
    if (!TUPC_FULL.test(id)) return;
    const url = getLookupPrefix() + encodeURIComponent(id) + '/';
    setFeedback('warn', 'Looking up student…');
    try {
      const res = await fetch(url, { headers: { 'Accept':'application/json' } });
      if (!res.ok) throw new Error('HTTP ' + res.status);
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
    } catch (e) {
      console.error('[CS TUPC lookup]', e);
      setFeedback('err', 'Lookup failed. See console.');
    }
  }

  // Freeze helpers
  function startFreeze(id) {
    lockedId = id;
    freezeUntil = Date.now() + 500; // 0.5s is enough to swallow the scanner tail
  }
  function isFrozen() { return Date.now() < freezeUntil; }

  // Block inserts while frozen (but allow deletions/navigation)
  sid.addEventListener('beforeinput', (e) => {
    if (!isFrozen()) return;
    const type = e.inputType || '';
    if (!type.startsWith('delete') && type !== 'historyUndo' && type !== 'historyRedo') {
      e.preventDefault();
    }
  });

  // Keep value locked during freeze
  const enforceLock = () => {
    if (isFrozen()) {
      sid.value = lockedId;
      // keep caret at end
      try { sid.setSelectionRange(lockedId.length, lockedId.length); } catch {}
    }
  };

  // Snap + lookup
  const snapAndLookup = () => {
    sid.value = normalize(sid.value);
    const id = firstId(sid.value);
    if (id) {
      sid.value = id;      // hard-trim to the ID
      startFreeze(id);     // block any tail (e.g., "RIBERAL 4351")
      doLookup();
      enforceLock();
    }
  };

  // Prevent Enter from submitting modal
  form.addEventListener('keydown', (e) => {
    if (e.key === 'Enter' && e.target.tagName !== 'TEXTAREA') e.preventDefault();
  });

  if (sid) {
    sid.addEventListener('input',  () => { snapAndLookup(); enforceLock(); });
    sid.addEventListener('blur',   () => { snapAndLookup(); enforceLock(); });
    sid.addEventListener('change', () => { snapAndLookup(); enforceLock(); });
    sid.addEventListener('keydown', (e) => {
      if (e.key === 'Enter') { e.preventDefault(); snapAndLookup(); enforceLock(); }
    });
    sid.addEventListener('paste',  () => setTimeout(() => { snapAndLookup(); enforceLock(); }, 0));
  }

  // Focus on open; reset on close
  modal?.addEventListener('shown.bs.modal', () => sid?.focus());
  modal?.addEventListener('hidden.bs.modal', () => {
    form.reset();
    form.querySelectorAll('input,select,textarea').forEach(el => el.style.borderColor = '');
    setFeedback('ok', '');
    lockedId = ''; freezeUntil = 0;
  });
})();




/////////////////////////////////////////////////////////////////////////

/* Sidebar Functions*/
        // Toggle Sidebar
      function toggleSidebar() {
        const sidebar = document.getElementById('sidebar');
        sidebar.classList.toggle('show');
      }

      // Handle Dropdowns Uniformly
      function handleDropdown(menuId) {
        const clickedIcon = document.getElementById(`icon-${menuId}`);
        const clickedMenu = document.getElementById(menuId);
        const clickedCollapse = bootstrap.Collapse.getOrCreateInstance(clickedMenu);

        // Toggle clicked menu
        if (clickedMenu.classList.contains('show')) {
          clickedCollapse.hide();
          clickedIcon.classList.remove('rotate');
        } else {
          clickedCollapse.show();
          clickedIcon.classList.add('rotate');
        }

        // Hide other open menus
        const allDropdowns = ['violationMenu', 'documentsMenu', 'postingsMenu', 'studentRecordMenu'];
        allDropdowns.forEach(id => {
          if (id !== menuId) {
            const menu = document.getElementById(id);
            const icon = document.getElementById(`icon-${id}`);
            const collapse = bootstrap.Collapse.getInstance(menu);
            if (collapse) collapse.hide();
            if (icon) icon.classList.remove('rotate');
          }
        });
      }

      // Highlight Active Link
      document.addEventListener('DOMContentLoaded', function () {
        const currentUrl = window.location.href;
        const navLinks = document.querySelectorAll('.nav-link');

        navLinks.forEach(link => {
          if (link.href && currentUrl.includes(link.href)) {
            link.classList.add('active');
          }
        });
      });
///////////////////////////// START HERE MAG ADD

  document.addEventListener('DOMContentLoaded', function () {
    const input = document.getElementById('communityservice_search');
    if (!input) return;

    // keep the input in sync with the current ?q
    const params = new URLSearchParams(window.location.search);
    input.value = params.get('q') || '';

    // submit on Enter
    input.addEventListener('keydown', function (e) {
      if (e.key === 'Enter') {
        e.preventDefault();
        const url = new URL(window.location.href);
        const q = input.value.trim();
        if (q) url.searchParams.set('q', q); else url.searchParams.delete('q');
        window.location.href = url.toString();
      }
    });

    // clicking the search icon also triggers search
    const icon = input.parentElement?.querySelector('.input-group-text');
    if (icon) {
      icon.style.cursor = 'pointer';
      icon.addEventListener('click', function () {
        const url = new URL(window.location.href);
        const q = input.value.trim();
        if (q) url.searchParams.set('q', q); else url.searchParams.delete('q');
        window.location.href = url.toString();
      });
    }
  });

///////////////////////////////////////////////////////////////////////
  window.addEventListener('pageshow', function (e) {
    if (e.persisted) location.reload();
  });


