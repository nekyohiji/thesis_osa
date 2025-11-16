


  function isInViewport(element) {
    const rect = element.getBoundingClientRect();
    return rect.top <= window.innerHeight * 0.75 && rect.bottom >= 0;
  }

  function animateSection(sectionId) {
    const section = document.getElementById(sectionId);
    const content = section.querySelector('.content');
    const bars = section.querySelectorAll('.shape-bar');

    if (!section) return;

    if (isInViewport(section)) {
      section.classList.add('visible');
      if (content) content.classList.add('animate');

      bars.forEach((bar, index) => {
        setTimeout(() => {
          bar.classList.add('slide-in');
        }, index * 200);
      });
    } else {
      section.classList.remove('visible');
      if (content) content.classList.remove('animate');
      bars.forEach(bar => bar.classList.remove('slide-in'));
    }
  }

  function handleScrollAnimations() {
    animateSection('home');
    animateSection('about');
    animateSection('services'); 
  }

  window.addEventListener('scroll', handleScrollAnimations);
  window.addEventListener('load', handleScrollAnimations);


// /////////////////////ABOUT


// /////////////////////CONTACT

