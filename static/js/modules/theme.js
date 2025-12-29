/**
 * Moment Dashboard - Theme Management
 * Dark/Light mode switching
 */

import { state } from './state.js';
import { updateChartTheme } from './chart.js';

// Initialize theme from localStorage
export function initTheme() {
  applyTheme();
}

// Toggle between dark and light mode
export function toggleTheme() {
  state.ui.darkMode = !state.ui.darkMode;
  applyTheme();
  
  const settingTheme = document.getElementById('setting-theme');
  if (settingTheme) settingTheme.checked = state.ui.darkMode;
}

// Apply current theme
export function applyTheme() {
  const theme = state.ui.darkMode ? 'dark' : 'light';
  document.documentElement.setAttribute('data-theme', theme);
  localStorage.setItem('theme', theme);
  
  // Update chart colors
  updateChartTheme(state.ui.darkMode);
}
