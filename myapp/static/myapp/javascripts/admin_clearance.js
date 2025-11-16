

/* Sidebar Functions*/
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

////////////////////////////////////////////////////////////////
(function () {
  const input = document.getElementById('clearance_search');
  const form  = input ? input.closest('form') : null;
  const table = document.querySelector('.clearance-table');
  const tbody = table ? table.querySelector('tbody') : null;
  if (!input || !tbody) return;

  // Don’t submit/refresh the page
  if (form) form.addEventListener('submit', (e) => e.preventDefault());

  function filterRows() {
    const q = input.value.trim().toLowerCase();
    const rows = Array.from(tbody.querySelectorAll('tr'));
    rows.forEach(tr => {
      const cells = tr.children;
      // columns: 0 = Student ID, 1 = Name
      const student = (cells[0]?.textContent || '').toLowerCase();
      const name    = (cells[1]?.textContent || '').toLowerCase();
      const match   = !q || student.includes(q) || name.includes(q);
      tr.style.display = match ? '' : 'none';
    });
  }

  // Live as you type; clearing the box shows all again
  input.addEventListener('input', filterRows);
  document.addEventListener('DOMContentLoaded', filterRows);
})();

//////////////////////////////////////////////////////////////////////////////////////
  window.addEventListener('pageshow', function (e) {
    if (e.persisted) location.reload();
  });
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
