/**
 * Moment - Dashboard
 */

// Router
const router = {
  current: 'dashboard',
  pages: ['dashboard', 'events', 'analytics', 'settings'],
  titles: {
    dashboard: 'Overview',
    events: 'Event Stream',
    analytics: 'Analytics',
    settings: 'Settings'
  },
  
  init() {
    window.addEventListener('hashchange', () => this.route());
    this.route();
  },
  
  route() {
    const hash = window.location.hash.slice(2) || 'dashboard';
    const page = this.pages.includes(hash) ? hash : 'dashboard';
    this.navigate(page, false);
  },
  
  navigate(page, updateHash = true) {
    if (!this.pages.includes(page)) return;
    if (updateHash) window.location.hash = `/${page}`;
    
    document.querySelectorAll('.page').forEach(p => p.classList.remove('active'));
    document.getElementById(`page-${page}`)?.classList.add('active');
    
    document.querySelectorAll('.nav-link').forEach(link => {
      link.classList.toggle('active', link.dataset.page === page);
    });
    
    document.getElementById('page-title').textContent = this.titles[page];
    
    if (page === 'events') badges.clearEvents();
    this.current = page;
    closeMobileMenu();
  }
};

// Badges
const badges = {
  events: 0,
  
  updateEvents(count) {
    this.events = count;
    const badge = document.getElementById('badge-events');
    if (badge) {
      if (count > 0 && router.current !== 'events') {
        badge.textContent = count > 99 ? '99+' : count;
        badge.classList.add('visible');
      } else {
        badge.classList.remove('visible');
      }
    }
  },
  
  clearEvents() {
    this.events = 0;
    document.getElementById('badge-events')?.classList.remove('visible');
  },
  
  updateAnalytics(connected) {
    const badge = document.getElementById('badge-analytics');
    if (badge) {
      badge.textContent = '✓';
      badge.classList.toggle('visible', connected);
      badge.classList.toggle('success-badge', connected);
    }
  },
  
  updateDashboard(running) {
    const badge = document.getElementById('badge-dashboard');
    if (badge) {
      badge.classList.toggle('visible', running);
      badge.classList.toggle('running-badge', running);
    }
  }
};

// State
const state = {
  ws: null,
  reconnectAttempts: 0,
  metrics: { events_produced: 0, decisions_made: 0, blocked: 0, allowed: 0, escalated: 0, throttled: 0, avg_latency_ms: 0 },
  kafka: { messages_sent: 0, messages_per_sec: 0, connection_status: 'connecting' },
  confluent: { schema_registry: { connected: false }, ksqldb: { connected: false }, metrics_api: { connected: false } },
  simulation: { running: false },
  ui: {
    soundEnabled: localStorage.getItem('soundEnabled') !== 'false',
    visualAlerts: localStorage.getItem('visualAlerts') !== 'false',
    lastBlockedCount: 0,
    newBlockedCount: 0,
    isFirstEvent: true
  },
  chart: null,
  audio: null
};

// Elements
const el = {};

function init() {
  cacheElements();
  router.init();
  initChart();
  initListeners();
  connect();
  updateSoundIcon();
}

function cacheElements() {
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
  
  // Settings
  el.settingSound = document.getElementById('setting-sound');
  el.settingVisual = document.getElementById('setting-visual');
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
  el.riskyActors = document.getElementById('risky-actors');
  el.riskChart = document.getElementById('risk-chart');
}

function initListeners() {
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
  
  // Init settings checkboxes
  if (el.settingSound) el.settingSound.checked = state.ui.soundEnabled;
  if (el.settingVisual) el.settingVisual.checked = state.ui.visualAlerts;
}

function toggleMobileMenu() {
  el.sidebar?.classList.toggle('open');
  el.mobileOverlay?.classList.toggle('active');
}

function closeMobileMenu() {
  el.sidebar?.classList.remove('open');
  el.mobileOverlay?.classList.remove('active');
}


// WebSocket
function connect() {
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

function send(msg) {
  if (state.ws?.readyState === WebSocket.OPEN) {
    state.ws.send(JSON.stringify(msg));
  }
}

function updateConnectionStatus(status) {
  if (el.connectionStatus) {
    el.connectionStatus.className = `connection-status ${status}`;
    el.connectionStatus.querySelector('.status-label').textContent = 
      status === 'connected' ? 'Connected' : status === 'disconnected' ? 'Disconnected' : 'Connecting';
  }
  
  if (el.wsStatus) {
    el.wsStatus.textContent = status === 'connected' ? 'Connected' : 'Disconnected';
    el.wsStatus.className = `status-badge ${status === 'connected' ? 'success' : 'danger'}`;
  }
}

// Message Handlers
function handleMessage(data) {
  switch (data.type) {
    case 'metrics': handleMetrics(data); break;
    case 'event_processed': handleEvent(data); break;
    case 'simulation_started': handleSimStart(data); break;
    case 'simulation_complete': handleSimComplete(); break;
    case 'scenario_started': handleScenarioStart(data); break;
    case 'scenario_complete': handleScenarioComplete(data); break;
    case 'metrics_reset': handleReset(); break;
    case 'error': console.error(data.message); break;
  }
}

function handleMetrics(data) {
  updateStats(data.data);
  updateKafka(data.kafka);
  updateChart(data.risk_trend);
  updateActors(data.top_actors);
  updateConfluent(data.confluent_status);
  updateKsqlDB(data.ksqldb_summaries);
  if (data.progress !== undefined) updateProgress(data.progress);
}

function handleEvent(data) {
  addEvent(data);
  if (el.eventCountBadge) {
    el.eventCountBadge.textContent = `${state.metrics.events_produced} events`;
  }
}

function handleSimStart(data) {
  state.simulation.running = true;
  state.ui.isFirstEvent = true;
  state.ui.newBlockedCount = 0;
  el.btnStart?.classList.add('hidden');
  el.btnStop?.classList.remove('hidden');
  badges.updateDashboard(true);
  setStatus(`Processing ${data.total_events} events...`);
}

function handleSimComplete() {
  state.simulation.running = false;
  el.btnStart?.classList.remove('hidden');
  el.btnStop?.classList.add('hidden');
  if (el.btnExport) el.btnExport.disabled = false;
  badges.updateDashboard(false);
  updateProgress(100);
  setStatus('Complete');
}

function handleScenarioStart(data) {
  state.simulation.running = true;
  state.ui.isFirstEvent = true;
  state.ui.newBlockedCount = 0;
  el.btnStart?.classList.add('hidden');
  el.btnStop?.classList.remove('hidden');
  badges.updateDashboard(true);
  setStatus(`Running: ${data.scenario.name}`);
}

function handleScenarioComplete(data) {
  state.simulation.running = false;
  el.btnStart?.classList.remove('hidden');
  el.btnStop?.classList.add('hidden');
  if (el.btnExport) el.btnExport.disabled = false;
  badges.updateDashboard(false);
  updateProgress(100);
  setStatus(`${data.scenario} - ${data.summary.detection_rate}% detection`);
}

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

// UI Updates
function updateStats(m) {
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
    if (router.current !== 'events') badges.updateEvents(state.ui.newBlockedCount);
    triggerAlert();
    state.ui.lastBlockedCount = m.blocked;
  }
  
  state.metrics = { ...m };
}

function setValue(el, val) {
  if (el && el.textContent !== String(val)) el.textContent = val;
}

function updateKafka(k) {
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

function updateConfluent(c) {
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

function updateStatusBadge(el, connected) {
  if (!el) return;
  el.textContent = connected ? 'Connected' : 'Offline';
  el.className = `status-badge ${connected ? 'success' : ''}`;
}

function updateActors(actors) {
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

function updateKsqlDB(summaries) {
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

function updateProgress(p) {
  if (el.progressBar) el.progressBar.style.width = `${p}%`;
}

function setStatus(text) {
  if (el.statusText) el.statusText.textContent = text;
}


// Event Feed
function addEvent(data) {
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
  if (d === 'block') showExplanation(data);
  
  el.eventFeed.insertBefore(item, el.eventFeed.firstChild);
  while (el.eventFeed.children.length > 50) el.eventFeed.removeChild(el.eventFeed.lastChild);
}

function showExplanation(data) {
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

// Chart
function initChart() {
  const ctx = el.riskChart?.getContext('2d');
  if (!ctx) return;
  
  state.chart = new Chart(ctx, {
    type: 'line',
    data: {
      labels: [],
      datasets: [{
        data: [],
        borderColor: '#6366f1',
        backgroundColor: 'rgba(99, 102, 241, 0.1)',
        fill: true,
        tension: 0.4,
        pointRadius: 0,
        borderWidth: 2
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      interaction: { intersect: false, mode: 'index' },
      scales: {
        y: {
          beginAtZero: true,
          max: 1,
          grid: { color: 'rgba(255,255,255,0.05)', drawBorder: false },
          ticks: { color: '#6b7280', callback: v => `${(v * 100).toFixed(0)}%` }
        },
        x: { display: false }
      },
      plugins: {
        legend: { display: false },
        tooltip: {
          backgroundColor: '#1f2937',
          titleColor: '#f3f4f6',
          bodyColor: '#9ca3af',
          borderColor: '#374151',
          borderWidth: 1,
          displayColors: false,
          callbacks: { label: ctx => `Risk: ${(ctx.raw * 100).toFixed(0)}%` }
        }
      },
      animation: { duration: 0 }
    }
  });
}

function updateChart(trend) {
  if (!trend || !state.chart) return;
  
  state.chart.data.labels = trend.map((_, i) => i);
  state.chart.data.datasets[0].data = trend.map(r => r.risk_score);
  
  const avg = trend.reduce((a, r) => a + r.risk_score, 0) / trend.length;
  const color = avg >= 0.6 ? '#ef4444' : avg >= 0.4 ? '#f59e0b' : '#10b981';
  state.chart.data.datasets[0].borderColor = color;
  state.chart.data.datasets[0].backgroundColor = color.replace(')', ', 0.1)').replace('rgb', 'rgba');
  
  state.chart.update();
}

// Audio
function toggleSound() {
  state.ui.soundEnabled = !state.ui.soundEnabled;
  localStorage.setItem('soundEnabled', state.ui.soundEnabled);
  updateSoundIcon();
  if (el.settingSound) el.settingSound.checked = state.ui.soundEnabled;
}

function updateSoundIcon() {
  el.soundToggle?.classList.toggle('muted', !state.ui.soundEnabled);
}

function playSound() {
  if (!state.ui.soundEnabled) return;
  try {
    if (!state.audio) state.audio = new (window.AudioContext || window.webkitAudioContext)();
    const osc = state.audio.createOscillator();
    const gain = state.audio.createGain();
    osc.connect(gain);
    gain.connect(state.audio.destination);
    osc.frequency.value = 800;
    gain.gain.setValueAtTime(0.2, state.audio.currentTime);
    gain.gain.exponentialRampToValueAtTime(0.01, state.audio.currentTime + 0.15);
    osc.start();
    osc.stop(state.audio.currentTime + 0.15);
  } catch (e) {}
}

function triggerAlert() {
  playSound();
  if (state.ui.visualAlerts && el.blockedCard) {
    el.blockedCard.classList.add('flash', 'shake');
    setTimeout(() => el.blockedCard.classList.remove('flash', 'shake'), 500);
  }
}

// Actions
function startSimulation() {
  send({
    action: 'start_simulation',
    event_count: parseInt(el.eventCount?.value || 50),
    attack_percentage: parseInt(el.attackPct?.value || 20),
    duration_seconds: parseInt(el.duration?.value || 10),
    use_ai: el.useAi?.checked || false
  });
}

function stopSimulation() {
  send({ action: 'stop_simulation' });
}

function resetMetrics() {
  send({ action: 'reset_metrics' });
  if (el.btnExport) el.btnExport.disabled = true;
}

function runScenario(id) {
  send({ action: 'run_scenario', scenario_id: id, use_ai: el.useAi?.checked || false });
}

async function exportReport() {
  try {
    const res = await fetch('/api/export-report');
    const data = await res.json();
    if (data.error) return alert(data.error);
    
    const win = window.open('', '_blank');
    win.document.write(`
      <!DOCTYPE html>
      <html>
      <head>
        <title>Security Report</title>
        <style>
          body { font-family: -apple-system, sans-serif; padding: 40px; max-width: 800px; margin: 0 auto; }
          h1 { color: #1f2937; border-bottom: 2px solid #6366f1; padding-bottom: 10px; }
          h2 { color: #374151; margin-top: 30px; }
          .stats { display: grid; grid-template-columns: repeat(4, 1fr); gap: 15px; margin: 20px 0; }
          .stat { background: #f3f4f6; padding: 15px; border-radius: 8px; text-align: center; }
          .stat-value { font-size: 24px; font-weight: bold; color: #6366f1; }
          .stat-label { font-size: 12px; color: #6b7280; }
          .blocked { color: #ef4444; }
          table { width: 100%; border-collapse: collapse; margin: 20px 0; }
          th, td { border: 1px solid #e5e7eb; padding: 10px; text-align: left; }
          th { background: #f3f4f6; }
        </style>
      </head>
      <body>
        <h1>Moment - Security Report</h1>
        <p>Generated: ${new Date(data.generated_at).toLocaleString()}</p>
        <div class="stats">
          <div class="stat"><div class="stat-value">${data.summary.total_events}</div><div class="stat-label">Events</div></div>
          <div class="stat"><div class="stat-value blocked">${data.summary.blocked}</div><div class="stat-label">Blocked</div></div>
          <div class="stat"><div class="stat-value">${data.summary.allowed}</div><div class="stat-label">Allowed</div></div>
          <div class="stat"><div class="stat-value">${data.summary.block_rate}%</div><div class="stat-label">Block Rate</div></div>
        </div>
        <h2>Top Risk Actors</h2>
        <table>
          <tr><th>Actor</th><th>Events</th><th>Blocked</th><th>Avg Risk</th></tr>
          ${data.top_risky_actors.map(a => `<tr><td>${a.actor_id}</td><td>${a.events}</td><td>${a.blocked}</td><td>${(a.avg_risk * 100).toFixed(0)}%</td></tr>`).join('')}
        </table>
      </body>
      </html>
    `);
    win.document.close();
    win.print();
  } catch (e) {
    alert('Export failed: ' + e.message);
  }
}

// Init
document.addEventListener('DOMContentLoaded', init);
