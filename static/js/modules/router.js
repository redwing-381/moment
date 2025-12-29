/**
 * Moment Dashboard - Router
 * Client-side hash-based routing
 */

import { badges } from './badges.js';

function closeMobileMenu() {
  document.getElementById('sidebar')?.classList.remove('open');
  document.getElementById('mobile-overlay')?.classList.remove('active');
}

export const router = {
  current: 'dashboard',
  pages: ['dashboard', 'events', 'analytics', 'settings'],
  titles: {
    dashboard: 'Overview',
    events: 'Event Stream',
    analytics: 'Analytics',
    settings: 'Settings'
  },

  init() {
    window.addEventListener('hashchange', () => this.route());
    this.route();
  },

  route() {
    const hash = window.location.hash.slice(2) || 'dashboard';
    const page = this.pages.includes(hash) ? hash : 'dashboard';
    this.navigate(page, false);
  },

  navigate(page, updateHash = true) {
    if (!this.pages.includes(page)) return;
    if (updateHash) window.location.hash = `/${page}`;

    document.querySelectorAll('.page').forEach(p => p.classList.remove('active'));
    document.getElementById(`page-${page}`)?.classList.add('active');

    document.querySelectorAll('.nav-link').forEach(link => {
      link.classList.toggle('active', link.dataset.page === page);
    });

    document.getElementById('page-title').textContent = this.titles[page];

    if (page === 'events') badges.clearEvents();
    this.current = page;
    closeMobileMenu();
  }
};
