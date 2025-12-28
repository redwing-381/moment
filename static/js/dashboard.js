/**
 * AI Risk Gatekeeper - Dashboard JavaScript
 * Real-time security monitoring dashboard
 */

// ============================================
// State Management
// ============================================
const appState = {
  // WebSocket connection
  ws: null,
  reconnectAttempts: 0,
  maxReconnectAttempts: 10,
  
  // Metrics
  metrics: {
    events_produced: 0,
    decisions_made: 0,
    blocked: 0,
    allowed: 0,
    escalated: 0,
    throttled: 0,
    avg_latency_ms: 0
  },
  
  // Kafka metrics
  kafka: {
    messages_sent: 0,
    messages_per_sec: 0,
    connection_status: 'connecting'
  },
  
  // Confluent status
  confluent: {
    schema_registry: { connected: false, format: 'JSON' },
    ksqldb: { connected: false, streams_ready: false },
    metrics_api: { connected: false, cluster_id: null }
  },
  
  // Simulation state
  simulation: {
    running: false,
    progress: 0,
    scenarioName: null
  },
  
  // UI state
  ui: {
    isFirstEvent: true,
    lastBlockedCount: 0,
    soundEnabled: localStorage.getItem('soundEnabled') !== 'false',
    lastAlertTime: 0,
    alertThrottleMs: 500
  },
  
  // Chart instance
  riskChart: null,
  
  // Audio context
  audioContext: null
};

// ============================================
// DOM Elements Cache
// ============================================
const elements = {
  // Metrics
  metricEvents: null,
  metricDecisions: null,
  metricAllowed: null,
  metricThrottled: null,
  metricEscalated: null,
  metricBlocked: null,
  metricLatency: null,
  blockedCard: null,
  
  // Kafka
  kafkaStatus: null,
  kafkaMessages: null,
  kafkaRate: null,
  
  // Confluent
  srStatus: null,
  srFormat: null,
  ksqlStatus: null,
  ksqlStreams: null,
  metricsApiStatus: null,
  clusterId: null,
  fullIntegrationBadge: null,
  
  // Controls
  btnStart: null,
  btnStop: null,
  btnReset: null,
  btnExport: null,
  eventCount: null,
  eventCountVal: null,
  attackPct: null,
  attackPctVal: null,
  duration: null,
  durationVal: null,
  useAi: null,
  
  // Scenario buttons
  btnInsider: null,
  btnBruteforce: null,
  btnExfiltration: null,
  
  // Display areas
  eventFeed: null,
  explanationPanel: null,
  riskyActors: null,
  progressBar: null,
  statusText: null,
  soundToggle: null,
  riskChart: null,
  
  // ksqlDB
  ksqldbPlaceholder: null,
  ksqldbSummaries: null,
  ksqldbTableBody: null
};

// ============================================
// Initialization
// ============================================
function initializeApp() {
  cacheElements();
  initChart();
  initAudio();
  initEventListeners();
  connect();
  updateSoundToggle();
}

function cacheElements() {
  // Metrics
  elements.metricEvents = document.getElementById('metric-events');
  elements.metricDecisions = document.getElementById('metric-decisions');
  elements.metricAllowed = document.getElementById('metric-allowed');
  elements.metricThrottled = document.getElementById('metric-throttled');
  elements.metricEscalated = document.getElementById('metric-escalated');
  elements.metricBlocked = document.getElementById('metric-blocked');
  elements.metricLatency = document.getElementById('metric-latency');
  elements.blockedCard = document.getElementById('blocked-card');
  
  // Kafka
  elements.kafkaStatus = document.getElementById('kafka-status');
  elements.kafkaMessages = document.getElementById('kafka-messages');
  elements.kafkaRate = document.getElementById('kafka-rate');
  
  // Confluent
  elements.srStatus = document.getElementById('sr-status');
  elements.srFormat = document.getElementById('sr-format');
  elements.ksqlStatus = document.getElementById('ksql-status');
  elements.ksqlStreams = document.getElementById('ksql-streams');
  elements.metricsApiStatus = document.getElementById('metrics-api-status');
  elements.clusterId = document.getElementById('cluster-id');
  elements.fullIntegrationBadge = document.getElementById('full-integration-badge');
  
  // Controls
  elements.btnStart = document.getElementById('btn-start');
  elements.btnStop = document.getElementById('btn-stop');
  elements.btnReset = document.getElementById('btn-reset');
  elements.btnExport = document.getElementById('btn-export');
  elements.eventCount = document.getElementById('event-count');
  elements.eventCountVal = document.getElementById('event-count-val');
  elements.attackPct = document.getElementById('attack-pct');
  elements.attackPctVal = document.getElementById('attack-pct-val');
  elements.duration = document.getElementById('duration');
  elements.durationVal = document.getElementById('duration-val');
  elements.useAi = document.getElementById('use-ai');
  
  // Scenario buttons
  elements.btnInsider = document.getElementById('btn-insider');
  elements.btnBruteforce = document.getElementById('btn-bruteforce');
  elements.btnExfiltration = document.getElementById('btn-exfiltration');
  
  // Display areas
  elements.eventFeed = document.getElementById('event-feed');
  elements.explanationPanel = document.getElementById('explanation-panel');
  elements.riskyActors = document.getElementById('risky-actors');
  elements.progressBar = document.getElementById('progress-bar');
  elements.statusText = document.getElementById('status-text');
  elements.soundToggle = document.getElementById('sound-toggle');
  elements.riskChart = document.getElementById('risk-chart');
  
  // ksqlDB
  elements.ksqldbPlaceholder = document.getElementById('ksqldb-placeholder');
  elements.ksqldbSummaries = document.getElementById('ksqldb-summaries');
  elements.ksqldbTableBody = document.getElementById('ksqldb-table-body');
}


// ============================================
// WebSocket Connection
// ============================================
function connect() {
  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
  appState.ws = new WebSocket(`${protocol}//${window.location.host}/ws`);
  
  appState.ws.onopen = () => {
    appState.reconnectAttempts = 0;
    updateStatusText('Connected to server');
    updateConnectionIndicator('connected');
  };
  
  appState.ws.onmessage = (event) => {
    const data = JSON.parse(event.data);
    handleMessage(data);
  };
  
  appState.ws.onclose = () => {
    updateStatusText('Disconnected. Reconnecting...');
    updateConnectionIndicator('disconnected');
    scheduleReconnect();
  };
  
  appState.ws.onerror = (error) => {
    console.error('WebSocket error:', error);
    updateConnectionIndicator('error');
  };
}

function scheduleReconnect() {
  if (appState.reconnectAttempts < appState.maxReconnectAttempts) {
    const delay = Math.min(1000 * Math.pow(2, appState.reconnectAttempts), 30000);
    appState.reconnectAttempts++;
    setTimeout(connect, delay);
  } else {
    updateStatusText('Connection failed. Please refresh the page.');
  }
}

function sendMessage(message) {
  if (appState.ws && appState.ws.readyState === WebSocket.OPEN) {
    appState.ws.send(JSON.stringify(message));
  }
}

function updateConnectionIndicator(status) {
  // Could add a visual connection indicator here
}

// ============================================
// Message Handlers
// ============================================
function handleMessage(data) {
  switch (data.type) {
    case 'metrics':
      handleMetricsUpdate(data);
      break;
    case 'event_processed':
      handleEventProcessed(data);
      break;
    case 'simulation_started':
      handleSimulationStarted(data);
      break;
    case 'simulation_complete':
      handleSimulationComplete();
      break;
    case 'scenario_started':
      handleScenarioStarted(data);
      break;
    case 'scenario_complete':
      handleScenarioComplete(data);
      break;
    case 'metrics_reset':
      handleMetricsReset();
      break;
    case 'error':
      handleError(data);
      break;
  }
}

function handleMetricsUpdate(data) {
  updateMetrics(data.data);
  updateKafkaMetrics(data.kafka);
  updateRiskChart(data.risk_trend);
  updateRiskyActors(data.top_actors);
  updateConfluentStatus(data.confluent_status);
  updateKsqlDBSummaries(data.ksqldb_summaries);
  
  if (data.progress !== undefined) {
    updateProgress(data.progress);
  }
  
  if (data.scenario_name) {
    updateStatusText(`Running: ${data.scenario_name}`);
  }
}

function handleEventProcessed(data) {
  addEventToFeed(data);
}

function handleSimulationStarted(data) {
  appState.simulation.running = true;
  appState.ui.isFirstEvent = true;
  
  if (elements.btnStart) elements.btnStart.classList.add('hidden');
  if (elements.btnStop) elements.btnStop.classList.remove('hidden');
  
  updateStatusText(`Processing ${data.total_events} events...`);
}

function handleSimulationComplete() {
  appState.simulation.running = false;
  
  if (elements.btnStart) elements.btnStart.classList.remove('hidden');
  if (elements.btnStop) elements.btnStop.classList.add('hidden');
  if (elements.btnExport) elements.btnExport.disabled = false;
  
  updateProgress(100);
  updateStatusText('Simulation complete!');
}

function handleScenarioStarted(data) {
  appState.simulation.running = true;
  appState.simulation.scenarioName = data.scenario.name;
  appState.ui.isFirstEvent = true;
  
  if (elements.btnStart) elements.btnStart.classList.add('hidden');
  if (elements.btnStop) elements.btnStop.classList.remove('hidden');
  
  updateStatusText(`${data.scenario.icon} Running: ${data.scenario.name}`);
}

function handleScenarioComplete(data) {
  appState.simulation.running = false;
  appState.simulation.scenarioName = null;
  
  if (elements.btnStart) elements.btnStart.classList.remove('hidden');
  if (elements.btnStop) elements.btnStop.classList.add('hidden');
  if (elements.btnExport) elements.btnExport.disabled = false;
  
  updateProgress(100);
  
  const summary = data.summary;
  updateStatusText(
    `✅ ${data.scenario} complete! Blocked ${summary.blocked}/${summary.expected_blocks} threats (${summary.detection_rate}% detection)`
  );
}

function handleMetricsReset() {
  appState.ui.isFirstEvent = true;
  appState.ui.lastBlockedCount = 0;
  
  updateProgress(0);
  
  if (elements.eventFeed) {
    elements.eventFeed.innerHTML = '<p class="text-muted text-center p-lg">Events will appear here when simulation starts...</p>';
  }
  
  if (elements.explanationPanel) {
    elements.explanationPanel.innerHTML = '<p class="text-muted text-center p-lg">Click on an event to see the AI\'s reasoning...</p>';
  }
  
  if (elements.riskyActors) {
    elements.riskyActors.innerHTML = '<p class="text-muted text-center p-md">No data yet...</p>';
  }
  
  if (elements.ksqldbSummaries) elements.ksqldbSummaries.classList.add('hidden');
  if (elements.ksqldbPlaceholder) elements.ksqldbPlaceholder.classList.remove('hidden');
  
  updateStatusText('Ready to simulate');
  
  // Reset chart
  if (appState.riskChart) {
    appState.riskChart.data.labels = [];
    appState.riskChart.data.datasets[0].data = [];
    appState.riskChart.update();
  }
}

function handleError(data) {
  console.error('Server error:', data.message);
  updateStatusText(`Error: ${data.message}`);
}


// ============================================
// Chart Management
// ============================================
function initChart() {
  const ctx = elements.riskChart?.getContext('2d');
  if (!ctx) return;
  
  appState.riskChart = new Chart(ctx, {
    type: 'line',
    data: {
      labels: [],
      datasets: [{
        label: 'Risk Score',
        data: [],
        borderColor: '#3b82f6',
        backgroundColor: 'rgba(59, 130, 246, 0.1)',
        fill: true,
        tension: 0.4,
        pointRadius: 2,
        pointHoverRadius: 5,
        borderWidth: 2
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      interaction: {
        intersect: false,
        mode: 'index'
      },
      scales: {
        y: {
          beginAtZero: true,
          max: 1,
          grid: {
            color: 'rgba(255, 255, 255, 0.05)',
            drawBorder: false
          },
          ticks: {
            color: '#94a3b8',
            font: { size: 11 },
            callback: (value) => `${(value * 100).toFixed(0)}%`
          }
        },
        x: {
          display: false,
          grid: { display: false }
        }
      },
      plugins: {
        legend: { display: false },
        tooltip: {
          backgroundColor: '#1e293b',
          titleColor: '#f8fafc',
          bodyColor: '#cbd5e1',
          borderColor: 'rgba(255, 255, 255, 0.1)',
          borderWidth: 1,
          padding: 12,
          displayColors: false,
          callbacks: {
            label: (context) => `Risk: ${(context.raw * 100).toFixed(0)}%`
          }
        }
      },
      animation: { duration: 0 }
    }
  });
}

function updateRiskChart(riskTrend) {
  if (!riskTrend || !appState.riskChart) return;
  
  const labels = riskTrend.map((_, i) => i);
  const data = riskTrend.map(r => r.risk_score);
  
  appState.riskChart.data.labels = labels;
  appState.riskChart.data.datasets[0].data = data;
  
  // Update color based on average risk
  const avgRisk = data.length > 0 ? data.reduce((a, b) => a + b, 0) / data.length : 0;
  
  if (avgRisk >= 0.6) {
    appState.riskChart.data.datasets[0].borderColor = '#ef4444';
    appState.riskChart.data.datasets[0].backgroundColor = 'rgba(239, 68, 68, 0.1)';
  } else if (avgRisk >= 0.4) {
    appState.riskChart.data.datasets[0].borderColor = '#f59e0b';
    appState.riskChart.data.datasets[0].backgroundColor = 'rgba(245, 158, 11, 0.1)';
  } else {
    appState.riskChart.data.datasets[0].borderColor = '#22c55e';
    appState.riskChart.data.datasets[0].backgroundColor = 'rgba(34, 197, 94, 0.1)';
  }
  
  appState.riskChart.update();
}

// ============================================
// UI Update Functions
// ============================================
function updateMetrics(metrics) {
  if (!metrics) return;
  
  animateValue(elements.metricEvents, appState.metrics.events_produced, metrics.events_produced);
  animateValue(elements.metricDecisions, appState.metrics.decisions_made, metrics.decisions_made);
  animateValue(elements.metricAllowed, appState.metrics.allowed, metrics.allowed);
  animateValue(elements.metricThrottled, appState.metrics.throttled, metrics.throttled);
  animateValue(elements.metricEscalated, appState.metrics.escalated, metrics.escalated);
  animateValue(elements.metricBlocked, appState.metrics.blocked, metrics.blocked);
  
  if (elements.metricLatency) {
    elements.metricLatency.textContent = metrics.avg_latency_ms.toFixed(1);
  }
  
  // Check for new blocks
  if (metrics.blocked > appState.ui.lastBlockedCount) {
    triggerBlockAlert();
    appState.ui.lastBlockedCount = metrics.blocked;
  }
  
  // Update state
  appState.metrics = { ...metrics };
}

function animateValue(element, from, to) {
  if (!element || from === to) {
    if (element) element.textContent = to;
    return;
  }
  
  element.textContent = to;
  element.classList.add('count-up');
  setTimeout(() => element.classList.remove('count-up'), 200);
}

function updateKafkaMetrics(kafka) {
  if (!kafka) return;
  
  if (elements.kafkaMessages) {
    elements.kafkaMessages.textContent = kafka.messages_sent;
  }
  
  if (elements.kafkaRate) {
    elements.kafkaRate.textContent = kafka.messages_per_sec.toFixed(1);
  }
  
  if (elements.kafkaStatus) {
    const statusMap = {
      'connected': { text: 'Connected', class: 'badge-success' },
      'error': { text: 'Error', class: 'badge-error' },
      'connecting': { text: 'Connecting...', class: 'badge-warning' }
    };
    
    const status = statusMap[kafka.connection_status] || statusMap.connecting;
    elements.kafkaStatus.textContent = status.text;
    elements.kafkaStatus.className = `badge ${status.class}`;
  }
  
  appState.kafka = { ...kafka };
}

function updateConfluentStatus(status) {
  if (!status) return;
  
  // Schema Registry
  if (elements.srStatus) {
    if (status.schema_registry.connected) {
      elements.srStatus.textContent = 'Connected';
      elements.srStatus.className = 'badge badge-success';
    } else {
      elements.srStatus.textContent = 'Offline';
      elements.srStatus.className = 'badge badge-neutral';
    }
  }
  
  if (elements.srFormat) {
    elements.srFormat.textContent = status.schema_registry.format || 'Avro';
  }
  
  // ksqlDB
  if (elements.ksqlStatus) {
    if (status.ksqldb.connected) {
      elements.ksqlStatus.textContent = 'Connected';
      elements.ksqlStatus.className = 'badge badge-success';
    } else {
      elements.ksqlStatus.textContent = 'Offline';
      elements.ksqlStatus.className = 'badge badge-neutral';
    }
  }
  
  if (elements.ksqlStreams) {
    elements.ksqlStreams.textContent = status.ksqldb.streams_ready ? 'Streams Ready' : '-';
  }
  
  // Metrics API
  if (elements.metricsApiStatus) {
    if (status.metrics_api.connected) {
      elements.metricsApiStatus.textContent = 'Connected';
      elements.metricsApiStatus.className = 'badge badge-success';
    } else {
      elements.metricsApiStatus.textContent = 'Offline';
      elements.metricsApiStatus.className = 'badge badge-neutral';
    }
  }
  
  if (elements.clusterId) {
    elements.clusterId.textContent = status.metrics_api.cluster_id || '-';
  }
  
  // Full integration badge
  if (elements.fullIntegrationBadge) {
    const allConnected = status.schema_registry.connected && 
                         status.ksqldb.connected && 
                         status.metrics_api.connected;
    elements.fullIntegrationBadge.classList.toggle('hidden', !allConnected);
  }
  
  appState.confluent = { ...status };
}

function updateRiskyActors(actors) {
  if (!actors || actors.length === 0 || !elements.riskyActors) return;
  
  const medals = ['🥇', '🥈', '🥉', '•', '•'];
  
  elements.riskyActors.innerHTML = actors.map((actor, i) => {
    const riskClass = actor.avg_risk >= 0.6 ? 'high' : actor.avg_risk >= 0.4 ? 'medium' : 'low';
    return `
      <div class="actor-card">
        <div>
          <span class="actor-rank">${medals[i] || '•'}</span>
          <span class="actor-id">${actor.actor_id}</span>
          <div class="actor-stats">${actor.events} events, ${actor.blocked} blocked</div>
        </div>
        <div class="actor-risk">
          <div class="actor-risk-value ${riskClass}">${(actor.avg_risk * 100).toFixed(0)}%</div>
          <div class="actor-risk-label">avg risk</div>
        </div>
      </div>
    `;
  }).join('');
}

function updateKsqlDBSummaries(summaries) {
  if (!summaries || summaries.length === 0) return;
  
  if (elements.ksqldbPlaceholder) elements.ksqldbPlaceholder.classList.add('hidden');
  if (elements.ksqldbSummaries) elements.ksqldbSummaries.classList.remove('hidden');
  
  if (elements.ksqldbTableBody) {
    elements.ksqldbTableBody.innerHTML = summaries.map(s => {
      const riskClass = s.avg_risk >= 0.6 ? 'text-red' : s.avg_risk >= 0.4 ? 'text-yellow' : 'text-green';
      const flagged = s.is_flagged 
        ? '<span class="badge badge-error">🚨 Flagged</span>' 
        : '<span class="badge badge-success">✓ Normal</span>';
      
      return `
        <tr>
          <td class="font-mono">${s.actor_id}</td>
          <td class="numeric">${s.event_count}</td>
          <td class="numeric ${riskClass}">${(s.avg_risk * 100).toFixed(0)}%</td>
          <td class="numeric">${(s.max_risk * 100).toFixed(0)}%</td>
          <td class="numeric">${s.high_risk_count}</td>
          <td>${flagged}</td>
        </tr>
      `;
    }).join('');
  }
}

function updateProgress(progress) {
  if (elements.progressBar) {
    elements.progressBar.style.width = `${progress}%`;
  }
}

function updateStatusText(text) {
  if (elements.statusText) {
    elements.statusText.textContent = text;
  }
}


// ============================================
// Event Feed Management
// ============================================
function addEventToFeed(data) {
  if (!elements.eventFeed) return;
  
  if (appState.ui.isFirstEvent) {
    elements.eventFeed.innerHTML = '';
    appState.ui.isFirstEvent = false;
  }
  
  const decision = data.decision.decision;
  const decisionIcons = {
    'allow': '✅',
    'throttle': '⏱️',
    'escalate': '⚠️',
    'block': '🚫'
  };
  
  const card = document.createElement('div');
  card.className = `event-card ${decision}`;
  card.innerHTML = `
    <div class="event-header">
      <div>
        <span class="event-actor">${data.event.actor_id}</span>
        <span class="event-action">${data.event.action}</span>
      </div>
      <div class="event-decision">
        <span class="event-decision-icon">${decisionIcons[decision] || '❓'}</span>
        <span class="event-latency">${data.latency_ms}ms</span>
      </div>
    </div>
    <div class="event-details">
      Risk: ${(data.signal.risk_score * 100).toFixed(0)}% | 
      ${data.signal.risk_factors.slice(0, 2).join(', ') || 'No risk factors'}
    </div>
  `;
  
  card.addEventListener('click', () => showExplanation(data));
  
  // Auto-show explanation for blocked events
  if (decision === 'block') {
    showExplanation(data);
  }
  
  elements.eventFeed.insertBefore(card, elements.eventFeed.firstChild);
  
  // Limit feed size
  while (elements.eventFeed.children.length > 50) {
    elements.eventFeed.removeChild(elements.eventFeed.lastChild);
  }
}

function showExplanation(data) {
  if (!elements.explanationPanel) return;
  
  const decision = data.decision.decision;
  const decisionIcons = {
    'allow': '✅',
    'throttle': '⏱️',
    'escalate': '⚠️',
    'block': '🚫'
  };
  
  elements.explanationPanel.innerHTML = `
    <div class="explanation-header">
      <span style="font-size: 2rem;">${decisionIcons[decision]}</span>
      <span class="explanation-decision ${decision}">${decision.toUpperCase()}</span>
    </div>
    <div class="explanation-meta mb-md">
      Actor: <span class="font-mono">${data.event.actor_id}</span> | 
      Action: ${data.event.action} | 
      Latency: <span class="numeric">${data.latency_ms}ms</span>
    </div>
    <div class="explanation-content">
      <h4 class="mb-sm" style="color: var(--text-muted);">Analysis:</h4>
      <pre style="white-space: pre-wrap; font-family: inherit;">${data.explanation || 'No explanation available'}</pre>
    </div>
  `;
}

// ============================================
// Audio Alert System
// ============================================
function initAudio() {
  // Audio context will be created on first user interaction
}

function playAlertSound() {
  if (!appState.ui.soundEnabled) return;
  
  const now = Date.now();
  if (now - appState.ui.lastAlertTime < appState.ui.alertThrottleMs) return;
  appState.ui.lastAlertTime = now;
  
  try {
    if (!appState.audioContext) {
      appState.audioContext = new (window.AudioContext || window.webkitAudioContext)();
    }
    
    const oscillator = appState.audioContext.createOscillator();
    const gainNode = appState.audioContext.createGain();
    
    oscillator.connect(gainNode);
    gainNode.connect(appState.audioContext.destination);
    
    oscillator.frequency.value = 800;
    oscillator.type = 'sine';
    gainNode.gain.setValueAtTime(0.3, appState.audioContext.currentTime);
    gainNode.gain.exponentialRampToValueAtTime(0.01, appState.audioContext.currentTime + 0.2);
    
    oscillator.start(appState.audioContext.currentTime);
    oscillator.stop(appState.audioContext.currentTime + 0.2);
  } catch (e) {
    console.log('Audio not available');
  }
}

function toggleSound() {
  appState.ui.soundEnabled = !appState.ui.soundEnabled;
  localStorage.setItem('soundEnabled', appState.ui.soundEnabled);
  updateSoundToggle();
}

function updateSoundToggle() {
  if (elements.soundToggle) {
    elements.soundToggle.textContent = appState.ui.soundEnabled ? '🔊 Sound: ON' : '🔇 Sound: OFF';
  }
}

function triggerBlockAlert() {
  playAlertSound();
  
  // Visual flash
  document.body.classList.add('screen-flash');
  setTimeout(() => document.body.classList.remove('screen-flash'), 300);
  
  // Card animation
  if (elements.blockedCard) {
    elements.blockedCard.classList.add('block-flash', 'shake');
    setTimeout(() => {
      elements.blockedCard.classList.remove('block-flash', 'shake');
    }, 500);
  }
}

// ============================================
// Event Listeners
// ============================================
function initEventListeners() {
  // Slider value updates
  if (elements.eventCount) {
    elements.eventCount.addEventListener('input', (e) => {
      if (elements.eventCountVal) elements.eventCountVal.textContent = e.target.value;
    });
  }
  
  if (elements.attackPct) {
    elements.attackPct.addEventListener('input', (e) => {
      if (elements.attackPctVal) elements.attackPctVal.textContent = e.target.value;
    });
  }
  
  if (elements.duration) {
    elements.duration.addEventListener('input', (e) => {
      if (elements.durationVal) elements.durationVal.textContent = e.target.value;
    });
  }
  
  // Scenario buttons
  if (elements.btnInsider) {
    elements.btnInsider.addEventListener('click', () => runScenario('insider_threat'));
  }
  
  if (elements.btnBruteforce) {
    elements.btnBruteforce.addEventListener('click', () => runScenario('brute_force'));
  }
  
  if (elements.btnExfiltration) {
    elements.btnExfiltration.addEventListener('click', () => runScenario('data_exfiltration'));
  }
  
  // Control buttons
  if (elements.btnStart) {
    elements.btnStart.addEventListener('click', startSimulation);
  }
  
  if (elements.btnStop) {
    elements.btnStop.addEventListener('click', stopSimulation);
  }
  
  if (elements.btnReset) {
    elements.btnReset.addEventListener('click', resetMetrics);
  }
  
  if (elements.btnExport) {
    elements.btnExport.addEventListener('click', exportReport);
  }
  
  // Sound toggle
  if (elements.soundToggle) {
    elements.soundToggle.addEventListener('click', toggleSound);
  }
}

// ============================================
// Control Actions
// ============================================
function startSimulation() {
  sendMessage({
    action: 'start_simulation',
    event_count: parseInt(elements.eventCount?.value || 50),
    attack_percentage: parseInt(elements.attackPct?.value || 20),
    duration_seconds: parseInt(elements.duration?.value || 10),
    use_ai: elements.useAi?.checked || false
  });
}

function stopSimulation() {
  sendMessage({ action: 'stop_simulation' });
}

function resetMetrics() {
  sendMessage({ action: 'reset_metrics' });
  if (elements.btnExport) elements.btnExport.disabled = true;
}

function runScenario(scenarioId) {
  sendMessage({
    action: 'run_scenario',
    scenario_id: scenarioId,
    use_ai: elements.useAi?.checked || false
  });
}

async function exportReport() {
  try {
    const response = await fetch('/api/export-report');
    const data = await response.json();
    
    if (data.error) {
      alert(data.error);
      return;
    }
    
    // Create printable report
    const reportWindow = window.open('', '_blank');
    reportWindow.document.write(generateReportHTML(data));
    reportWindow.document.close();
    reportWindow.print();
  } catch (e) {
    alert('Failed to generate report: ' + e.message);
  }
}

function generateReportHTML(data) {
  return `
    <!DOCTYPE html>
    <html>
    <head>
      <title>AI Risk Gatekeeper - Security Report</title>
      <style>
        body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; padding: 40px; max-width: 800px; margin: 0 auto; color: #1f2937; }
        h1 { color: #1e40af; border-bottom: 2px solid #1e40af; padding-bottom: 10px; }
        h2 { color: #374151; margin-top: 30px; }
        .summary { display: grid; grid-template-columns: repeat(4, 1fr); gap: 15px; margin: 20px 0; }
        .stat { background: #f3f4f6; padding: 15px; border-radius: 8px; text-align: center; }
        .stat-value { font-size: 24px; font-weight: bold; color: #1e40af; }
        .stat-label { font-size: 12px; color: #6b7280; }
        .blocked { color: #dc2626; }
        table { width: 100%; border-collapse: collapse; margin: 20px 0; }
        th, td { border: 1px solid #e5e7eb; padding: 10px; text-align: left; }
        th { background: #f3f4f6; }
        .footer { margin-top: 40px; text-align: center; color: #9ca3af; font-size: 12px; }
        @media print { body { padding: 20px; } }
      </style>
    </head>
    <body>
      <h1>🛡️ AI Risk Gatekeeper - Security Report</h1>
      <p>Generated: ${new Date(data.generated_at).toLocaleString()}</p>
      
      <h2>Summary</h2>
      <div class="summary">
        <div class="stat"><div class="stat-value">${data.summary.total_events}</div><div class="stat-label">Total Events</div></div>
        <div class="stat"><div class="stat-value blocked">${data.summary.blocked}</div><div class="stat-label">Blocked</div></div>
        <div class="stat"><div class="stat-value">${data.summary.allowed}</div><div class="stat-label">Allowed</div></div>
        <div class="stat"><div class="stat-value">${data.summary.block_rate}%</div><div class="stat-label">Block Rate</div></div>
      </div>
      
      <h2>Top Risky Actors</h2>
      <table>
        <tr><th>Actor ID</th><th>Events</th><th>Blocked</th><th>Avg Risk</th></tr>
        ${data.top_risky_actors.map(a => 
          `<tr><td>${a.actor_id}</td><td>${a.events}</td><td>${a.blocked}</td><td>${(a.avg_risk * 100).toFixed(0)}%</td></tr>`
        ).join('')}
      </table>
      
      <h2>Recent Blocked Events</h2>
      <table>
        <tr><th>Actor</th><th>Action</th><th>Risk Score</th></tr>
        ${data.blocked_events.slice(0, 10).map(e => 
          `<tr><td>${e.actor_id}</td><td>${e.action}</td><td>${(e.risk_score * 100).toFixed(0)}%</td></tr>`
        ).join('')}
      </table>
      
      <div class="footer">
        <p>AI Risk Gatekeeper | Confluent Kafka + Google Vertex AI</p>
        <p>Avg Latency: ${data.summary.avg_latency_ms}ms</p>
      </div>
    </body>
    </html>
  `;
}

// ============================================
// Initialize on DOM Ready
// ============================================
document.addEventListener('DOMContentLoaded', initializeApp);
