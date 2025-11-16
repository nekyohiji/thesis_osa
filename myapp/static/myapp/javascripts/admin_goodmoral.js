


    // Prevent typing 0, negatives, and decimals
    document.addEventListener("DOMContentLoaded", () => {
      const inputs = document.querySelectorAll(
        "#gmf-batch-from, #gmf-batch-to, #forms-batch-from, #forms-batch-to"
      );

      inputs.forEach(input => {
        // Handle typing
        input.addEventListener("input", () => {
          // Remove decimals and non-numeric characters
          input.value = input.value.replace(/[^0-9]/g, '');

          // Prevent 0 or negative
          if (input.value !== "" && parseInt(input.value) < 1) {
            input.value = 1;
          }
        });

        // Handle pasting
        input.addEventListener("paste", (e) => {
          let pasteData = e.clipboardData.getData("text");
          // Reject if contains non-digits or less than 1
          if (!/^\d+$/.test(pasteData) || parseInt(pasteData) < 1) {
            e.preventDefault();
            input.value = 1;
          }
        });
      });
    });

    document.addEventListener('DOMContentLoaded', () => {
      const btn  = document.getElementById('gmf-batch-print-btn');
      const inpF = document.getElementById('gmf-batch-from');
      const inpT = document.getElementById('gmf-batch-to');
      if (!btn || !inpF || !inpT) return;

      btn.addEventListener('click', () => {
        const frm = parseInt(inpF.value || '1', 10);
        const to  = parseInt(inpT.value || String(frm), 10);
        if (Number.isNaN(frm) || Number.isNaN(to) || to < frm) {
          alert('Please enter a valid range.');
          return;
        }
        window.open(`/gmf/batch-preview?frm=${encodeURIComponent(frm)}&to=${encodeURIComponent(to)}`, '_blank');
      });
    });



  /* ===== Sidebar & Menus ===== */
  function toggleSidebar() {
    document.getElementById('sidebar')?.classList.toggle('show');
  }

  function handleDropdown(id) {
    const icon   = document.getElementById('icon-' + id);
    const target = document.getElementById(id);
    const bsTarget = bootstrap.Collapse.getOrCreateInstance(target);

    if (target.classList.contains('show')) {
      bsTarget.hide();
      icon?.classList.remove('rotate');
    } else {
      bsTarget.show();
      icon?.classList.add('rotate');
    }

    const allMenus = ['violationMenu', 'documentsMenu', 'postingsMenu', 'studentRecordMenu'];
    allMenus.forEach(menu => {
      if (menu !== id) {
        const el = document.getElementById(menu);
        const ic = document.getElementById('icon-' + menu);
        const bs = el ? bootstrap.Collapse.getInstance(el) : null;
        bs && bs.hide();
        ic && ic.classList.remove('rotate');
      }
    });
  }

  /* Highlight current nav link */
  document.addEventListener("DOMContentLoaded", function () {
    const currentUrl = window.location.href;
    document.querySelectorAll(".nav-link").forEach(link => {
      if (link.href && currentUrl.includes(link.href)) link.classList.add("active");
    });
  });

  /* ===== Table Searching (by multiple columns) =====
    colIndices is 1-based (e.g., [1,2] to include No. and Name) */
  function setupSearchByColumns(inputId, tableSelector, colIndices) {
    const input = document.getElementById(inputId);
    const table = document.querySelector(tableSelector);
    if (!input || !table) return;

    input.addEventListener('input', function () {
      const q = this.value.trim().toLowerCase();
      table.querySelectorAll('tbody tr').forEach(row => {
        const tds = row.querySelectorAll('td');
        if (!tds.length) return;

        // Skip empty-state rows (single <td colspan="...">)
        if (tds.length === 1 && tds[0].hasAttribute('colspan')) {
          row.style.display = q ? 'none' : '';
          return;
        }

        let haystack = '';
        colIndices.forEach(i => {
          const cell = row.querySelector(`td:nth-child(${i})`);
          if (cell) haystack += ' ' + (cell.innerText || cell.textContent || '').toLowerCase();
        });

        row.style.display = haystack.includes(q) ? '' : 'none';
      });
    });
  }

  /* Hook up searches:
    After adding the "No." column, Name is column 2; we want No. + Name → [1,2] */
  document.addEventListener('DOMContentLoaded', () => {
    setupSearchByColumns('goodmoral_search',        '.pending-table', [1,2]);
    setupSearchByColumns('goodmoral_record_search', '.history-table', [1,2]);
  });
    document.addEventListener('DOMContentLoaded', () => {
    const btn      = document.getElementById('forms-batch-print-btn');
    const inpFrom  = document.getElementById('forms-batch-from');
    const inpTo    = document.getElementById('forms-batch-to');
    const selStat  = document.getElementById('forms-batch-status');
    const chkGuide = document.getElementById('forms-batch-guide');

    if (!btn || !inpFrom || !inpTo) return;

    btn.addEventListener('click', () => {
      const frm = parseInt(inpFrom.value || '1', 10);
      const to  = parseInt(inpTo.value   || String(frm), 10);
      if (Number.isNaN(frm) || Number.isNaN(to) || to < frm) {
        alert('Please enter a valid range.');
        return;
      }

      const base   = btn.dataset.url || '/gmrf/batch-preview';
      const status = (selStat?.value || 'all').toLowerCase();
      const guide  = chkGuide?.checked ? '&guide=1' : '';

      const qs = `?frm=${encodeURIComponent(frm)}&to=${encodeURIComponent(to)}&status=${encodeURIComponent(status)}${guide}`;
      window.open(base + qs, '_blank');
    });
  });
    // Mark interaction to pause polling & swaps
  (function () {
    const tbl = document.getElementById('gm_pending_table');
    if (!tbl) return;

    const add = () => tbl.classList.add('interacting');
    const removeSoon = () => setTimeout(() => tbl.classList.remove('interacting'), 800);

    ['mousedown','touchstart','focusin','mouseenter'].forEach(ev => {
      tbl.addEventListener(ev, add, { passive: true });
    });
    ['mouseup','touchend','mouseleave','focusout','click'].forEach(ev => {
      tbl.addEventListener(ev, removeSoon, { passive: true });
    });
  })();

  // Safe navigation for "View More"
  (function () {
    document.addEventListener('click', function (e) {
      const a = e.target.closest('a[data-safe-nav]');
      if (!a) return;
      window.__navClicking = true;
      setTimeout(() => { window.__navClicking = false; }, 1500);
      e.preventDefault();
      window.location.href = a.href;
    }, { capture: true });
  })();
  
///////////////////////////////////////////////////////////////////////////////
  window.addEventListener('pageshow', function (e) {
    if (e.persisted) location.reload();
  });


//////////////////////////////////////////////////////////////////////////////////////
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
