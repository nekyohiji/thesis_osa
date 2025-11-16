
    // Toggle Sidebar
    function toggleSidebar() {
        const sidebar = document.getElementById('sidebar');
        sidebar.classList.toggle('show');
    }

    // Handle Dropdown Toggles in Sidebar
    function handleDropdown(menuId) {
        const clickedIcon = document.getElementById(`icon-${menuId}`);
        const clickedMenu = document.getElementById(menuId);
        const clickedCollapse = bootstrap.Collapse.getOrCreateInstance(clickedMenu);
        const isOpen = clickedMenu.classList.contains('show');

        const allDropdowns = ['violationMenu', 'documentsMenu', 'postingsMenu', 'studentRecordMenu'];
        allDropdowns.forEach(id => {
            if (id !== menuId) {
                const menu = document.getElementById(id);
                const icon = document.getElementById(`icon-${id}`);
                const collapse = bootstrap.Collapse.getInstance(menu);
                if (collapse && menu.classList.contains('show')) {
                    collapse.hide();
                    if (icon) icon.classList.remove('rotate');
                }
            }
        });

        if (isOpen) {
            clickedCollapse.hide();
            clickedIcon.classList.remove('rotate');
        } else {
            clickedCollapse.show();
            clickedIcon.classList.add('rotate');
        }
    }

    document.addEventListener("DOMContentLoaded", function () {
        // Highlight active nav link
        const currentUrl = window.location.href;
        document.querySelectorAll(".nav-link").forEach(link => {
            if (link.href && link.id !== 'logoutLink') {
                const linkPath = new URL(link.href).pathname;
                const currentPath = new URL(currentUrl).pathname;
                if (currentPath.includes(linkPath) && linkPath !== '/') {
                    link.classList.add("active");
                }
            }

            // Collapse dropdown if submenu item is clicked
            if (link.closest('.submenu')) {
                link.addEventListener('click', function () {
                    const parentCollapse = this.closest('.submenu.collapse');
                    if (parentCollapse) {
                        const collapseInstance = bootstrap.Collapse.getInstance(parentCollapse);
                        if (collapseInstance) {
                            collapseInstance.hide();
                            const parentDropdown = parentCollapse.previousElementSibling;
                            if (parentDropdown && parentDropdown.classList.contains('nav-link')) {
                                const icon = parentDropdown.querySelector('.dropdown-icon');
                                if (icon) icon.classList.remove('rotate');
                            }
                        }
                    }
                });
            }
        });
    });





document.getElementById('generatePdfBtn').addEventListener('click', function() {
    const element = document.getElementById('pdfWrapper');

    const opt = {
        margin: 0,
        filename: 'ACSO_Certificate.pdf',
        image: { type: 'png', quality: 1 },
        html2canvas: { scale: 2, useCORS: true },
        jsPDF: {
            unit: 'px',
            format: [element.offsetWidth, element.offsetHeight],
            orientation: 'portrait'
        }
    };

    html2pdf().set(opt).from(element).save();
});
