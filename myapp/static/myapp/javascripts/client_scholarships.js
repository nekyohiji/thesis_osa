

document.addEventListener('DOMContentLoaded', function() {
    const scholarshipDetailModal = document.getElementById('scholarshipDetailModal');
    scholarshipDetailModal.addEventListener('show.bs.modal', function (event) {

        const button = event.relatedTarget;

        const title = button.getAttribute('data-title');
        const postedDate = button.getAttribute('data-posted-date');
        const deadlineDate = button.getAttribute('data-deadline-date');
        const category = button.getAttribute('data-category');
        const description = button.getAttribute('data-description');

        const modalTitle = scholarshipDetailModal.querySelector('#modalScholarshipTitle');
        const modalPostedDate = scholarshipDetailModal.querySelector('#modalScholarshipPostedDate');
        const modalDeadlineDate = scholarshipDetailModal.querySelector('#modalScholarshipDeadlineDate');
        const modalCategoryBadge = scholarshipDetailModal.querySelector('#modalScholarshipCategoryBadge');
        const modalDescription = scholarshipDetailModal.querySelector('#modalScholarshipDescription');

        modalTitle.innerHTML = `<i class="bi bi-journal-text me-2"></i>${title}`;
        modalPostedDate.textContent = postedDate;
        modalDeadlineDate.textContent = deadlineDate ? deadlineDate : 'N/A';
        modalDescription.innerHTML = description;

        modalCategoryBadge.classList.remove('bg-secondary', 'bg-success', 'bg-info');
        let iconClass = '';
        if (category === 'Internal') {
            modalCategoryBadge.classList.add('bg-secondary');
            iconClass = 'bi-house-fill';
        } else if (category === 'External (Govt)') {
            modalCategoryBadge.classList.add('bg-success');
            iconClass = 'bi-globe';
        } else {
            modalCategoryBadge.classList.add('bg-info');
            iconClass = 'bi-link-45deg';
        }
        modalCategoryBadge.innerHTML = `<i class="bi ${iconClass} me-1"></i>Category: ${category}`;
    });
});

function pollScholarships() {
    const container = document.getElementById('scholarships-feed');
    const scrollPos = window.scrollY;

    fetch('/api/scholarships/')
        .then(response => response.json())
        .then(data => {
            let html = '';

            data.scholarships.forEach(s => {
                html += `
                <div class="card mb-4 shadow-sm border-0">
                    <div class="card-body">
                        <h4 class="card-title text-primary mb-2">${s.title}</h4>
                        <h6 class="card-subtitle mb-3 text-muted">
                            Posted: ${s.posted_date} | Deadline: ${s.deadline_date}
                        </h6>
                        <p class="card-text">${s.description.replace(/\n/g, '<br>')}</p>
                    </div>
                </div>`;
            });

            if (data.scholarships.length === 0) {
                html = `<p class="text-center">No scholarships posted at this time. Please check back later.</p>`;
            }
            container.innerHTML = html;
            window.scrollTo(0, scrollPos);
        });
}

pollScholarships();
setInterval(pollScholarships, 10000);

function shareToFacebook(url, title) {
    const shareUrl = `https://www.facebook.com/sharer/sharer.php?u=${encodeURIComponent(url)}&quote=${encodeURIComponent(title)}`;
    window.open(shareUrl, '_blank', 'width=600,height=400');
}
