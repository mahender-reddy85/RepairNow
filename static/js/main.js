document.addEventListener('DOMContentLoaded', () => {
  initMobileNav();
  initNotificationDismiss();
  initAvailabilityToggle();
  initTrackingPoller();
  initStarRating();
  initActiveNavHighlight();
  initAlertAutoDismiss();
  initStepperAnimation();
});

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

function initStepperAnimation() {
  const stepper = document.querySelector('.stepper');
  if (!stepper) return;

  function runStepperAnimation() {
    const progress = stepper.querySelector('.stepper-progress');
    const steps = stepper.querySelectorAll('.step-item');

    steps.forEach(step => step.classList.remove('completed'));

    progress.style.animation = 'none';
    progress.offsetHeight;
    progress.style.animation = 'progressFill 2.5s ease-out forwards';

    steps.forEach((step, index) => {
      const circle = step.querySelector('.step-circle');
      circle.style.animation = 'none';
      circle.offsetHeight;

      const delays = [
        { anim: '0.6s', timeout: 1000 },
        { anim: '1.4s', timeout: 1800 },
        { anim: '2.2s', timeout: 2600 },
      ];

      if (delays[index]) {
        circle.style.animation = `stepComplete 0.4s ease-out ${delays[index].anim} forwards`;
        setTimeout(() => step.classList.add('completed'), delays[index].timeout);
      }
    });
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