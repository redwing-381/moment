/**
 * Moment Dashboard - Audio & Alerts
 * Sound effects and visual alerts
 */

import { state, el } from './state.js';

// Play alert sound
export function playSound() {
  if (!state.ui.soundEnabled) return;
  
  try {
    if (!state.audio) {
      state.audio = new (window.AudioContext || window.webkitAudioContext)();
    }
    const osc = state.audio.createOscillator();
    const gain = state.audio.createGain();
    osc.connect(gain);
    gain.connect(state.audio.destination);
    osc.frequency.value = 800;
    gain.gain.setValueAtTime(0.2, state.audio.currentTime);
    gain.gain.exponentialRampToValueAtTime(0.01, state.audio.currentTime + 0.15);
    osc.start();
    osc.stop(state.audio.currentTime + 0.15);
  } catch (e) {
    // Ignore audio errors
  }
}

// Trigger visual and audio alert
export function triggerAlert() {
  playSound();
  
  if (state.ui.visualAlerts && el.blockedCard) {
    el.blockedCard.classList.add('flash', 'shake');
    setTimeout(() => el.blockedCard.classList.remove('flash', 'shake'), 500);
  }
}

// Toggle sound on/off
export function toggleSound() {
  state.ui.soundEnabled = !state.ui.soundEnabled;
  localStorage.setItem('soundEnabled', state.ui.soundEnabled);
  updateSoundIcon();
  
  const settingSound = document.getElementById('setting-sound');
  if (settingSound) settingSound.checked = state.ui.soundEnabled;
}

// Update sound icon state
export function updateSoundIcon() {
  const soundToggle = document.getElementById('sound-toggle');
  soundToggle?.classList.toggle('muted', !state.ui.soundEnabled);
}
