
    /* Sidebar Functions */
    function toggleSidebar() {
      const sidebar = document.getElementById('sidebar');
      sidebar.classList.toggle('show');
    }

    function handleDropdown(menuId) {
      const clickedIcon = document.getElementById(`icon-${menuId}`);
      const clickedMenu = document.getElementById(menuId);
      const clickedCollapse = bootstrap.Collapse.getOrCreateInstance(clickedMenu);

      if (clickedMenu.classList.contains('show')) {
        clickedCollapse.hide();
        clickedIcon.classList.remove('rotate');
      } else {
        clickedCollapse.show();
        clickedIcon.classList.add('rotate');
      }

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

  console.log("DATA_URL =", DATA_URL);
  const elCardStudentAssist = document.getElementById('cardStudentAssist');
  const elCardAcso          = document.getElementById('cardAcso');
  const elLastUpdated  = document.getElementById('lastUpdated');
  const elCardGrand    = document.getElementById('cardGrand');
  const elCardGM       = document.getElementById('cardGoodMoral');
  const elCardClr      = document.getElementById('cardClearance');
  const elCardSurr     = document.getElementById('cardSurrender');
  const elMonthlyBody  = document.getElementById('monthlyBody');
  
  // NEW: rejected spans
  const elCardGrandRejected = document.getElementById('cardGrandRejected');
  const elCardGMRejected    = document.getElementById('cardGMRejected');
  const elCardSurrRejected  = document.getElementById('cardSurrRejected');

  // Small inline error
  const errorBadge = document.createElement('div');
  errorBadge.className = 'text-warning mt-2';
  errorBadge.style.fontSize = '0.85rem';
  errorBadge.style.display = 'none';
  errorBadge.id = 'loadError';
  elLastUpdated.parentNode.appendChild(errorBadge);

  function showError(msg) {
    const el = document.getElementById('loadError');
    el.textContent = msg;
    el.style.display = 'block';
  }
  function hideError() {
    const el = document.getElementById('loadError');
    el.textContent = '';
    el.style.display = 'none';
  }
  function fmt(n) { return (n || 0).toLocaleString(); }

  function renderTotals(totals, asOf) {
    elCardGrand.textContent = fmt(totals.grand_total);
    elCardGM.textContent    = fmt(totals.goodmoral_approved);
    elCardClr.textContent   = fmt(totals.clearance_all);
    elCardSurr.textContent  = fmt(totals.surrender_approved);

    // rejected
    if (elCardGrandRejected) elCardGrandRejected.textContent = fmt(totals.grand_rejected || 0);
    if (elCardGMRejected)    elCardGMRejected.textContent    = fmt(totals.goodmoral_rejected || 0);
    if (elCardSurrRejected)  elCardSurrRejected.textContent  = fmt(totals.surrender_rejected || 0);

    // NEW cards
    if (elCardStudentAssist) elCardStudentAssist.textContent = fmt(totals.studentassist_all || 0);
    if (elCardAcso)          elCardAcso.textContent          = fmt(totals.acso_all || 0);

    elLastUpdated.textContent = "Updated " + new Date(asOf).toLocaleString();
  }

  const PAGE_SIZE = 5;
  let allRows = [];       // full dataset from backend (already newest-first)
  let filteredRows = [];  // after search filter
  let currentPage = 1;

  function renderMonthlyPage(rows) {
    elMonthlyBody.innerHTML = "";
    if (!rows || rows.length === 0) {
      elMonthlyBody.innerHTML =
        '<tr id="monthlyEmpty"><td colspan="7" class="text-muted">No data yet.</td></tr>';
      return;
    }
    rows.forEach(r => {
      elMonthlyBody.insertAdjacentHTML('beforeend', `
        <tr>
          <td>${r.month_label}</td>
          <td class="fw-semibold">${fmt(r.total)}</td>
          <td>${fmt(r.goodmoral_approved)}</td>
          <td>${fmt(r.clearance_all)}</td>
          <td>${fmt(r.surrender_approved)}</td>
          <td>${fmt(r.studentassist_all || 0)}</td>
          <td>${fmt(r.acso_all || 0)}</td>
        </tr>
      `);
    });
  }

  function renderPage() {
    const total = filteredRows.length;
    const totalPages = Math.max(1, Math.ceil(total / PAGE_SIZE));
    if (currentPage > totalPages) currentPage = totalPages;
    const start = (currentPage - 1) * PAGE_SIZE;
    const pageRows = filteredRows.slice(start, start + PAGE_SIZE);

    renderMonthlyPage(pageRows);

    // Pager UI
    const pageInfo = document.getElementById('pageInfo');
    const btnPrev  = document.getElementById('btnPrev');
    const btnNext  = document.getElementById('btnNext');

    if (pageInfo) pageInfo.textContent = `Page ${total ? currentPage : 0} / ${total ? totalPages : 0}`;
    if (btnPrev)  btnPrev.disabled = (currentPage <= 1) || total === 0;
    if (btnNext)  btnNext.disabled = (currentPage >= totalPages) || total === 0;
  }

  async function loadDashboard() {
    hideError();
    try {
      const res = await fetch(DATA_URL, {
        cache: 'no-store',
        credentials: 'same-origin',
        headers: { 'X-Requested-With': 'XMLHttpRequest' }
      });

      const ct = res.headers.get('content-type') || '';
      if (!res.ok) {
        const text = await res.text();
        console.error('admin_dashboard_data failed:', res.status, text);
        showError(`Failed to load data (${res.status}). See console.`);
        return;
      }
      if (!ct.includes('application/json')) {
        const text = await res.text();
        console.error('Expected JSON, got:', ct, text.slice(0, 400));
        showError('Data endpoint returned non-JSON (likely a redirect). Check auth/URL.');
        return;
      }

      const data = await res.json();
      renderTotals(data.totals, data.as_of);
      // pagination init
      allRows = data.rows || [];     // newest-first from backend
      filteredRows = [...allRows];   // start with everything
      currentPage = 1;               // show newest page
      renderPage();
    } catch (e) {
      console.error("Dashboard load exception:", e);
      showError('Error loading dashboard data. See console for details.');
    }
  }

  loadDashboard();
  setInterval(loadDashboard, 60_000);




  // Search Function
 const searchInput  = document.querySelector('.search-input');
  const tableBody    = document.getElementById('monthlyBody');
  const btnPrev      = document.getElementById('btnPrev');
  const btnNext      = document.getElementById('btnNext');

  function applyFilter() {
    const q = (searchInput?.value || '').toLowerCase().trim();
    if (!q) {
      filteredRows = [...allRows];
    } else {
      filteredRows = allRows.filter(r => (r.month_label || '').toLowerCase().includes(q));
    }
    currentPage = 1;
    renderPage();
  }

  // Search on typing + button click
  searchInput.addEventListener('keyup', applyFilter);
  // If you keep a clickable button, point it here too:
  const searchButton = document.querySelector('.btn.border'); // your search button next to the input
  if (searchButton) searchButton.addEventListener('click', applyFilter);

  // Pager clicks
  btnPrev.addEventListener('click', () => {
    if (currentPage > 1) {
      currentPage--;
      renderPage();
    }
  });
  btnNext.addEventListener('click', () => {
    currentPage++;
    renderPage();
  });


///////////////////////////////////////////////////// ###

  window.addEventListener('pageshow', function (e) {
    if (e.persisted) location.reload();
  });

///////////////////////////////////////////////////// ###