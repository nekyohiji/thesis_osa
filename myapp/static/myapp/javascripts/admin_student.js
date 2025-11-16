
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
///////////////////////////// START HERE MAG ADD

 
    window.addEventListener('pageshow', function (e) {
      if (e.persisted) location.reload();
    });
