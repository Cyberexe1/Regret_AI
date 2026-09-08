import type { DecisionReport } from '@/types';

/* -------------------------------------------------------------------------- *
 * Worked report for the cloud kitchen decision.
 *
 * Hand-written and internally consistent: the assumption tally matches the
 * listed assumptions, the threshold in the chart matches the uncertainty card,
 * and the experiment cost matches `exp-2210` in data/experiments.ts.
 * -------------------------------------------------------------------------- */

const cloudKitchenReport: DecisionReport = {
  decisionId: 'dcn-5104',
  title: 'Start a cloud kitchen',
  statusLabel: 'Needs validation',
  riskLevel: 'medium',
  summary: 'The decision is viable only if several uncertain assumptions hold.',

  snapshot: [
    { label: 'Budget', value: '₹5,00,000' },
    { label: 'Timeline', value: '6 months' },
    { label: 'Risk tolerance', value: 'Balanced' },
    { label: 'Decision confidence', value: '68%', percentage: 68, tone: 'warning' },
  ],

  uncertainties: [
    {
      id: 'unc-1',
      rank: '01',
      title: 'Repeat customer rate',
      summary: 'Every projection in the plan depends on customers ordering more than once.',
      current: { label: 'Current estimate', value: '18–21%' },
      threshold: { label: 'Required threshold', value: '24%' },
      impact: 'high',
      confidence: 'low',
      detail: {
        whyItMatters:
          'Contribution margin only turns positive when acquisition is amortised over repeat orders. Below the threshold, every new customer has to be bought again, and the kitchen runs under break-even regardless of order volume.',
        evidence: [
          'Category benchmarks for the city sit at 18–21%, published by two aggregator reports',
          'No first-party data: nobody has paid for this menu twice without a discount',
          'Discount-led launch weeks systematically overstate early repeat rates',
        ],
        howToResolve:
          'Measure the second-order rate of the first 200 customers from a rented kitchen, with no promotional discount active after day three.',
      },
    },
    {
      id: 'unc-2',
      rank: '02',
      title: 'Customer acquisition cost',
      summary: 'Paid placement is the only reliable discovery channel at launch.',
      current: { label: 'Current estimate', value: '₹180–₹240' },
      threshold: { label: 'Maximum sustainable', value: '₹210' },
      impact: 'high',
      confidence: 'low',
      detail: {
        whyItMatters:
          'The upper end of the current estimate already exceeds what the unit economics can carry. If acquisition settles above ₹210, the model needs a higher repeat rate to survive, compounding the first uncertainty rather than offsetting it.',
        evidence: [
          'Two comparable launches in the same catchment reported ₹195 and ₹240',
          'Aggregator ad auction pricing is seasonal and was sampled in a low month',
          'No organic discovery baseline has been measured',
        ],
        howToResolve:
          'Run a listing-only test with zero paid spend to establish the organic baseline, then price paid acquisition against it.',
      },
    },
    {
      id: 'unc-3',
      rank: '03',
      title: 'Platform commission',
      summary: 'Commission is contractual but the effective rate moves with ranking and promotions.',
      current: { label: 'Current assumption', value: '25–30%' },
      threshold: { label: 'Modelled at', value: '22%' },
      impact: 'medium',
      confidence: 'medium',
      detail: {
        whyItMatters:
          'The plan models 22% while the observed range is 25–30% once mandatory promotions and ranking fees are included. A three-point gap moves break-even by roughly a percentage point of repeat rate.',
        evidence: [
          'Published commission schedule confirms a 22% base rate',
          'Operators report effective rates of 25–30% after promotional participation',
          'Ranking weight for new listings requires paid promotion in the first eight weeks',
        ],
        howToResolve:
          'Confirm the effective all-in rate for a new listing in writing, including promotional minimums for the first two months.',
      },
    },
    {
      id: 'unc-4',
      rank: '04',
      title: 'Kitchen capacity utilisation',
      summary: 'A single brand may not fill the kitchen during off-peak hours.',
      current: { label: 'Current assumption', value: '62% of capacity' },
      threshold: { label: 'Needed to justify rent', value: '55%' },
      impact: 'low',
      confidence: 'medium',
      detail: {
        whyItMatters:
          'This one currently clears its threshold, so it is not driving the risk. It matters as a second-order effect: if repeat rate underperforms, utilisation falls with it and the rent becomes harder to carry.',
        evidence: [
          'Lease terms and equipment throughput are documented',
          'Off-peak demand in the catchment has not been sampled directly',
        ],
        howToResolve: 'Track hourly order distribution during the same pilot; no separate test needed.',
      },
    },
  ],

  threshold: {
    metricLabel: 'Repeat customer rate',
    valueLabel: 'Expected monthly contribution',
    narrative:
      'If repeat customer rate stays below 24%, the business model becomes significantly harder to sustain.',
    currentRange: [18, 21],
    thresholdValue: 24,
    domain: [14, 32],
    breakEvenRate: 22,
    curve: [
      { rate: 14, contribution: -58_000 },
      { rate: 16, contribution: -44_000 },
      { rate: 18, contribution: -30_000 },
      { rate: 20, contribution: -16_000 },
      { rate: 22, contribution: 0 },
      { rate: 24, contribution: 16_000 },
      { rate: 26, contribution: 33_000 },
      { rate: 28, contribution: 50_000 },
      { rate: 30, contribution: 68_000 },
      { rate: 32, contribution: 86_000 },
    ],
  },

  scenarios: [
    {
      id: 'scn-base',
      kind: 'base',
      title: 'Base case',
      description: 'Business reaches moderate profitability.',
      probability: 45,
      impact: 'medium',
      trigger: 'Repeat rate settles at 24–26% and acquisition holds near ₹200.',
      tone: 'info',
    },
    {
      id: 'scn-failure',
      kind: 'failure',
      title: 'Failure case',
      description:
        'Acquisition remains expensive and repeat customers stay below threshold.',
      probability: 35,
      impact: 'high',
      trigger: 'Second-order rate under 22% once launch discounts end.',
      tone: 'danger',
    },
    {
      id: 'scn-upside',
      kind: 'upside',
      title: 'Upside case',
      description: 'Retention exceeds threshold and acquisition costs decline.',
      probability: 20,
      impact: 'high',
      trigger: 'Repeat rate above 27% with organic orders covering a third of volume.',
      tone: 'success',
    },
  ],

  assumptions: [
    {
      id: 'rasm-1',
      statement: 'At least 24% of first-time customers order again within 30 days.',
      support: 'unsupported',
      note: 'Drawn from category benchmarks. No first-party evidence exists.',
    },
    {
      id: 'rasm-2',
      statement: 'Customer acquisition cost stays at or below ₹210.',
      support: 'uncertain',
      note: 'Comparable launches straddle the threshold at ₹195 and ₹240.',
    },
    {
      id: 'rasm-3',
      statement: 'Effective platform commission stays near the 22% base rate.',
      support: 'uncertain',
      note: 'Base rate is documented; the effective rate after promotions is not.',
    },
    {
      id: 'rasm-4',
      statement: 'Kitchen rent and fit-out total ₹5,00,000 with no overrun.',
      support: 'supported',
      note: 'Two written quotes and a signed lease term sheet on file.',
    },
    {
      id: 'rasm-5',
      statement: 'Break-even requires roughly 42 orders a day.',
      support: 'supported',
      note: 'Derived from the cost model and consistent under both commission rates.',
    },
    {
      id: 'rasm-6',
      statement: 'Food cost stays at 32% of order value.',
      support: 'supported',
      note: 'Based on current supplier pricing with a three-month rate lock.',
    },
    {
      id: 'rasm-7',
      statement: 'A single brand can fill 62% of kitchen capacity.',
      support: 'supported',
      note: 'Throughput documented; clears the 55% needed to justify rent.',
    },
  ],

  recommendation: {
    verdict: "Don't commit yet.",
    action:
      'Run a 14-day demand and retention pilot before investing the full ₹5,00,000.',
    costLabel: '₹15,000',
    expectedLearning: 'high',
    decisionImpact: 'high',
    ctaLabel: 'Design This Experiment',
  },
};

const reportsByDecisionId: Record<string, DecisionReport> = {
  [cloudKitchenReport.decisionId]: cloudKitchenReport,
};

/**
 * Only the cloud kitchen decision has a full report so far. Everything else
 * falls back to its analysis summary, rather than inventing a report for it.
 */
export function findDecisionReport(decisionId: string): DecisionReport | undefined {
  return reportsByDecisionId[decisionId];
}

/** Counts for the assumption summary, derived so they cannot drift from the list. */
export function summariseAssumptions(report: DecisionReport) {
  return {
    total: report.assumptions.length,
    supported: report.assumptions.filter((a) => a.support === 'supported').length,
    uncertain: report.assumptions.filter((a) => a.support === 'uncertain').length,
    unsupported: report.assumptions.filter((a) => a.support === 'unsupported').length,
  };
}
