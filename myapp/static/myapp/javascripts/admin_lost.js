
        /* Sidebar Functions*/
        // Toggle Sidebar
        function toggleSidebar() {
            const sidebar = document.getElementById('sidebar');
            sidebar.classList.toggle('show');
        }

        // Handle Dropdowns Uniformly (for main menu items)
        function handleDropdown(menuId) {
            const clickedIcon = document.getElementById(`icon-${menuId}`);
            const clickedMenu = document.getElementById(menuId);
            const clickedCollapse = bootstrap.Collapse.getOrCreateInstance(clickedMenu);

            // Toggle clicked menu
            const isCurrentlyOpen = clickedMenu.classList.contains('show');

            // Close other top-level dropdowns
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

            // Now, toggle the clicked menu
            if (isCurrentlyOpen) {
                clickedCollapse.hide();
                clickedIcon.classList.remove('rotate');
            } else {
                clickedCollapse.show();
                clickedIcon.classList.add('rotate');
            }
        }

        document.addEventListener('DOMContentLoaded', function () {
            const currentUrl = window.location.href;
            const navLinks = document.querySelectorAll('.nav-link');

            navLinks.forEach(link => {
                // Exclude the logout link from active state
                if (link.href && link.id !== 'logoutLink') {
                    const linkPath = new URL(link.href).pathname;
                    const currentPath = new URL(currentUrl).pathname;

                    // Apply 'active' class to the current page's link
                    // Use includes for partial match, but be careful with root path '/'
                    if (currentPath.includes(linkPath) && linkPath !== '/') {
                        link.classList.add('active');

                        // *** IMPORTANT CHANGE HERE: REMOVED AUTO-OPENING PARENT DROPDOWN ON PAGE LOAD ***
                        // To ensure the dropdown closes unless explicitly clicked,
                        // we do NOT re-open the parent here even if a child is active.
                        // The 'active' class will still highlight the child link.
                    }
                }

                // Add click listener for all nav-links to close parent dropdowns if they are submenu items
                if (link.closest('.submenu')) { // Check if the link is inside a submenu
                    link.addEventListener('click', function() {
                        const parentCollapse = this.closest('.submenu.collapse');
                        if (parentCollapse) {
                            const parentCollapseInstance = bootstrap.Collapse.getInstance(parentCollapse);
                            if (parentCollapseInstance) {
                                parentCollapseInstance.hide(); // Hide the parent submenu
                                // Also rotate the icon back if it's a top-level dropdown icon
                                const parentDropdownLink = parentCollapse.previousElementSibling;
                                if (parentDropdownLink && parentDropdownLink.classList.contains('nav-link')) {
                                    const icon = parentDropdownLink.querySelector('.dropdown-icon');
                                    if (icon) {
                                        icon.classList.remove('rotate');
                                    }
                                }
                            }
                        }
                    });
                }
            });

            /* Lost & Found: Image Preview */
            const imageUpload = document.getElementById('imageUpload');
            const imagePreview = document.getElementById('imagePreview');
            const imagePreviewContainer = document.getElementById('imagePreviewContainer');

            // Only attach event listener if elements exist
            if (imageUpload && imagePreview && imagePreviewContainer) {
                imageUpload.addEventListener('change', function (event) {
                    if (event.target.files && event.target.files[0]) {
                        const reader = new FileReader();
                        reader.onload = function (e) {
                            imagePreview.src = e.target.result;
                            imagePreviewContainer.style.display = 'flex';
                        };
                        reader.readAsDataURL(event.target.files[0]);
                    } else {
                        removeImagePreview();
                    }
                });
            }
        }); // End of DOMContentLoaded

        function previewImage(event) {
            const imagePreview = document.getElementById('imagePreview');
            const imagePreviewContainer = document.getElementById('imagePreviewContainer');
            if (event.target.files && event.target.files[0]) {
                const reader = new FileReader();
                reader.onload = function (e) {
                    imagePreview.src = e.target.result;
                    imagePreviewContainer.style.display = 'flex';
                };
                reader.readAsDataURL(event.target.files[0]);
            } else {
                removeImagePreview();
            }
        }

        function removeImagePreview() {
            const imageUpload = document.getElementById('imageUpload');
            const imagePreview = document.getElementById('imagePreview');
            const imagePreviewContainer = document.getElementById('imagePreviewContainer');

            if (imagePreview && imagePreviewContainer && imageUpload) {
                imagePreview.src = '#';
                imagePreviewContainer.style.display = 'none';
                imageUpload.value = '';
            }
        }
        // The deleteItem function was incorrectly placed and causing an issue.
        // It's not called directly from HTML now, but through showDeleteModal.
        // Keeping it commented out or removed ensures no duplicate definitions if it exists elsewhere.
        /* function deleteItem(itemId) {
            if (!confirm("Are you sure you want to delete this item?")) return;
            fetch(`/lostandfound/ajax/delete/${itemId}/`, {
                method: "POST",
                headers: {
                    "X-CSRFToken": getCSRFToken(),
                }
            }).then(res => res.json()).then(data => {
                if (data.success) {
                    location.reload(); // or dynamically remove the card
                }
            });
        } */

        function editItem(itemId) {
            document.getElementById('editItemId').value = itemId;
            const card = document.querySelector(`[data-item-id="${itemId}"]`);
            document.getElementById('editDescription').value = card.querySelector('.description-text').innerText.trim();
            const modal = new bootstrap.Modal(document.getElementById('editModal'));
            modal.show();
        }

        function submitEdit() {
            const itemId = document.getElementById('editItemId').value;
            const formData = new FormData(document.getElementById('editForm'));
            fetch(`/lostandfound/ajax/edit/${itemId}/`, {
                method: "POST",
                headers: {
                    "X-CSRFToken": getCSRFToken(),
                },
                body: formData
            }).then(res => res.json()).then(data => {
                if (data.success) {
                    location.reload(); // or update the card contents dynamically
                } else {
                    console.error("Edit failed:", data.error);
                    alert("Failed to edit item: " + (data.error || "Unknown error"));
                }
            }).catch(error => {
                console.error("Error submitting edit:", error);
                alert("An error occurred while submitting the edit.");
            });
        }

        function getCSRFToken() {
            return document.querySelector('[name=csrfmiddlewaretoken]').value;
        }

        let deleteItemId = null;

        function showDeleteModal(itemId) {
            deleteItemId = itemId;
            const modal = new bootstrap.Modal(document.getElementById('deleteModal'));
            modal.show();
        }

        document.getElementById('confirmDeleteBtn').addEventListener('click', () => {
            if (!deleteItemId) return;

            fetch(`/lostandfound/ajax/delete/${deleteItemId}/`, {
                method: "POST",
                headers: {
                    "X-CSRFToken": getCSRFToken(),
                }
            }).then(res => res.json()).then(data => {
                if (data.success) {
                    location.reload(); // or remove card dynamically
                } else {
                    console.error("Delete failed:", data.error);
                    alert("Failed to delete item: " + (data.error || "Unknown error"));
                }
            }).catch(error => {
                console.error("Error deleting item:", error);
                alert("An error occurred while deleting the item.");
            });

            // hide modal
            const modal = bootstrap.Modal.getInstance(document.getElementById('deleteModal'));
            modal.hide();
        });


 ///////////////////////////////////////////////////////
        window.addEventListener('pageshow', function (e) {
            if (e.persisted) location.reload();
        });
//////////////////////////////////////////////////////////