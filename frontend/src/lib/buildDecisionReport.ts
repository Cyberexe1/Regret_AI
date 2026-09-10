import type { ApiAssumption, ApiBlindspot, ApiChallenge, ApiRegretScenario, ApiThreshold } from '@/api/types';
import type {
  CriticalUncertainty,
  ReportAssumptionRow,
  ReportChallenge,
  ReportScenario,
  ReportThreshold,
} from '@/types/report';
import {
  blindspotEvidenceStatusLabel,
  blindspotEvidenceStatusTone,
  confidenceLabel,
  confidencePercent,
  confidenceTone,
  evidenceStatusLabel,
  evidenceStatusTone,
  importanceLabel,
  importanceTone,
  severityTone,
  thresholdHasNumericValue,
  validationStatusLabel,
  validationStatusTone,
} from './reportModel';

/**
 * Builds the report's "critical uncertainties" list from real assumptions
 * and blindspots, ranked by importance (critical/high first) - a
 * deterministic sort, never a re-scoring. Ties are broken by lower
 * confidence first (the least-supported claim is more urgent to resolve).
 */
export function buildCriticalUncertainties(
  assumptions: ApiAssumption[],
  blindspots: ApiBlindspot[],
): CriticalUncertainty[] {
  const importanceWeight = (value: string | null) => {
    const lower = (value ?? '').toLowerCase();
    if (lower.includes('critical')) return 3;
    if (lower.includes('high')) return 2;
    if (lower.includes('medium') || lower.includes('moderate')) return 1;
    return 0;
  };

  const fromAssumptions: CriticalUncertainty[] = assumptions.map((assumption) => ({
    id: assumption.id,
    kind: 'assumption',
    rank: '',
    title: assumption.statement,
    importanceLabel: importanceLabel(assumption.importance),
    importanceTone: importanceTone(assumption.importance),
    confidenceLabel: confidenceLabel(assumption.confidence),
    confidenceTone: confidenceTone(assumption.confidence),
    confidencePercent: confidencePercent(assumption.confidence),
    evidenceStatusLabel: evidenceStatusLabel(assumption.evidence_status),
    evidenceStatusTone: evidenceStatusTone(assumption.evidence_status),
    reason: assumption.reason,
    dependency: assumption.dependency,
    failureConsequence: assumption.failure_consequence,
  }));

  const fromBlindspots: CriticalUncertainty[] = blindspots.map((blindspot) => ({
    id: blindspot.id,
    kind: 'blindspot',
    rank: '',
    title: blindspot.question,
    importanceLabel: importanceLabel(blindspot.importance),
    importanceTone: importanceTone(blindspot.importance),
    confidenceLabel: confidenceLabel(blindspot.confidence),
    confidenceTone: confidenceTone(blindspot.confidence),
    confidencePercent: confidencePercent(blindspot.confidence),
    evidenceStatusLabel: blindspotEvidenceStatusLabel(blindspot.evidence_status),
    evidenceStatusTone: blindspotEvidenceStatusTone(blindspot.evidence_status),
    whyItMatters: blindspot.why_it_matters,
    evidenceGap: blindspot.evidence_gap,
  }));

  const combined = [...fromAssumptions, ...fromBlindspots].sort((a, b) => {
    const byImportance = importanceWeight(b.importanceLabel) - importanceWeight(a.importanceLabel);
    if (byImportance !== 0) return byImportance;
    return (a.confidencePercent ?? 100) - (b.confidencePercent ?? 100);
  });

  return combined.map((item, index) => ({ ...item, rank: String(index + 1).padStart(2, '0') }));
}

export function buildReportScenarios(scenarios: ApiRegretScenario[]): ReportScenario[] {
  return scenarios.map((scenario) => ({
    id: scenario.id,
    title: scenario.title,
    failureCondition: scenario.failure_condition,
    probabilityBand: scenario.probability_band,
    impact: scenario.impact,
    impactTone: importanceTone(scenario.impact),
    regretLevel: scenario.regret_level,
    regretLevelTone: severityTone(scenario.regret_level),
    triggerVariable: scenario.trigger_variable,
    triggerDirection: scenario.trigger_direction,
    consequence: scenario.consequence,
    evidenceBasis: scenario.evidence_basis,
  }));
}

export function buildReportThresholds(thresholds: ApiThreshold[]): ReportThreshold[] {
  return thresholds.map((threshold) => ({
    id: threshold.id,
    variable: threshold.variable,
    unit: threshold.unit,
    direction: threshold.direction,
    thresholdValue: threshold.threshold_value,
    lowerBound: threshold.lower_bound,
    upperBound: threshold.upper_bound,
    hasNumericValue: thresholdHasNumericValue(threshold),
    validationStatusLabel: validationStatusLabel(threshold.validation_status),
    validationStatusTone: validationStatusTone(threshold.validation_status),
    confidencePercent: confidencePercent(threshold.confidence),
    consequence: threshold.consequence,
    derivation: threshold.derivation,
    evidenceBasis: threshold.evidence_basis,
  }));
}

export function buildReportAssumptionRows(assumptions: ApiAssumption[]): ReportAssumptionRow[] {
  return assumptions.map((assumption) => ({
    id: assumption.id,
    statement: assumption.statement,
    evidenceStatusLabel: evidenceStatusLabel(assumption.evidence_status),
    evidenceStatusTone: evidenceStatusTone(assumption.evidence_status),
    note: assumption.reason,
  }));
}

/** The Devil's Advocate's real, evidence-grounded attacks on the decision -
 * ranked by severity, then confidence, the same deterministic ordering
 * used for critical uncertainties above. */
export function buildReportChallenges(challenges: ApiChallenge[]): ReportChallenge[] {
  const severityWeight = (value: string | null) => {
    const lower = (value ?? '').toLowerCase();
    if (lower === 'critical') return 3;
    if (lower === 'high') return 2;
    if (lower === 'medium') return 1;
    return 0;
  };

  return [...challenges]
    .sort((a, b) => {
      const bySeverity = severityWeight(b.severity) - severityWeight(a.severity);
      if (bySeverity !== 0) return bySeverity;
      return (b.confidence ?? 0) - (a.confidence ?? 0);
    })
    .map((challenge) => ({
      id: challenge.id,
      claim: challenge.claim,
      attack: challenge.attack,
      severityLabel: importanceLabel(challenge.severity),
      severityTone: severityTone(challenge.severity),
      confidencePercent: confidencePercent(challenge.confidence),
      failureMechanism: challenge.failure_mechanism,
      evidenceBasis: challenge.evidence_basis,
    }));
}
