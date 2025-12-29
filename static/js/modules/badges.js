/**
 * Moment Dashboard - Badge Management
 * Navigation badge updates
 */

export const badges = {
  events: 0,

  updateEvents(count) {
    this.events = count;
    const badge = document.getElementById('badge-events');
    if (badge) {
      const router = window.MomentApp?.router;
      if (count > 0 && router?.current !== 'events') {
        badge.textContent = count > 99 ? '99+' : count;
        badge.classList.add('visible');
      } else {
        badge.classList.remove('visible');
      }
    }
  },

  clearEvents() {
    this.events = 0;
    document.getElementById('badge-events')?.classList.remove('visible');
  },

  updateAnalytics(connected) {
    const badge = document.getElementById('badge-analytics');
    if (badge) {
      badge.textContent = '✓';
      badge.classList.toggle('visible', connected);
      badge.classList.toggle('success-badge', connected);
    }
  },

  updateDashboard(running) {
    const badge = document.getElementById('badge-dashboard');
    if (badge) {
      badge.classList.toggle('visible', running);
      badge.classList.toggle('running-badge', running);
    }
  }
};
