import type { Decision } from '@/types';

/**
 * Local sample corpus. Everything here is static and hand-written so the UI can
 * be exercised at realistic density before any analysis engine is wired up.
 */
export const decisions: Decision[] = [
  {
    id: 'dcn-4812',
    title: 'Leave staff engineering role to co-found a seed-stage startup',
    statement:
      'I have an offer to co-found a developer-tooling company with a former colleague. It means giving up a staff engineering position, unvested equity worth roughly $180k, and a predictable income for at least 24 months.',
    domain: 'career',
    status: 'analyzed',
    stakes: 'defining',
    createdAt: '2026-08-24T09:12:00.000Z',
    updatedAt: '2026-09-05T16:40:00.000Z',
    commitBy: '2026-09-19T00:00:00.000Z',
    analysis: {
      regretIndex: 68,
      analysisConfidence: 74,
      reversibility: 'costly-to-reverse',
      verdictSummary:
        'The decision is defensible on upside but rests on two untested assumptions: that your co-founder relationship survives disagreement about direction, and that you can re-enter the market at staff level if the company fails. Neither has been tested, and both are cheap to test.',
      assumptions: [
        {
          id: 'asm-1',
          statement: 'I can return to a staff-level role within three months if the company fails.',
          origin: 'hidden',
          confidence: 'medium',
          fragility: 72,
          evidence: 'anecdotal',
          impactIfWrong: 'high',
        },
        {
          id: 'asm-2',
          statement: 'My co-founder and I agree on what the company should become by year three.',
          origin: 'hidden',
          confidence: 'low',
          fragility: 84,
          evidence: 'none',
          impactIfWrong: 'critical',
        },
        {
          id: 'asm-3',
          statement: '24 months of runway is enough to reach a seed-to-Series-A signal.',
          origin: 'stated',
          confidence: 'medium',
          fragility: 58,
          evidence: 'partial',
          impactIfWrong: 'high',
        },
        {
          id: 'asm-4',
          statement: 'The forfeited equity will not vest into meaningful value anyway.',
          origin: 'stated',
          confidence: 'high',
          fragility: 31,
          evidence: 'documented',
          impactIfWrong: 'moderate',
        },
      ],
      blindSpots: [
        {
          id: 'bsp-1',
          title: 'Household financial tolerance is treated as fixed',
          description:
            'The framing covers your own risk appetite but never the household budget under a 24-month zero-salary scenario, including the cost of losing employer health coverage.',
          severity: 'high',
          probingQuestion:
            'What is the exact monthly burn your household can absorb before the decision reverses itself for you?',
        },
        {
          id: 'bsp-2',
          title: 'No stated definition of failure',
          description:
            'Without a pre-committed exit trigger, the likely outcome is extending runway past the point where re-entry is easy.',
          severity: 'critical',
          probingQuestion:
            'What observable result at month 12 would make you stop rather than raise a bridge?',
        },
        {
          id: 'bsp-3',
          title: 'Equity split and decision rights are unspecified',
          description:
            'Founder conflict rarely starts over the split itself; it starts over who decides when the two of you disagree.',
          severity: 'high',
          probingQuestion: 'Who breaks a tie on product direction, and is that written down?',
        },
      ],
      failureConditions: [
        {
          id: 'fcd-1',
          trigger: 'Co-founder disagreement on target market surfaces after the first ten customers',
          mechanism:
            'Early customers pull the product toward a niche neither of you chose, forcing a direction call before revenue is defensible.',
          probability: 0.46,
          horizon: '1-year',
          severity: 'critical',
          earlyWarningSignal:
            'Two consecutive roadmap discussions ending without a written decision.',
        },
        {
          id: 'fcd-2',
          trigger: 'Seed round takes longer than four months to close',
          mechanism:
            'Runway assumptions collapse, and hiring freezes right when customer commitments require delivery.',
          probability: 0.38,
          horizon: '1-year',
          severity: 'high',
          earlyWarningSignal: 'Fewer than three partner meetings booked after twenty intro calls.',
        },
        {
          id: 'fcd-3',
          trigger: 'Senior-market hiring contracts while you are out of the workforce',
          mechanism:
            'Re-entry at staff level takes six to nine months instead of three, converting a recoverable failure into a compensation reset.',
          probability: 0.29,
          horizon: '3-years',
          severity: 'high',
          earlyWarningSignal:
            'Recruiter outreach for staff roles drops below one qualified approach per month.',
        },
      ],
      regretScenarios: [
        {
          id: 'rgs-1',
          horizon: '6-months',
          title: 'You miss the work, not the money',
          narrative:
            'The company is alive and the work is interesting, but you are doing sales and support instead of engineering. The regret is about craft, not income, and it fades once the first engineer is hired.',
          regretScore: 28,
          likelihood: 0.42,
          recoveryCost: 'reversible',
        },
        {
          id: 'rgs-2',
          horizon: '1-year',
          title: 'Direction conflict with no tie-breaker',
          narrative:
            'You and your co-founder want different companies. Without written decision rights the disagreement consumes a quarter, the seed round slips, and you look back at an avoidable structural gap.',
          regretScore: 81,
          likelihood: 0.34,
          recoveryCost: 'costly-to-reverse',
        },
        {
          id: 'rgs-3',
          horizon: '3-years',
          title: 'Re-entry costs more than expected',
          narrative:
            'The company winds down. Returning takes eight months and a level reset, and the forfeited equity turns out to have been worth more than modelled.',
          regretScore: 74,
          likelihood: 0.22,
          recoveryCost: 'costly-to-reverse',
        },
        {
          id: 'rgs-4',
          horizon: '5-years',
          title: 'You never tried and the window closed',
          narrative:
            'You stayed. The role is comfortable, the tooling market consolidated, and the specific opening you had with this specific co-founder never came back.',
          regretScore: 66,
          likelihood: 0.31,
          recoveryCost: 'irreversible',
        },
      ],
      trajectory: [
        { horizonMonths: 3, commitNow: 34, runExperiment: 22 },
        { horizonMonths: 6, commitNow: 48, runExperiment: 27 },
        { horizonMonths: 12, commitNow: 66, runExperiment: 35 },
        { horizonMonths: 24, commitNow: 71, runExperiment: 38 },
        { horizonMonths: 36, commitNow: 68, runExperiment: 33 },
        { horizonMonths: 60, commitNow: 59, runExperiment: 29 },
      ],
      recommendedExperimentId: 'exp-2201',
    },
  },
  {
    id: 'dcn-4790',
    title: 'Replace the self-hosted vector store with a managed service',
    statement:
      'Our self-hosted vector index is consuming about 30% of platform engineering time. Moving to a managed provider would free that capacity but adds roughly $4.2k/month and puts retrieval latency outside our control.',
    domain: 'technology',
    status: 'testing',
    stakes: 'high',
    createdAt: '2026-08-11T14:05:00.000Z',
    updatedAt: '2026-09-02T11:20:00.000Z',
    analysis: {
      regretIndex: 41,
      analysisConfidence: 81,
      reversibility: 'reversible',
      verdictSummary:
        'Low regret exposure because migration is reversible within a quarter. The real risk is not cost but the tail latency you cannot tune once retrieval lives behind someone else\u2019s API.',
      assumptions: [
        {
          id: 'asm-5',
          statement: 'Managed p99 retrieval latency stays under 180ms at our query volume.',
          origin: 'stated',
          confidence: 'low',
          fragility: 69,
          evidence: 'none',
          impactIfWrong: 'high',
        },
        {
          id: 'asm-6',
          statement: 'The freed platform capacity gets spent on roadmap work, not new toil.',
          origin: 'hidden',
          confidence: 'low',
          fragility: 77,
          evidence: 'anecdotal',
          impactIfWrong: 'moderate',
        },
        {
          id: 'asm-7',
          statement: 'Index rebuild cost stays flat as the corpus triples.',
          origin: 'hidden',
          confidence: 'medium',
          fragility: 54,
          evidence: 'partial',
          impactIfWrong: 'moderate',
        },
      ],
      blindSpots: [
        {
          id: 'bsp-4',
          title: 'Exit path is not costed',
          description:
            'Nothing in the plan covers what it takes to move back if pricing changes at renewal, which is when leverage is lowest.',
          severity: 'moderate',
          probingQuestion: 'How many engineer-weeks does it take to bring the index back in-house?',
        },
        {
          id: 'bsp-5',
          title: 'Data residency obligations unreviewed',
          description:
            'Two enterprise contracts specify regional storage; the managed provider default region has not been checked against them.',
          severity: 'high',
          probingQuestion:
            'Which existing contracts constrain where embeddings may physically live?',
        },
      ],
      failureConditions: [
        {
          id: 'fcd-4',
          trigger: 'Tail latency exceeds 300ms during peak retrieval',
          mechanism:
            'Answer quality degrades under timeout fallbacks, and the failure is invisible in average-latency dashboards.',
          probability: 0.33,
          horizon: '6-months',
          severity: 'high',
          earlyWarningSignal: 'p99 drifting above 220ms for three consecutive days.',
        },
        {
          id: 'fcd-5',
          trigger: 'Renewal pricing rises above in-house total cost',
          mechanism:
            'Switching costs have accumulated by then, so the increase is absorbed rather than contested.',
          probability: 0.27,
          horizon: '3-years',
          severity: 'moderate',
          earlyWarningSignal: 'Provider announcing usage-tier restructuring.',
        },
      ],
      regretScenarios: [
        {
          id: 'rgs-5',
          horizon: '6-months',
          title: 'Latency regression you cannot fix',
          narrative:
            'Retrieval is slower at the tail and the only lever is a support ticket. Engineers who used to tune the index now write escalations.',
          regretScore: 57,
          likelihood: 0.31,
          recoveryCost: 'reversible',
        },
        {
          id: 'rgs-6',
          horizon: '1-year',
          title: 'Capacity was reclaimed, then absorbed',
          narrative:
            'The 30% came back and quietly went into other operational work, so the roadmap never moved and the cost stayed.',
          regretScore: 44,
          likelihood: 0.39,
          recoveryCost: 'reversible',
        },
      ],
      trajectory: [
        { horizonMonths: 3, commitNow: 29, runExperiment: 19 },
        { horizonMonths: 6, commitNow: 41, runExperiment: 23 },
        { horizonMonths: 12, commitNow: 45, runExperiment: 24 },
        { horizonMonths: 24, commitNow: 43, runExperiment: 22 },
        { horizonMonths: 36, commitNow: 38, runExperiment: 21 },
        { horizonMonths: 60, commitNow: 34, runExperiment: 20 },
      ],
      recommendedExperimentId: 'exp-2204',
    },
  },
  {
    id: 'dcn-4771',
    title: 'Hire a VP of Sales before reaching $1M ARR',
    statement:
      'Two founders are still closing every deal. A VP of Sales candidate is available now at $220k base plus equity. We are at $640k ARR with an unclear repeatable motion.',
    domain: 'hiring',
    status: 'analyzed',
    stakes: 'high',
    createdAt: '2026-07-29T08:30:00.000Z',
    updatedAt: '2026-08-28T13:15:00.000Z',
    commitBy: '2026-09-30T00:00:00.000Z',
    analysis: {
      regretIndex: 74,
      analysisConfidence: 69,
      reversibility: 'costly-to-reverse',
      verdictSummary:
        'The hire is being asked to discover a sales motion rather than scale one. That is the failure pattern: a leader optimised for scaling arrives before there is anything repeatable to scale, and the mis-hire costs three quarters to detect.',
      assumptions: [
        {
          id: 'asm-8',
          statement: 'A repeatable sales motion already exists and only needs a leader.',
          origin: 'hidden',
          confidence: 'low',
          fragility: 88,
          evidence: 'none',
          impactIfWrong: 'critical',
        },
        {
          id: 'asm-9',
          statement: 'Founder-led selling is now the binding constraint on growth.',
          origin: 'stated',
          confidence: 'medium',
          fragility: 61,
          evidence: 'partial',
          impactIfWrong: 'high',
        },
        {
          id: 'asm-10',
          statement: 'We can evaluate the hire fairly within two quarters.',
          origin: 'hidden',
          confidence: 'low',
          fragility: 74,
          evidence: 'anecdotal',
          impactIfWrong: 'high',
        },
      ],
      blindSpots: [
        {
          id: 'bsp-6',
          title: 'Win reasons are undocumented',
          description:
            'Nobody has written down why the last fifteen deals closed, so any incoming leader inherits intuition instead of a playbook.',
          severity: 'critical',
          probingQuestion: 'What did the last fifteen won deals have in common?',
        },
        {
          id: 'bsp-7',
          title: 'Founder time does not actually free up',
          description:
            'Early sales leaders need heavy founder involvement for the first two quarters, so the expected time saving inverts before it appears.',
          severity: 'high',
          probingQuestion: 'How many founder hours per week will onboarding this leader consume?',
        },
      ],
      failureConditions: [
        {
          id: 'fcd-6',
          trigger: 'No closed-won deal sourced independently of the founders by month six',
          mechanism:
            'The leader cannot build a pipeline without a defined motion, and attribution disputes delay the decision to part ways.',
          probability: 0.52,
          horizon: '6-months',
          severity: 'critical',
          earlyWarningSignal: 'Founder attendance still required on every second-stage call.',
        },
        {
          id: 'fcd-7',
          trigger: 'Two account executives are hired under an unproven playbook',
          mechanism:
            'Burn triples while conversion stays flat, converting a single mis-hire into a team-shaped commitment.',
          probability: 0.41,
          horizon: '1-year',
          severity: 'critical',
          earlyWarningSignal: 'Ramp plans written before any documented win pattern exists.',
        },
      ],
      regretScenarios: [
        {
          id: 'rgs-7',
          horizon: '6-months',
          title: 'Expensive discovery',
          narrative:
            'Two quarters in, the leader is still learning the market and the founders are still closing. Cash burned buys knowledge the founders already had.',
          regretScore: 69,
          likelihood: 0.44,
          recoveryCost: 'costly-to-reverse',
        },
        {
          id: 'rgs-8',
          horizon: '1-year',
          title: 'Team built on an unproven motion',
          narrative:
            'The org grew around a playbook that never validated. Unwinding it costs relationships, severance, and the next fundraise narrative.',
          regretScore: 88,
          likelihood: 0.27,
          recoveryCost: 'irreversible',
        },
      ],
      trajectory: [
        { horizonMonths: 3, commitNow: 41, runExperiment: 24 },
        { horizonMonths: 6, commitNow: 69, runExperiment: 31 },
        { horizonMonths: 12, commitNow: 82, runExperiment: 36 },
        { horizonMonths: 24, commitNow: 77, runExperiment: 34 },
        { horizonMonths: 36, commitNow: 70, runExperiment: 30 },
        { horizonMonths: 60, commitNow: 62, runExperiment: 28 },
      ],
      recommendedExperimentId: 'exp-2206',
    },
  },
  {
    id: 'dcn-4756',
    title: 'Move from usage-based pricing to per-seat pricing',
    statement:
      'Usage-based billing makes revenue unpredictable and procurement conversations slow. Per-seat pricing is easier to forecast but penalises our highest-volume automation customers.',
    domain: 'business-model',
    status: 'analyzing',
    stakes: 'high',
    createdAt: '2026-09-01T10:45:00.000Z',
    updatedAt: '2026-09-07T09:05:00.000Z',
    commitBy: '2026-10-15T00:00:00.000Z',
  },
  {
    id: 'dcn-4743',
    title: 'Consolidate the engineering team into a single Lisbon hub',
    statement:
      'We are distributed across nine time zones. Consolidating into one hub would improve delivery cadence but would likely cost us four of our eleven engineers.',
    domain: 'relocation',
    status: 'draft',
    stakes: 'defining',
    createdAt: '2026-09-06T18:20:00.000Z',
    updatedAt: '2026-09-06T18:20:00.000Z',
  },
  {
    id: 'dcn-4698',
    title: 'Sunset the free tier',
    statement:
      'The free tier drives 71% of signups and 4% of revenue, and consumes most of the support load. Removing it simplifies the funnel but ends our strongest acquisition channel.',
    domain: 'product',
    status: 'committed',
    stakes: 'moderate',
    createdAt: '2026-06-17T12:00:00.000Z',
    updatedAt: '2026-07-22T15:30:00.000Z',
  },
  {
    id: 'dcn-4655',
    title: 'Take a $2M bridge round at flat valuation',
    statement:
      'A bridge extends runway by ten months without a priced round, but it signals weakness to the next lead investor and dilutes the founding team before the metrics recover.',
    domain: 'financial',
    status: 'abandoned',
    stakes: 'high',
    createdAt: '2026-05-04T09:00:00.000Z',
    updatedAt: '2026-06-02T17:45:00.000Z',
  },
];

export function findDecision(id: string): Decision | undefined {
  return decisions.find((decision) => decision.id === id);
}
