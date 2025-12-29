/**
 * Moment Dashboard - Main Application
 * Modular entry point
 * 
 * Module Structure:
 * - state.js      : Application state management
 * - router.js     : Client-side routing
 * - badges.js     : Navigation badge updates
 * - websocket.js  : WebSocket connection
 * - handlers.js   : Message handlers
 * - ui-updates.js : UI update functions
 * - analytics.js  : Analytics page updates
 * - events.js     : Event feed management
 * - chart.js      : Risk trend chart
 * - audio.js      : Sound and alerts
 * - theme.js      : Theme management
 * - toast.js      : Toast notifications
 * - actions.js    : User actions
 * - elements.js   : DOM element caching
 * - listeners.js  : Event listeners
 */

import { state } from './modules/state.js';
import { router } from './modules/router.js';
import { badges } from './modules/badges.js';
import { connect } from './modules/websocket.js';
import { cacheElements } from './modules/elements.js';
import { initListeners } from './modules/listeners.js';
import { initTheme } from './modules/theme.js';
import { initChart } from './modules/chart.js';
import { updateSoundIcon } from './modules/audio.js';

// Initialize application
function init() {
  console.log('Moment Dashboard initializing...');
  
  // Cache DOM elements
  cacheElements();
  
  // Initialize router
  router.init();
  
  // Initialize theme
  initTheme();
  
  // Initialize chart
  initChart();
  
  // Setup event listeners
  initListeners();
  
  // Connect WebSocket
  connect();
  
  // Update sound icon
  updateSoundIcon();
  
  console.log('Moment Dashboard initialized');
}

// Export for global access if needed
window.MomentApp = {
  state,
  router,
  badges
};

// Initialize on DOM ready
document.addEventListener('DOMContentLoaded', init);
