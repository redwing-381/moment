/**
 * Moment Dashboard - Event Listeners
 * UI event bindings
 */

import { state, el } from './state.js';
import { router } from './router.js';
import { toggleSound, updateSoundIcon } from './audio.js';
import { toggleTheme, applyTheme } from './theme.js';
import { startSimulation, stopSimulation, resetMetrics, runScenario, setDecisionMode, exportReport } from './actions.js';

// Toggle mobile menu
function toggleMobileMenu() {
  el.sidebar?.classList.toggle('open');
  el.mobileOverlay?.classList.toggle('active');
}

// Close mobile menu
function closeMobileMenu() {
  el.sidebar?.classList.remove('open');
  el.mobileOverlay?.classList.remove('active');
}

// Initialize all event listeners
export function initListeners() {
  // Navigation
  document.querySelectorAll('.nav-link').forEach(link => {
    link.addEventListener('click', e => {
      e.preventDefault();
      router.navigate(link.dataset.page);
    });
  });

  // Mobile menu
  el.menuToggle?.addEventListener('click', toggleMobileMenu);
  el.mobileOverlay?.addEventListener('click', closeMobileMenu);

  // Sliders
  el.eventCount?.addEventListener('input', e => el.eventCountVal.textContent = e.target.value);
  el.attackPct?.addEventListener('input', e => el.attackPctVal.textContent = e.target.value + '%');
  el.duration?.addEventListener('input', e => el.durationVal.textContent = e.target.value + 's');

  // Buttons
  el.btnStart?.addEventListener('click', startSimulation);
  el.btnStop?.addEventListener('click', stopSimulation);
  el.btnReset?.addEventListener('click', resetMetrics);
  el.btnExport?.addEventListener('click', exportReport);
  el.btnInsider?.addEventListener('click', () => runScenario('insider_threat'));
  el.btnBruteforce?.addEventListener('click', () => runScenario('brute_force'));
  el.btnExfiltration?.addEventListener('click', () => runScenario('data_exfiltration'));

  // Sound toggle
  el.soundToggle?.addEventListener('click', toggleSound);

  // Theme toggle
  el.themeToggle?.addEventListener('click', toggleTheme);

  // Settings
  el.settingSound?.addEventListener('change', e => {
    state.ui.soundEnabled = e.target.checked;
    localStorage.setItem('soundEnabled', state.ui.soundEnabled);
    updateSoundIcon();
  });

  el.settingVisual?.addEventListener('change', e => {
    state.ui.visualAlerts = e.target.checked;
    localStorage.setItem('visualAlerts', state.ui.visualAlerts);
  });

  el.settingTheme?.addEventListener('change', e => {
    state.ui.darkMode = e.target.checked;
    applyTheme();
  });

  // Init settings checkboxes
  if (el.settingSound) el.settingSound.checked = state.ui.soundEnabled;
  if (el.settingVisual) el.settingVisual.checked = state.ui.visualAlerts;
  if (el.settingTheme) el.settingTheme.checked = state.ui.darkMode;

  // Decision mode selector
  document.querySelectorAll('input[name="decision-mode"]').forEach(radio => {
    radio.addEventListener('change', e => {
      if (e.target.checked) {
        setDecisionMode(e.target.value);
      }
    });
  });
}
