import type { Decision } from '@/types';

/**
 * Local sample corpus. Everything here is static and hand-written so the UI can
 * be exercised at realistic density before any analysis engine is wired up.
 */
export const decisions: Decision[] = [
  {
    id: 'dcn-5104',
    title: 'Start a cloud kitchen',
    statement:
      'Invest ₹5,00,000 to launch a single-brand cloud kitchen in Indiranagar, covering kitchen fit-out, three months of rent and initial marketing. Break-even needs roughly 42 orders a day.',
    domain: 'financial',
    status: 'analyzed',
    stakes: 'high',
    createdAt: '2026-09-02T07:30:00.000Z',
    updatedAt: '2026-09-08T06:15:00.000Z',
    commitBy: '2026-09-26T00:00:00.000Z',
    analysis: {
      regretIndex: 54,
      analysisConfidence: 68,
      reversibility: 'costly-to-reverse',
      verdictSummary:
        'The unit economics work only if customers order more than once. Every projection in the plan assumes a repeat rate of at least 24%, and the evidence available sits at 18–21%. That single number decides the outcome, and it can be measured for far less than ₹5,00,000.',
      assumptions: [
        {
          id: 'asm-11',
          statement: 'At least 24% of first-time customers order again within 30 days.',
          origin: 'hidden',
          confidence: 'low',
          fragility: 82,
          evidence: 'partial',
          impactIfWrong: 'critical',
        },
        {
          id: 'asm-12',
          statement: 'Aggregator commission stays at 22% through the first year.',
          origin: 'stated',
          confidence: 'medium',
          fragility: 61,
          evidence: 'documented',
          impactIfWrong: 'high',
        },
        {
          id: 'asm-13',
          statement: 'A single brand is enough to fill kitchen capacity.',
          origin: 'hidden',
          confidence: 'low',
          fragility: 74,
          evidence: 'none',
          impactIfWrong: 'high',
        },
      ],
      blindSpots: [
        {
          id: 'bsp-8',
          title: 'Repeat behaviour is inferred from category averages',
          description:
            'The repeat rate in the plan comes from published category benchmarks, not from anyone who has ordered this menu at this price point.',
          severity: 'critical',
          probingQuestion:
            'How many people have paid for this food twice, without a discount attached?',
        },
        {
          id: 'bsp-9',
          title: 'Kitchen lease outlasts the test',
          description:
            'The eleven-month lease and equipment purchase both commit capital before the first repeat cohort can even be observed.',
          severity: 'high',
          probingQuestion: 'What is the shortest lease that still lets you run a real trial?',
        },
      ],
      failureConditions: [
        {
          id: 'fcd-8',
          trigger: 'Repeat rate settles below 24% after the discount period ends',
          mechanism:
            'Contribution margin turns negative once acquisition has to be paid for twice, and daily orders plateau below break-even.',
          probability: 0.52,
          horizon: '6-months',
          severity: 'critical',
          earlyWarningSignal:
            'Second-order rate under 20% in the first 200 customers, measured without promo codes.',
        },
        {
          id: 'fcd-9',
          trigger: 'Aggregator raises commission or changes ranking weight',
          mechanism:
            'Visibility falls, paid placement becomes mandatory, and the marketing budget is consumed before repeat behaviour compounds.',
          probability: 0.34,
          horizon: '1-year',
          severity: 'high',
          earlyWarningSignal: 'Organic impressions declining while order volume is flat.',
        },
      ],
      regretScenarios: [
        {
          id: 'rgs-9',
          horizon: '6-months',
          title: 'Orders arrive, customers do not return',
          narrative:
            'Launch week looks healthy on discounts. By month four the cohort curve is flat, and the kitchen is running at 60% of break-even with rent already paid through the lease.',
          regretScore: 78,
          likelihood: 0.44,
          recoveryCost: 'costly-to-reverse',
        },
        {
          id: 'rgs-10',
          horizon: '1-year',
          title: 'Capital locked in equipment',
          narrative:
            'Winding down recovers perhaps a third of the fit-out. The lesson cost ₹3,00,000 more than a two-week test would have.',
          regretScore: 71,
          likelihood: 0.29,
          recoveryCost: 'irreversible',
        },
      ],
      trajectory: [
        { horizonMonths: 3, commitNow: 31, runExperiment: 18 },
        { horizonMonths: 6, commitNow: 58, runExperiment: 24 },
        { horizonMonths: 12, commitNow: 67, runExperiment: 27 },
        { horizonMonths: 24, commitNow: 61, runExperiment: 25 },
        { horizonMonths: 36, commitNow: 54, runExperiment: 23 },
        { horizonMonths: 60, commitNow: 47, runExperiment: 21 },
      ],
      recommendedExperimentId: 'exp-2210',
    },
  },
  {
    id: 'dcn-5098',
    title: 'Buy a new laptop',
    statement:
      'Replace a four-year-old machine that now adds roughly 40 minutes a day to build and test cycles. Budget is ₹1,80,000, and the current machine still resells for about ₹35,000.',
    domain: 'technology',
    status: 'analyzed',
    stakes: 'low',
    createdAt: '2026-09-05T11:00:00.000Z',
    updatedAt: '2026-09-07T09:45:00.000Z',
    analysis: {
      regretIndex: 16,
      analysisConfidence: 88,
      reversibility: 'reversible',
      verdictSummary:
        'Low regret exposure. The cost is bounded, the time saving is already measured, and resale keeps the downside small. No experiment is warranted; the decision is ready to make.',
      assumptions: [
        {
          id: 'asm-14',
          statement: 'The 40 minutes lost per day is caused by the machine, not the toolchain.',
          origin: 'hidden',
          confidence: 'high',
          fragility: 28,
          evidence: 'documented',
          impactIfWrong: 'moderate',
        },
        {
          id: 'asm-15',
          statement: 'Resale value holds near ₹35,000 for the next month.',
          origin: 'stated',
          confidence: 'medium',
          fragility: 34,
          evidence: 'partial',
          impactIfWrong: 'low',
        },
      ],
      blindSpots: [
        {
          id: 'bsp-10',
          title: 'Build times were measured on one project',
          description:
            'The time saving is extrapolated from a single repository, which may be the least representative workload.',
          severity: 'low',
          probingQuestion: 'Does the slowdown hold across the two other projects you touch weekly?',
        },
      ],
      failureConditions: [
        {
          id: 'fcd-10',
          trigger: 'Build times stay flat on the new machine',
          mechanism:
            'The bottleneck was toolchain configuration, so the spend buys no recovered time.',
          probability: 0.18,
          horizon: '6-months',
          severity: 'low',
          earlyWarningSignal: 'A profiling run showing most time spent waiting on network calls.',
        },
      ],
      regretScenarios: [
        {
          id: 'rgs-11',
          horizon: '6-months',
          title: 'Marginal gain, easily absorbed',
          narrative:
            'The machine is faster but the saving is nearer fifteen minutes than forty. Mildly annoying, entirely recoverable, and the old laptop was already sold.',
          regretScore: 22,
          likelihood: 0.31,
          recoveryCost: 'reversible',
        },
      ],
      trajectory: [
        { horizonMonths: 3, commitNow: 14, runExperiment: 12 },
        { horizonMonths: 6, commitNow: 18, runExperiment: 15 },
        { horizonMonths: 12, commitNow: 16, runExperiment: 14 },
        { horizonMonths: 24, commitNow: 13, runExperiment: 12 },
        { horizonMonths: 36, commitNow: 11, runExperiment: 11 },
        { horizonMonths: 60, commitNow: 9, runExperiment: 9 },
      ],
      recommendedExperimentId: null,
    },
  },
  {
    id: 'dcn-5091',
    title: 'Leave job for GATE preparation',
    statement:
      'Resign from a ₹14L software role to prepare full time for GATE, targeting an M.Tech admission. Preparation window is eleven months with no income, and the attempt cannot be repeated for a year if missed.',
    domain: 'career',
    status: 'analyzing',
    stakes: 'defining',
    createdAt: '2026-09-04T05:20:00.000Z',
    updatedAt: '2026-09-05T14:10:00.000Z',
    commitBy: '2026-10-10T00:00:00.000Z',
    analysis: {
      regretIndex: 79,
      analysisConfidence: 52,
      reversibility: 'costly-to-reverse',
      verdictSummary:
        'Analysis is still open. Five assumptions carry the decision and none of them has evidence strong enough to settle it, which is why the confidence in this read is low.',
      assumptions: [
        {
          id: 'asm-16',
          statement: 'Eleven months of full-time study is enough to clear the target rank.',
          origin: 'stated',
          confidence: 'low',
          fragility: 76,
          evidence: 'anecdotal',
          impactIfWrong: 'critical',
        },
        {
          id: 'asm-17',
          statement: 'Six hours of focused study a day is sustainable without income.',
          origin: 'hidden',
          confidence: 'low',
          fragility: 81,
          evidence: 'partial',
          impactIfWrong: 'high',
        },
        {
          id: 'asm-18',
          statement: 'A software role at a similar level is available if the attempt fails.',
          origin: 'hidden',
          confidence: 'low',
          fragility: 72,
          evidence: 'none',
          impactIfWrong: 'critical',
        },
        {
          id: 'asm-19',
          statement: 'Savings cover eleven months of expenses without new debt.',
          origin: 'stated',
          confidence: 'medium',
          fragility: 48,
          evidence: 'documented',
          impactIfWrong: 'high',
        },
        {
          id: 'asm-20',
          statement: 'An M.Tech materially changes the roles available afterwards.',
          origin: 'hidden',
          confidence: 'low',
          fragility: 69,
          evidence: 'anecdotal',
          impactIfWrong: 'high',
        },
      ],
      blindSpots: [
        {
          id: 'bsp-11',
          title: 'No fallback attempt defined',
          description:
            'The plan assumes a single attempt. GATE runs annually, so failing once means either a second unpaid year or re-entering the market mid-cycle.',
          severity: 'critical',
          probingQuestion: 'What happens on the day the result arrives and the rank is short?',
        },
      ],
      failureConditions: [
        {
          id: 'fcd-11',
          trigger: 'Study hours settle below five a day by month three',
          mechanism:
            'Preparation falls behind the syllabus while income stays at zero, so the cost compounds without improving the odds.',
          probability: 0.44,
          horizon: '6-months',
          severity: 'critical',
          earlyWarningSignal: 'Two consecutive weeks averaging under five hours a day.',
        },
      ],
      regretScenarios: [
        {
          id: 'rgs-12',
          horizon: '1-year',
          title: 'Rank short, year spent',
          narrative:
            'The attempt lands just outside the cutoff. Twelve months of income are gone and the market re-entry conversation starts from a gap on the CV.',
          regretScore: 84,
          likelihood: 0.38,
          recoveryCost: 'costly-to-reverse',
        },
      ],
      trajectory: [
        { horizonMonths: 3, commitNow: 38, runExperiment: 22 },
        { horizonMonths: 6, commitNow: 62, runExperiment: 29 },
        { horizonMonths: 12, commitNow: 84, runExperiment: 37 },
        { horizonMonths: 24, commitNow: 76, runExperiment: 34 },
        { horizonMonths: 36, commitNow: 68, runExperiment: 31 },
        { horizonMonths: 60, commitNow: 57, runExperiment: 27 },
      ],
      recommendedExperimentId: 'exp-2213',
    },
  },
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

/**
 * Readable id the analysis hand-off uses, so `/decision/demo` resolves to a
 * real report instead of a not-found state.
 */
export const DEMO_DECISION_ALIAS = 'demo';

const ID_ALIASES: Record<string, string> = {
  [DEMO_DECISION_ALIAS]: 'dcn-5104',
};

export function findDecision(id: string): Decision | undefined {
  const resolvedId = ID_ALIASES[id] ?? id;
  return decisions.find((decision) => decision.id === resolvedId);
}
