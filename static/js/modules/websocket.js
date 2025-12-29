/**
 * Moment Dashboard - WebSocket Connection
 * Real-time communication with server
 */

import { state, el } from './state.js';
import { handleMessage } from './handlers.js';

export function connect() {
  const protocol = location.protocol === 'https:' ? 'wss:' : 'ws:';
  state.ws = new WebSocket(`${protocol}//${location.host}/ws`);

  state.ws.onopen = () => {
    state.reconnectAttempts = 0;
    updateConnectionStatus('connected');
  };

  state.ws.onmessage = e => handleMessage(JSON.parse(e.data));

  state.ws.onclose = () => {
    updateConnectionStatus('disconnected');
    if (state.reconnectAttempts < 10) {
      setTimeout(connect, Math.min(1000 * Math.pow(2, state.reconnectAttempts++), 30000));
    }
  };

  state.ws.onerror = () => updateConnectionStatus('error');
}

export function send(msg) {
  if (state.ws?.readyState === WebSocket.OPEN) {
    state.ws.send(JSON.stringify(msg));
  }
}

export function updateConnectionStatus(status) {
  const connectionStatus = document.getElementById('connection-status');
  if (connectionStatus) {
    connectionStatus.className = `connection-status ${status}`;
    connectionStatus.querySelector('.status-label').textContent =
      status === 'connected' ? 'Connected' : status === 'disconnected' ? 'Disconnected' : 'Connecting';
  }

  const wsStatus = document.getElementById('ws-status');
  if (wsStatus) {
    wsStatus.textContent = status === 'connected' ? 'Connected' : 'Disconnected';
    wsStatus.className = `status-badge ${status === 'connected' ? 'success' : 'danger'}`;
  }
}
