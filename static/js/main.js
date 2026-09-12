document.addEventListener('DOMContentLoaded', () => {
  initMobileNav();
  initNotificationDismiss();
  initAvailabilityToggle();
  initTrackingPoller();
  initStarRating();
  initActiveNavHighlight();
  initAlertAutoDismiss();
  initStepperAnimation();
  initImagePreview();
  initFileInputName();
  initHeroVisualSync();
});

function initHeroVisualSync() {
  const heroImage = document.querySelector('.hero-photo');
  const words = Array.from(document.querySelectorAll('.tech-word-text'));

  const serviceImageMap = {
    'AC Repair': '/media/customers/ac.png',
    'Computer Repair': '/media/customers/computer.png',
    'Electrical Repair': '/media/customers/electrician.jpg',
    'Mobile Repair': '/media/customers/mobile.jpg',
    'Plumbing': '/media/customers/plumbing.jpg',
    'Refrigerator Repair': '/media/customers/refrigirator.jpg',
    'TV Repair': '/media/customers/tv.png',
    'Vehicle Repair': '/media/customers/vehicle.png',
    'Washing Machine Repair': '/media/customers/technician.jpg'
  };

  let wordIndex = 0;

  if (words.length) {
    words[wordIndex].classList.add('active');
  }

  if (heroImage && words.length) {
    const firstService = words[0].textContent.trim();
    heroImage.src = serviceImageMap[firstService] || '/media/customers/technician.jpg';
    heroImage.alt = firstService + ' RepairNow service image';
  }

  setInterval(() => {
    const nextWordIndex = words.length ? (wordIndex + 1) % words.length : 0;

    if (heroImage && words.length) {
      const nextService = words[nextWordIndex].textContent.trim();
      const nextImage = serviceImageMap[nextService] || '/media/customers/technician.jpg';

      heroImage.animate([
        { opacity: 1 },
        { opacity: 0.2 },
        { opacity: 1 }
      ], {
        duration: 500,
        easing: 'ease-in-out'
      });

      setTimeout(() => {
        heroImage.src = nextImage;
        heroImage.alt = nextService + ' RepairNow service image';
        heroImage.title = nextService;
      }, 250);
    }

    if (words.length) {
      words[wordIndex].classList.remove('active');
      words[wordIndex].classList.add('exit');

      words[nextWordIndex].classList.remove('exit');
      words[nextWordIndex].classList.add('active');

      setTimeout(() => {
        words[wordIndex].classList.remove('exit');
      }, 480);

      wordIndex = nextWordIndex;
    }
  }, 3000);
}

function initMobileNav() {
  const toggleBtn = document.querySelector('.mobile-toggle');
  const drawer = document.querySelector('.mobile-drawer');
  const drawerClose = document.querySelector('.mobile-drawer-close');

  if (toggleBtn && drawer) {
    toggleBtn.addEventListener('click', () => {
      drawer.classList.add('open');
      document.body.style.overflow = 'hidden';
    });
  }

  if (drawerClose && drawer) {
    drawerClose.addEventListener('click', () => {
      drawer.classList.remove('open');
      document.body.style.overflow = '';
    });
  }

  if (drawer) {
    drawer.addEventListener('click', (e) => {
      if (e.target === drawer) {
        drawer.classList.remove('open');
        document.body.style.overflow = '';
      }
    });
  }
}

function initActiveNavHighlight() {
  const currentPath = window.location.pathname;
  const navLinks = document.querySelectorAll('.nav-link, .sidebar-nav a');

  navLinks.forEach(link => {
    const href = link.getAttribute('href');
    if (href && (currentPath === href || currentPath.startsWith(href + '/'))) {
      link.classList.add('active');
    }
  });
}

function initAlertAutoDismiss() {
  const alerts = document.querySelectorAll('.alert');
  alerts.forEach(alert => {
    setTimeout(() => {
      alert.classList.add('fade-out');
      setTimeout(() => {
        alert.remove();
      }, 300);
    }, 5000);
  });
}

function initNotificationDismiss() {
  document.querySelectorAll('.mark-read-btn').forEach(btn => {
    btn.addEventListener('click', async (e) => {
      e.preventDefault();
      const notifId = btn.dataset.notifId;
      if (!notifId) return;

      try {
        const res = await fetch(`/notifications/${notifId}/mark-read/?ajax=1`, {
          headers: { 'X-Requested-With': 'XMLHttpRequest' }
        });
        const data = await res.json();
        if (data.success) {
          const item = document.getElementById(`notif-item-${notifId}`);
          if (item) {
            item.classList.remove('unread');
            item.style.opacity = '0.6';
            btn.remove();
          }
          const badge = document.querySelector('.unread-count-badge');
          if (badge) {
            let count = parseInt(badge.textContent, 10) - 1;
            if (count > 0) {
              badge.textContent = count;
            } else {
              badge.remove();
            }
          }
        }
      } catch (err) {
        console.error('Error marking notification read:', err);
      }
    });
  });
}

function initAvailabilityToggle() {
  const toggleSelect = document.getElementById('tech-quick-avail-select');
  if (toggleSelect) {
    toggleSelect.addEventListener('change', async () => {
      const newStatus = toggleSelect.value;
      const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]')?.value;

      try {
        const formData = new FormData();
        formData.append('status', newStatus);

        const res = await fetch('/technician/availability/toggle-ajax/', {
          method: 'POST',
          headers: {
            'X-CSRFToken': csrfToken,
            'X-Requested-With': 'XMLHttpRequest'
          },
          body: formData
        });
        const data = await res.json();
        if (data.success) {
          const statusBadge = document.getElementById('tech-status-badge');
          if (statusBadge) {
            statusBadge.textContent = data.status_display;
            statusBadge.className = `badge badge-${data.status.toLowerCase()}`;
          }
        }
      } catch (err) {
        console.error('Error toggling availability:', err);
      }
    });
  }
}

function initTrackingPoller() {
  const trackerEl = document.getElementById('tracking-container');
  if (!trackerEl) return;

  const requestId = trackerEl.dataset.requestId;
  if (!requestId) return;

  const interval = setInterval(async () => {
    try {
      const res = await fetch(`/customer/repair/${requestId}/status-api/`);
      if (!res.ok) return;
      const data = await res.json();

      const currentStatusBadge = document.getElementById('live-status-badge');
      if (currentStatusBadge && currentStatusBadge.textContent !== data.request_status_display) {
        currentStatusBadge.textContent = data.request_status_display;

        window.location.reload();
      }

      if (data.is_completed) {
        clearInterval(interval);
      }
    } catch (err) {
      console.error('Status poll error:', err);
    }
  }, 8000);
}

function initStarRating() {
  const ratingContainers = document.querySelectorAll('.interactive-star-rating');
  ratingContainers.forEach(container => {
    const stars = container.querySelectorAll('.star-icon');
    const input = container.querySelector('input[type=hidden]');

    stars.forEach(star => {
      star.addEventListener('click', () => {
        const val = star.dataset.value;
        if (input) input.value = val;
        stars.forEach(s => {
          if (parseInt(s.dataset.value, 10) <= parseInt(val, 10)) {
            s.style.color = '#f59e0b';
          } else {
            s.style.color = '#cbd5e1';
          }
        });
      });
    });
  });
}

function initFileInputName() {
  const fileInputs = document.querySelectorAll('input[type="file"]');

  fileInputs.forEach(input => {
    const fileGroup = input.closest('.form-group');
    if (!fileGroup) return;

    const fileNameBox = fileGroup.querySelector('.file-input-name');
    const updateName = () => {
      const file = input.files && input.files[0];
      if (!fileNameBox) return;
      if (file) {
        fileNameBox.textContent = file.name;
        fileNameBox.style.display = 'block';
      } else {
        fileNameBox.textContent = 'No file chosen';
        fileNameBox.style.display = 'none';
      }
    };

    input.addEventListener('change', updateName);
    updateName();
  });
}

function initImagePreview() {
  const fileInputs = document.querySelectorAll('input[type="file"]');

  fileInputs.forEach(input => {
    const accepted = input.accept || '';
    if (!accepted.includes('image')) return;

    input.addEventListener('change', () => {
      const file = input.files && input.files[0];
      if (!file) return;

      const form = input.closest('form');
      if (!form) return;

      const profileLabel = form.querySelector(`label[for="${input.id}"]`);
      if (!profileLabel) return;

      let previewImg = profileLabel.querySelector('img.upload-preview-image');
      if (!previewImg) {
        const existingImg = profileLabel.querySelector('img');
        if (existingImg) {
          previewImg = existingImg;
          previewImg.classList.add('upload-preview-image');
        } else {
          previewImg = document.createElement('img');
          previewImg.className = 'upload-preview-image';
          previewImg.alt = 'Selected profile preview';
          previewImg.style.width = '100px';
          previewImg.style.height = '100px';
          previewImg.style.borderRadius = '50%';
          previewImg.style.objectFit = 'cover';
          previewImg.style.border = '3px solid var(--gray-200)';
          const placeholderIcon = profileLabel.querySelector('div');
          if (placeholderIcon) {
            placeholderIcon.remove();
          }
          profileLabel.appendChild(previewImg);
        }
      }

      const reader = new FileReader();
      reader.onload = function(evt) {
        previewImg.src = evt.target.result;
        previewImg.style.display = 'block';
      };
      reader.readAsDataURL(file);
    });
  });
}

function initStepperAnimation() {
  const stepper = document.querySelector('.stepper');
  if (!stepper) return;

  function runStepperAnimation() {
    const progress = stepper.querySelector('.stepper-progress');
    const steps = stepper.querySelectorAll('.step-item');

    steps.forEach(step => step.classList.remove('completed'));

    if (progress) {
      progress.style.animation = 'none';
      progress.offsetHeight;
      progress.style.animation = 'progressFill 3s ease-out forwards';
    }

    steps.forEach((step, index) => {
      const circle = step.querySelector('.step-circle');
      if (!circle) return;

      circle.style.animation = 'none';
      circle.offsetHeight;

      const delays = [
        { anim: '0.3s', timeout: 900 },
        { anim: '1.1s', timeout: 1700 },
        { anim: '1.9s', timeout: 2600 },
      ];

      if (delays[index]) {
        circle.style.animation = `stepComplete 0.45s ease-out ${delays[index].anim} forwards`;
        setTimeout(() => step.classList.add('completed'), delays[index].timeout);
      }
    });
  }

  if (!('IntersectionObserver' in window)) {
    runStepperAnimation();
    return;
  }

  const observer = new IntersectionObserver((entries) => {
    entries.forEach(entry => {
      if (entry.isIntersecting) {
        runStepperAnimation();
      }
    });
  }, { threshold: 0.3 });

  observer.observe(stepper);
}