/**
 * Moment Dashboard - Event Feed
 * Event display and explanation panel
 */

import { state, el } from './state.js';
import { showToast } from './toast.js';

// Add event to feed
export function addEvent(data) {
  if (!el.eventFeed) return;

  if (state.ui.isFirstEvent) {
    el.eventFeed.innerHTML = '';
    state.ui.isFirstEvent = false;
  }

  const d = data.decision.decision;
  const risk = data.signal.risk_score;
  const riskClass = risk >= 0.6 ? 'high' : risk >= 0.4 ? 'medium' : 'low';

  const item = document.createElement('div');
  item.className = `event-item ${d}`;
  item.innerHTML = `
    <div class="event-main">
      <span class="event-actor">${data.event.actor_id}</span>
      <span class="event-action">${data.event.action}</span>
    </div>
    <div class="event-meta">
      <span class="event-risk ${riskClass}">${(risk * 100).toFixed(0)}%</span>
      <span class="event-latency">${data.latency_ms}ms</span>
      <span class="event-decision ${d}">${d}</span>
    </div>
  `;

  item.addEventListener('click', () => showExplanation(data));
  
  if (d === 'block') {
    showExplanation(data);
    showToast('Threat Blocked', `${data.event.actor_id} - ${data.event.action}`, 'danger');
  } else if (d === 'escalate') {
    showToast('Escalated', `${data.event.actor_id} - ${data.event.action}`, 'warning', 3000);
  }

  el.eventFeed.insertBefore(item, el.eventFeed.firstChild);
  
  // Limit to 50 events
  while (el.eventFeed.children.length > 50) {
    el.eventFeed.removeChild(el.eventFeed.lastChild);
  }
}

// Show event explanation
export function showExplanation(data) {
  if (!el.explanationPanel) return;

  const d = data.decision.decision;
  el.explanationPanel.innerHTML = `
    <div class="explanation-header">
      <span class="explanation-decision ${d}">${d.toUpperCase()}</span>
    </div>
    <div class="explanation-meta">
      Actor: <span class="mono">${data.event.actor_id}</span> · 
      Action: ${data.event.action} · 
      Latency: ${data.latency_ms}ms
    </div>
    <div class="explanation-content">${data.explanation || 'No analysis available'}</div>
  `;
}
