

  window.addEventListener('pageshow', function (e) {
    if (e.persisted) location.reload();
  });


///////////////////////////////////////////////////////////////////////////////////

(function () {
  // where to send users if the session is gone
  var loginUrl = "{% url 'login' %}";
  function goLogin() {
    var next = encodeURIComponent(location.pathname + location.search + location.hash);
    location.replace(loginUrl + "?next=" + next);
  }

  // --- 1) HTMX: if any background request gets 401, bounce to login
  document.body.addEventListener('htmx:responseError', function (e) {
    var xhr = e.detail && e.detail.xhr;
    if (!xhr) return;

    // 401 = unauthenticated; (optionally also 440 if you ever use it)
    if (xhr.status === 401 || xhr.status === 440) {
      goLogin();
    }
  });

  // Optional: pause HTMX polling while tab hidden (saves requests, doesn’t affect auth)
  if (window.htmx) {
    document.addEventListener('visibilitychange', function () {
      if (document.hidden) {
        // disable all polling elements
        document.querySelectorAll('[hx-trigger*="every"]').forEach(function (el) {
          el.setAttribute('data-poll-disabled', '1');
          el.setAttribute('hx-trigger', el.getAttribute('hx-trigger') + ' consume');
        });
      } else {
        // re-enable by forcing a refresh of attributes
        document.querySelectorAll('[data-poll-disabled="1"]').forEach(function (el) {
          el.removeAttribute('data-poll-disabled');
          var trig = el.getAttribute('hx-trigger') || '';
          el.setAttribute('hx-trigger', trig.replace(/\s*consume\b/, ''));
          // optional: kick one refresh
          if (el.matches('[hx-get], [hx-post], [hx-patch], [hx-put]')) {
            htmx.trigger(el, 'refresh');
          }
        });
      }
    });
  }

  // --- 2) fetch(): wrap to catch 401s from non-HTMX AJAX
  if (!window.__fetchWrapped) {
    var _fetch = window.fetch;
    window.fetch = function () {
      return _fetch.apply(this, arguments).then(function (res) {
        if (res && (res.status === 401 || res.status === 440)) {
          goLogin();
          // return a never-resolving promise to stop downstream handlers
          return new Promise(function () {});
        }
        return res;
      }).catch(function (err) {
        // network errors stay as-is
        throw err;
      });
    };
    window.__fetchWrapped = true;
  }

  // --- 3) (Optional nicety) if the page was restored from bfcache, hard-reload
  // so we don’t show a stale “logged-in” view after logout in another tab.
  window.addEventListener('pageshow', function (e) {
    if (e.persisted) location.reload();
  });

})();

