/**
 * Moment Dashboard - Analytics Updates
 * Agent pipeline and architecture visualization
 */

import { el } from './state.js';

// Update agent pipeline stats
export function updateAgentPipeline(metrics, decisionStats) {
  if (!metrics) return;

  if (el.agentProducerStat) el.agentProducerStat.textContent = `${metrics.events_produced} events`;
  if (el.agentProcessorStat) el.agentProcessorStat.textContent = `${metrics.events_produced} signals`;
  if (el.agentDecisionStat) el.agentDecisionStat.textContent = `${metrics.decisions_made} decisions`;

  if (decisionStats && el.agentAiStat) {
    el.agentAiStat.textContent = `${decisionStats.ai_decisions || 0} queries`;
  }
}

// Update pipeline running status
export function updatePipelineStatus(running) {
  if (el.pipelineStatus) {
    el.pipelineStatus.textContent = running ? 'Processing' : 'Idle';
    el.pipelineStatus.className = `card-badge ${running ? 'success' : ''}`;
  }

  // Update agent status indicators
  const statuses = [el.agentProducerStatus, el.agentProcessorStatus, el.agentDecisionStatus];
  statuses.forEach(s => {
    if (s) s.className = `agent-status ${running ? 'active' : 'idle'}`;
  });

  // AI status depends on whether AI is being used
  if (el.agentAiStatus) {
    const useAi = document.getElementById('use-ai')?.checked;
    el.agentAiStatus.className = `agent-status ${running && useAi ? 'active' : 'idle'}`;
  }
}

// Update architecture visual
export function updateArchitecture(metrics, decisionMode) {
  if (!metrics) return;

  // Update counts
  if (el.archEventsCount) el.archEventsCount.textContent = metrics.events_produced;
  if (el.topicEventsCount) el.topicEventsCount.textContent = metrics.events_produced;
  if (el.topicSignalsCount) el.topicSignalsCount.textContent = metrics.events_produced;
  if (el.topicDecisionsCount) el.topicDecisionsCount.textContent = metrics.decisions_made;

  // Update decision counts
  if (el.archAllowCount) el.archAllowCount.textContent = metrics.allowed;
  if (el.archThrottleCount) el.archThrottleCount.textContent = metrics.throttled;
  if (el.archEscalateCount) el.archEscalateCount.textContent = metrics.escalated;
  if (el.archBlockCount) el.archBlockCount.textContent = metrics.blocked;

  // Update mode display
  if (el.archHybridMode && decisionMode) {
    const modeLabels = { fast: 'Fast', hybrid: 'Hybrid', full_ai: 'Full AI' };
    el.archHybridMode.textContent = modeLabels[decisionMode] || 'Hybrid';
  }
}

// Flash architecture flow lines
export function flashArchitectureFlow() {
  const flows = ['flow-1', 'flow-2', 'flow-3', 'flow-4'];
  flows.forEach((id, i) => {
    const flow = document.getElementById(id);
    if (flow) {
      setTimeout(() => {
        flow.classList.add('active');
        setTimeout(() => flow.classList.remove('active'), 300);
      }, i * 100);
    }
  });
}
