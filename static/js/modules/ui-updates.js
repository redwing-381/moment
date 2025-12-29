/**
 * Moment Dashboard - UI Updates
 * Functions for updating UI elements
 */

import { state, el } from './state.js';
import { badges } from './badges.js';
import { triggerAlert } from './audio.js';

// Helper to set element value only if changed
function setValue(element, val) {
  if (element && element.textContent !== String(val)) {
    element.textContent = val;
  }
}

// Update status badge helper
function updateStatusBadge(element, connected) {
  if (!element) return;
  element.textContent = connected ? 'Connected' : 'Offline';
  element.className = `status-badge ${connected ? 'success' : ''}`;
}

// Update main stats
export function updateStats(m) {
  if (!m) return;

  setValue(el.metricEvents, m.events_produced);
  setValue(el.metricDecisions, m.decisions_made);
  setValue(el.metricAllowed, m.allowed);
  setValue(el.metricThrottled, m.throttled);
  setValue(el.metricEscalated, m.escalated);
  setValue(el.metricBlocked, m.blocked);
  if (el.metricLatency) el.metricLatency.textContent = m.avg_latency_ms.toFixed(1);

  if (m.blocked > state.ui.lastBlockedCount) {
    state.ui.newBlockedCount += m.blocked - state.ui.lastBlockedCount;
    const router = window.MomentApp?.router;
    if (router?.current !== 'events') badges.updateEvents(state.ui.newBlockedCount);
    triggerAlert();
    state.ui.lastBlockedCount = m.blocked;
  }

  state.metrics = { ...m };
}

// Update Kafka metrics
export function updateKafka(k) {
  if (!k) return;
  if (el.kafkaMessages) el.kafkaMessages.textContent = k.messages_sent;
  if (el.kafkaRate) el.kafkaRate.textContent = k.messages_per_sec.toFixed(1);

  const status = k.connection_status === 'connected' ? 'success' : 'danger';
  if (el.kafkaStatus) {
    el.kafkaStatus.textContent = k.connection_status === 'connected' ? 'Connected' : 'Error';
    el.kafkaStatus.className = `status-badge ${status}`;
  }
  if (el.kafkaConnStatus) {
    el.kafkaConnStatus.textContent = k.connection_status === 'connected' ? 'Connected' : 'Error';
    el.kafkaConnStatus.className = `status-badge ${status}`;
  }

  state.kafka = { ...k };
}

// Update Confluent status
export function updateConfluent(c) {
  if (!c) return;

  updateStatusBadge(el.srStatus, c.schema_registry.connected);
  updateStatusBadge(el.ksqlStatus, c.ksqldb.connected);
  updateStatusBadge(el.metricsApiStatus, c.metrics_api.connected);
  updateStatusBadge(el.srConnStatus, c.schema_registry.connected);
  updateStatusBadge(el.ksqlConnStatus, c.ksqldb.connected);

  if (el.srFormat) el.srFormat.textContent = c.schema_registry.format || 'Avro';
  if (el.ksqlStreams) el.ksqlStreams.textContent = c.ksqldb.streams_ready ? 'Streams Ready' : 'Stream Processing';
  if (el.clusterId) el.clusterId.textContent = c.metrics_api.cluster_id || 'Cluster Monitoring';

  const allConnected = c.schema_registry.connected && c.ksqldb.connected && c.metrics_api.connected;
  if (el.fullIntegrationBadge) el.fullIntegrationBadge.style.display = allConnected ? 'inline' : 'none';
  badges.updateAnalytics(allConnected);

  state.confluent = { ...c };
}

// Update risky actors list
export function updateActors(actors) {
  if (!actors?.length || !el.riskyActors) return;

  el.riskyActors.innerHTML = actors.map((a, i) => {
    const rankClass = i === 0 ? 'gold' : i === 1 ? 'silver' : i === 2 ? 'bronze' : '';
    const riskClass = a.avg_risk >= 0.6 ? 'high' : a.avg_risk >= 0.4 ? 'medium' : 'low';
    return `
      <div class="actor-item">
        <div class="actor-info">
          <span class="actor-rank ${rankClass}">${i + 1}</span>
          <div>
            <div class="actor-name">${a.actor_id}</div>
            <div class="actor-stats">${a.events} events, ${a.blocked} blocked</div>
          </div>
        </div>
        <div class="actor-risk">
          <div class="actor-risk-value ${riskClass}">${(a.avg_risk * 100).toFixed(0)}%</div>
          <div class="actor-risk-label">avg risk</div>
        </div>
      </div>
    `;
  }).join('');
}

// Update ksqlDB summaries table
export function updateKsqlDB(summaries) {
  if (!summaries?.length) return;

  if (el.ksqldbPlaceholder) el.ksqldbPlaceholder.classList.add('hidden');
  if (el.ksqldbSummaries) el.ksqldbSummaries.classList.remove('hidden');

  if (el.ksqldbTableBody) {
    el.ksqldbTableBody.innerHTML = summaries.map(s => {
      const riskClass = s.avg_risk >= 0.6 ? 'danger' : s.avg_risk >= 0.4 ? 'warning' : 'success';
      return `
        <tr>
          <td class="mono">${s.actor_id}</td>
          <td>${s.event_count}</td>
          <td class="${riskClass}">${(s.avg_risk * 100).toFixed(0)}%</td>
          <td>${(s.max_risk * 100).toFixed(0)}%</td>
          <td>${s.high_risk_count}</td>
          <td><span class="status-badge ${s.is_flagged ? 'danger' : 'success'}">${s.is_flagged ? 'Flagged' : 'Normal'}</span></td>
        </tr>
      `;
    }).join('');
  }
}

// Update decision stats
export function updateDecisionStats(stats) {
  if (!stats) return;

  const elements = {
    'stat-rule-decisions': stats.rule_decisions || 0,
    'stat-cache-hits': stats.cache_hits || 0,
    'stat-ai-decisions': stats.ai_decisions || 0,
    'stat-rule-latency': (stats.avg_rule_latency_ms || 0).toFixed(1),
    'stat-cache-latency': (stats.avg_cache_latency_ms || 0).toFixed(1),
    'stat-ai-latency': (stats.avg_ai_latency_ms || 0).toFixed(1)
  };

  Object.entries(elements).forEach(([id, value]) => {
    const element = document.getElementById(id);
    if (element) element.textContent = value;
  });
}

// Update progress bar
export function updateProgress(p) {
  if (el.progressBar) el.progressBar.style.width = `${p}%`;
}

// Set status text
export function setStatus(text) {
  if (el.statusText) el.statusText.textContent = text;
}
