/**
 * Moment Dashboard - Element Cache
 * DOM element caching for performance
 */

import { el, setToastContainer } from './state.js';

// Cache all DOM elements
export function cacheElements() {
  // Stats
  el.metricEvents = document.getElementById('metric-events');
  el.metricDecisions = document.getElementById('metric-decisions');
  el.metricAllowed = document.getElementById('metric-allowed');
  el.metricThrottled = document.getElementById('metric-throttled');
  el.metricEscalated = document.getElementById('metric-escalated');
  el.metricBlocked = document.getElementById('metric-blocked');
  el.metricLatency = document.getElementById('metric-latency');
  el.blockedCard = document.getElementById('blocked-card');

  // Controls
  el.btnStart = document.getElementById('btn-start');
  el.btnStop = document.getElementById('btn-stop');
  el.btnReset = document.getElementById('btn-reset');
  el.btnExport = document.getElementById('btn-export');
  el.eventCount = document.getElementById('event-count');
  el.eventCountVal = document.getElementById('event-count-val');
  el.attackPct = document.getElementById('attack-pct');
  el.attackPctVal = document.getElementById('attack-pct-val');
  el.duration = document.getElementById('duration');
  el.durationVal = document.getElementById('duration-val');
  el.useAi = document.getElementById('use-ai');
  el.progressBar = document.getElementById('progress-bar');
  el.statusText = document.getElementById('status-text');

  // Scenarios
  el.btnInsider = document.getElementById('btn-insider');
  el.btnBruteforce = document.getElementById('btn-bruteforce');
  el.btnExfiltration = document.getElementById('btn-exfiltration');

  // Events
  el.eventFeed = document.getElementById('event-feed');
  el.eventCountBadge = document.getElementById('event-count-badge');
  el.explanationPanel = document.getElementById('explanation-panel');

  // Analytics
  el.srStatus = document.getElementById('sr-status');
  el.srFormat = document.getElementById('sr-format');
  el.ksqlStatus = document.getElementById('ksql-status');
  el.ksqlStreams = document.getElementById('ksql-streams');
  el.metricsApiStatus = document.getElementById('metrics-api-status');
  el.clusterId = document.getElementById('cluster-id');
  el.fullIntegrationBadge = document.getElementById('full-integration-badge');
  el.kafkaStatus = document.getElementById('kafka-status');
  el.kafkaMessages = document.getElementById('kafka-messages');
  el.kafkaRate = document.getElementById('kafka-rate');
  el.ksqldbPlaceholder = document.getElementById('ksqldb-placeholder');
  el.ksqldbSummaries = document.getElementById('ksqldb-summaries');
  el.ksqldbTableBody = document.getElementById('ksqldb-table-body');

  // Agent Pipeline
  el.pipelineStatus = document.getElementById('pipeline-status');
  el.agentProducerStat = document.getElementById('agent-producer-stat');
  el.agentProcessorStat = document.getElementById('agent-processor-stat');
  el.agentDecisionStat = document.getElementById('agent-decision-stat');
  el.agentAiStat = document.getElementById('agent-ai-stat');
  el.agentProducerStatus = document.getElementById('agent-producer-status');
  el.agentProcessorStatus = document.getElementById('agent-processor-status');
  el.agentDecisionStatus = document.getElementById('agent-decision-status');
  el.agentAiStatus = document.getElementById('agent-ai-status');

  // Architecture Visual
  el.archEventsCount = document.getElementById('arch-events-count');
  el.topicEventsCount = document.getElementById('topic-events-count');
  el.topicSignalsCount = document.getElementById('topic-signals-count');
  el.topicDecisionsCount = document.getElementById('topic-decisions-count');
  el.archHybridMode = document.getElementById('arch-hybrid-mode');
  el.archAllowCount = document.getElementById('arch-allow-count');
  el.archThrottleCount = document.getElementById('arch-throttle-count');
  el.archEscalateCount = document.getElementById('arch-escalate-count');
  el.archBlockCount = document.getElementById('arch-block-count');

  // Settings
  el.settingSound = document.getElementById('setting-sound');
  el.settingVisual = document.getElementById('setting-visual');
  el.settingTheme = document.getElementById('setting-theme');
  el.wsStatus = document.getElementById('ws-status');
  el.kafkaConnStatus = document.getElementById('kafka-conn-status');
  el.srConnStatus = document.getElementById('sr-conn-status');
  el.ksqlConnStatus = document.getElementById('ksql-conn-status');

  // Layout
  el.sidebar = document.getElementById('sidebar');
  el.menuToggle = document.getElementById('menu-toggle');
  el.mobileOverlay = document.getElementById('mobile-overlay');
  el.connectionStatus = document.getElementById('connection-status');
  el.soundToggle = document.getElementById('sound-toggle');
  el.themeToggle = document.getElementById('theme-toggle');
  el.riskyActors = document.getElementById('risky-actors');
  el.riskChart = document.getElementById('risk-chart');

  // Toast container
  setToastContainer(document.getElementById('toast-container'));
}
