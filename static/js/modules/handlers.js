/**
 * Moment Dashboard - Message Handlers
 * WebSocket message processing
 */

import { state, el } from './state.js';
import { badges } from './badges.js';
import { updateStats, updateKafka, updateConfluent, updateActors, updateKsqlDB, updateDecisionStats, updateProgress, setStatus } from './ui-updates.js';
import { updateAgentPipeline, updatePipelineStatus, updateArchitecture, flashArchitectureFlow } from './analytics.js';
import { addEvent } from './events.js';
import { updateChart } from './chart.js';

// Main message handler
export function handleMessage(data) {
  switch (data.type) {
    case 'metrics': handleMetrics(data); break;
    case 'event_processed': handleEvent(data); break;
    case 'simulation_started': handleSimStart(data); break;
    case 'simulation_complete': handleSimComplete(); break;
    case 'scenario_started': handleScenarioStart(data); break;
    case 'scenario_complete': handleScenarioComplete(data); break;
    case 'metrics_reset': handleReset(); break;
    case 'decision_mode_changed': handleDecisionModeChanged(data); break;
    case 'decision_stats': updateDecisionStats(data.stats); break;
    case 'error': console.error(data.message); break;
  }
}

// Handle metrics update
function handleMetrics(data) {
  updateStats(data.data);
  updateKafka(data.kafka);
  updateChart(data.risk_trend);
  updateActors(data.top_actors);
  updateConfluent(data.confluent_status);
  updateKsqlDB(data.ksqldb_summaries);
  updateDecisionStats(data.decision_stats);
  updateAgentPipeline(data.data, data.decision_stats);
  updateArchitecture(data.data, data.decision_mode);
  
  if (data.progress !== undefined) updateProgress(data.progress);

  // Update decision mode if provided
  if (data.decision_mode) {
    const radio = document.getElementById(`mode-${data.decision_mode.replace('_', '-')}`);
    if (radio && !radio.checked) radio.checked = true;
  }
}

// Handle event processed
function handleEvent(data) {
  addEvent(data);
  if (el.eventCountBadge) {
    el.eventCountBadge.textContent = `${state.metrics.events_produced} events`;
  }
  flashArchitectureFlow();
}

// Handle simulation start
function handleSimStart(data) {
  state.simulation.running = true;
  state.ui.isFirstEvent = true;
  state.ui.newBlockedCount = 0;
  el.btnStart?.classList.add('hidden');
  el.btnStop?.classList.remove('hidden');
  badges.updateDashboard(true);
  setStatus(`Processing ${data.total_events} events...`);
  updatePipelineStatus(true);
}

// Handle simulation complete
function handleSimComplete() {
  state.simulation.running = false;
  el.btnStart?.classList.remove('hidden');
  el.btnStop?.classList.add('hidden');
  if (el.btnExport) el.btnExport.disabled = false;
  badges.updateDashboard(false);
  updateProgress(100);
  setStatus('Complete');
  updatePipelineStatus(false);
}

// Handle scenario start
function handleScenarioStart(data) {
  state.simulation.running = true;
  state.ui.isFirstEvent = true;
  state.ui.newBlockedCount = 0;
  el.btnStart?.classList.add('hidden');
  el.btnStop?.classList.remove('hidden');
  badges.updateDashboard(true);
  setStatus(`Running: ${data.scenario.name}`);
  updatePipelineStatus(true);
}

// Handle scenario complete
function handleScenarioComplete(data) {
  state.simulation.running = false;
  el.btnStart?.classList.remove('hidden');
  el.btnStop?.classList.add('hidden');
  if (el.btnExport) el.btnExport.disabled = false;
  updatePipelineStatus(false);
  badges.updateDashboard(false);
  updateProgress(100);
  setStatus(`${data.scenario} - ${data.summary.detection_rate}% detection`);
}

// Handle metrics reset
function handleReset() {
  state.ui.isFirstEvent = true;
  state.ui.lastBlockedCount = 0;
  state.ui.newBlockedCount = 0;
  updateProgress(0);
  badges.clearEvents();

  if (el.eventFeed) el.eventFeed.innerHTML = '<div class="empty-state">Events will appear when simulation starts</div>';
  if (el.explanationPanel) el.explanationPanel.innerHTML = '<div class="empty-state">Select an event to view analysis</div>';
  if (el.riskyActors) el.riskyActors.innerHTML = '<div class="empty-state">No data available</div>';
  if (el.eventCountBadge) el.eventCountBadge.textContent = '0 events';
  if (el.ksqldbSummaries) el.ksqldbSummaries.classList.add('hidden');
  if (el.ksqldbPlaceholder) el.ksqldbPlaceholder.classList.remove('hidden');

  setStatus('Ready');

  if (state.chart) {
    state.chart.data.labels = [];
    state.chart.data.datasets[0].data = [];
    state.chart.update();
  }
}

// Handle decision mode change
function handleDecisionModeChanged(data) {
  const radio = document.getElementById(`mode-${data.mode.replace('_', '-')}`);
  if (radio) radio.checked = true;
  updateDecisionStats(data.decision_stats);
}
