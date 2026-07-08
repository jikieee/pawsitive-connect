// Phase 3 — Mobile responsiveness helpers shared by all dashboards.
(function () {
  function ensureBackdrop() {
    if (document.querySelector('.mobile-sidebar-backdrop')) return;
    const backdrop = document.createElement('div');
    backdrop.className = 'mobile-sidebar-backdrop';
    backdrop.setAttribute('aria-hidden', 'true');
    backdrop.addEventListener('click', closeSidebar);
    document.body.appendChild(backdrop);
  }

  function isMobile() {
    return window.matchMedia('(max-width: 820px)').matches;
  }

  function openSidebar() {
    const sidebar = document.getElementById('sidebar');
    if (!sidebar) return;
    ensureBackdrop();
    sidebar.classList.add('open');
    document.body.classList.add('sidebar-open');
  }

  function closeSidebar() {
    const sidebar = document.getElementById('sidebar');
    if (!sidebar) return;
    sidebar.classList.remove('open');
    document.body.classList.remove('sidebar-open');
  }

  window.toggleSidebar = function () {
    const sidebar = document.getElementById('sidebar');
    if (!sidebar) return;
    if (sidebar.classList.contains('open')) closeSidebar();
    else openSidebar();
  };

  function addAdminMenuButton() {
    const topbar = document.querySelector('body.admin-page .topbar');
    if (!topbar || topbar.querySelector('.admin-mobile-menu-btn')) return;
    const btn = document.createElement('button');
    btn.type = 'button';
    btn.className = 'admin-mobile-menu-btn mobile-only';
    btn.setAttribute('aria-label', 'Open navigation menu');
    btn.textContent = '☰';
    btn.addEventListener('click', window.toggleSidebar);
    topbar.prepend(btn);
  }

  function labelTables() {
    document.querySelectorAll('table').forEach(table => {
      const headers = Array.from(table.querySelectorAll('thead th')).map(th => th.textContent.trim());
      if (!headers.length) return;
      table.querySelectorAll('tbody tr').forEach(row => {
        Array.from(row.children).forEach((cell, index) => {
          if (!cell.hasAttribute('data-label') && headers[index]) {
            cell.setAttribute('data-label', headers[index]);
          }
        });
      });
    });
  }

  function invalidateMapsAndCharts() {
    setTimeout(() => {
      // Leaflet stores map instances on containers in many builds as _leaflet_id.
      // Dispatch resize so Leaflet/Chart.js listeners recalculate dimensions.
      window.dispatchEvent(new Event('resize'));

      if (window.Chart && Chart.instances) {
        Object.values(Chart.instances).forEach(chart => {
          if (chart && typeof chart.resize === 'function') chart.resize();
        });
      }
    }, 180);
  }

  function patchTabClosers() {
    document.addEventListener('click', event => {
      const nav = event.target.closest('.nav-item, [data-admin-nav]');
      if (nav && isMobile()) {
        setTimeout(closeSidebar, 120);
        setTimeout(invalidateMapsAndCharts, 180);
      }

      const modalTrigger = event.target.closest('[onclick*="openModal"], [onclick*="openAdmin"], [onclick*="openReport"], [onclick*="openAnimal"]');
      if (modalTrigger) invalidateMapsAndCharts();
    });

    document.addEventListener('keydown', event => {
      if (event.key === 'Escape') closeSidebar();
    });
  }

  function syncOnResize() {
    if (!isMobile()) closeSidebar();
    invalidateMapsAndCharts();
  }

  document.addEventListener('DOMContentLoaded', () => {
    ensureBackdrop();
    addAdminMenuButton();
    labelTables();
    patchTabClosers();
    invalidateMapsAndCharts();
    window.addEventListener('resize', syncOnResize);
  });
})();
