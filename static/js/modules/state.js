/**
 * Moment Dashboard - State Management
 * Centralized application state
 */

export const state = {
  ws: null,
  reconnectAttempts: 0,
  metrics: {
    events_produced: 0,
    decisions_made: 0,
    blocked: 0,
    allowed: 0,
    escalated: 0,
    throttled: 0,
    avg_latency_ms: 0
  },
  kafka: {
    messages_sent: 0,
    messages_per_sec: 0,
    connection_status: 'connecting'
  },
  confluent: {
    schema_registry: { connected: false },
    ksqldb: { connected: false },
    metrics_api: { connected: false }
  },
  simulation: { running: false },
  ui: {
    soundEnabled: localStorage.getItem('soundEnabled') !== 'false',
    visualAlerts: localStorage.getItem('visualAlerts') !== 'false',
    darkMode: localStorage.getItem('theme') !== 'light',
    lastBlockedCount: 0,
    newBlockedCount: 0,
    isFirstEvent: true
  },
  chart: null,
  audio: null
};

// Element cache
export const el = {};

// Toast container reference
export let toastContainer = null;

export function setToastContainer(container) {
  toastContainer = container;
}
