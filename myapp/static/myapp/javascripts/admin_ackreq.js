


    // Prevent typing 0, negatives, decimals, or non-numeric
    document.addEventListener("DOMContentLoaded", () => {
      const inputs = document.querySelectorAll("#ack-batch-from, #ack-batch-to");

      inputs.forEach(input => {
        // Handle typing
        input.addEventListener("input", () => {
          // Remove decimals and non-numeric characters
          input.value = input.value.replace(/[^0-9]/g, '');

          // Prevent 0 or negatives
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

        // Ensure empty fields reset to 1 on blur
        input.addEventListener("blur", () => {
          if (input.value === "" || parseInt(input.value) < 1) {
            input.value = 1;
          }
        });
      });
    });



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

  // Live filter by name, student number, or date (case-insensitive)
  function attachLiveFilter(inputId, tableId) {
    const input = document.getElementById(inputId);
    const table = document.getElementById(tableId);
    if (!input || !table) return;

    const rows = table.querySelectorAll('tbody tr');
    const norm = s => (s || '').toString().toLowerCase().trim();

    input.addEventListener('input', () => {
      const q = norm(input.value);
      rows.forEach(row => {
        // read only the allowed fields
        const name = norm(row.querySelector('.td-name')?.textContent);
        const student = norm(row.querySelector('.td-student')?.textContent);
        const date = norm(row.querySelector('.td-date')?.textContent);

        const match = !q || name.includes(q) || student.includes(q) || date.includes(q);
        row.style.display = match ? '' : 'none';
      });
    });
  }

  attachLiveFilter('historySearch', 'historyTable');
    (function () {
    const btn = document.getElementById("ack-batch-print-btn");
    if (!btn) return;

    btn.addEventListener("click", () => {
      const fromEl = document.getElementById("ack-batch-from");
      const toEl   = document.getElementById("ack-batch-to");

      const frm = parseInt(fromEl?.value, 10);
      const to  = parseInt(toEl?.value, 10);

      // basic client-side validation
      if (!Number.isInteger(frm) || frm < 1) {
        alert("Please enter a valid 'From' number (≥ 1).");
        fromEl?.focus();
        return;
      }
      if (!Number.isInteger(to) || to < frm) {
        alert("Please enter a valid 'To' number (≥ From).");
        toEl?.focus();
        return;
      }

      // open server-rendered merged PDF (inline)
      const url = `{% url 'ackreq_batch_preview' %}?frm=${encodeURIComponent(frm)}&to=${encodeURIComponent(to)}`;
      window.open(url, "_blank"); // use location.href = url; to stay in the same tab
    });
  })();
    (function () {
    const tbl = document.getElementById('pendingTable');
    if (!tbl) return;

    const add = () => tbl.classList.add('interacting');
    const removeSoon = () => setTimeout(() => tbl.classList.remove('interacting'), 300);

    ['mousedown','touchstart','focusin','mouseenter'].forEach(ev => {
      tbl.addEventListener(ev, add, { passive: true });
    });
    ['mouseup','touchend','mouseleave','focusout'].forEach(ev => {
      tbl.addEventListener(ev, removeSoon, { passive: true });
    });
  })();
  
////////////////////////////////////////////////////////////////////////////////////////
  // Make View More clicks immune to in-flight HTMX swaps/polls
  (function () {
    document.addEventListener('click', function (e) {
      const a = e.target.closest('a[data-safe-nav]');
      if (!a) return;

      // Tell HTMX to skip any swap that lands during this click
      window.__navClicking = true;
      setTimeout(() => { window.__navClicking = false; }, 1500);

      // Immediately navigate (bypasses any race with async swaps)
      e.preventDefault();
      window.location.href = a.href;
    }, { capture: true });
  })();


  ///////////////////////////////////////////////////////////////////
  window.addEventListener('pageshow', function (e) {
    if (e.persisted) location.reload();
  });
///////////////////////////////////////////////////////////////////////
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
