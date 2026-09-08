import { useEffect, useMemo, useRef, useState } from 'react';
import {
  analysisAgents,
  analysisDurationMs,
  analysisFindings,
  analysisMetricSpecs,
  analysisStages,
  type AgentStatus,
  type AnalysisFinding,
  type AnalysisMetricSpec,
} from '@/data/analysisAgents';

const TICK_MS = 80;

interface Position {
  progress: number;
  /** Index of the running stage, or `analysisStages.length` once finished. */
  stageIndex: number;
}

/** Interpolates progress between the scripted checkpoints. */
function positionAt(elapsedMs: number): Position {
  let consumed = 0;

  for (let index = 0; index < analysisStages.length; index += 1) {
    const stage = analysisStages[index]!;

    if (elapsedMs < consumed + stage.durationMs) {
      const ratio = (elapsedMs - consumed) / stage.durationMs;
      const nextStart = analysisStages[index + 1]?.startProgress ?? 100;
      return {
        progress: stage.startProgress + (nextStart - stage.startProgress) * ratio,
        stageIndex: index,
      };
    }

    consumed += stage.durationMs;
  }

  return { progress: 100, stageIndex: analysisStages.length };
}

export interface ResolvedAnalysisMetric extends AnalysisMetricSpec {
  value: number;
  /** True once the counter has reached its final value. */
  settled: boolean;
}

export interface AnalysisSimulation {
  /** 0-100, rounded for display. */
  progress: number;
  isComplete: boolean;
  agentStatuses: Record<string, AgentStatus>;
  /** Findings released so far, in the order they appeared. */
  findings: AnalysisFinding[];
  metrics: ResolvedAnalysisMetric[];
  /** Agent currently working, or null when finished. */
  activeAgentId: string | null;
}

/**
 * Drives the local stress-test simulation from a single elapsed-time value, so
 * progress, agent status, findings and counters can never disagree.
 */
export function useAnalysisSimulation(): AnalysisSimulation {
  const [elapsed, setElapsed] = useState(0);
  const startedAt = useRef<number | null>(null);

  useEffect(() => {
    startedAt.current = Date.now();

    const interval = window.setInterval(() => {
      const start = startedAt.current;
      if (start === null) return;

      const next = Date.now() - start;

      if (next >= analysisDurationMs) {
        setElapsed(analysisDurationMs);
        window.clearInterval(interval);
        return;
      }

      setElapsed(next);
    }, TICK_MS);

    return () => window.clearInterval(interval);
  }, []);

  return useMemo(() => {
    const { progress, stageIndex } = positionAt(elapsed);
    const isComplete = stageIndex >= analysisStages.length;

    const agentStatuses = analysisAgents.reduce<Record<string, AgentStatus>>((acc, agent, index) => {
      acc[agent.id] = isComplete
        ? 'complete'
        : index < stageIndex
          ? 'complete'
          : index === stageIndex
            ? 'running'
            : 'waiting';
      return acc;
    }, {});

    const metrics = analysisMetricSpecs.map((spec) => {
      const ratio = Math.min(1, progress / spec.settlesAtProgress);
      return {
        ...spec,
        value: Math.round(spec.finalValue * ratio),
        settled: ratio >= 1,
      };
    });

    return {
      progress: Math.round(progress),
      isComplete,
      agentStatuses,
      findings: analysisFindings.filter((finding) => progress >= finding.atProgress),
      metrics,
      activeAgentId: isComplete ? null : (analysisAgents[stageIndex]?.id ?? null),
    };
  }, [elapsed]);
}
