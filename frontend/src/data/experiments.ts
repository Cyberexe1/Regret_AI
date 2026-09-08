import type { Experiment } from '@/types';

/**
 * Candidate and in-flight experiments. Each one exists to attack a specific
 * assumption for the cheapest price that still changes belief.
 */
export const experiments: Experiment[] = [
  {
    id: 'exp-2210',
    decisionId: 'dcn-5104',
    title: '14-day customer retention pilot',
    hypothesis:
      'At least 24% of first-time customers order again within 30 days without a discount attached.',
    method:
      'Cook the menu from a rented commercial kitchen for fourteen days, list on one aggregator, and track the second-order rate of the first 200 customers with no promo codes after day three.',
    status: 'running',
    cost: { currency: 'INR', amount: 15_000, days: 14, effort: 'medium' },
    informationGain: 88,
    targets: ['asm-11'],
    successCriteria: [
      'Second-order rate at or above 24% within 30 days',
      'At least 200 unique first-time customers reached',
      'No promotional discount active after day three',
    ],
    createdAt: '2026-09-03T06:00:00.000Z',
  },
  {
    id: 'exp-2211',
    decisionId: 'dcn-5104',
    title: 'Cloud kitchen demand test',
    hypothesis:
      'A single brand can sustain 42 orders a day in this catchment without paid placement.',
    method:
      'Run a listing-only test with a limited menu from the same rented kitchen, holding marketing spend at zero, and record daily organic order volume across the catchment.',
    status: 'running',
    cost: { currency: 'INR', amount: 18_000, days: 21, effort: 'low' },
    informationGain: 64,
    targets: ['asm-13'],
    successCriteria: [
      'Median daily orders at or above 42 in the final week',
      'No paid placement or aggregator promotion used',
    ],
    createdAt: '2026-09-04T06:30:00.000Z',
  },
  {
    id: 'exp-2212',
    decisionId: 'dcn-5098',
    title: 'Laptop battery test',
    hypothesis:
      'The current machine sustains a full build cycle off-charger, so the slowdown is thermal rather than age-related.',
    method:
      'Run three consecutive full builds off-charger, logging wall-clock time per build and remaining charge after each.',
    status: 'validated',
    cost: { currency: 'INR', amount: 0, days: 2, effort: 'low' },
    informationGain: 41,
    targets: ['asm-14'],
    successCriteria: [
      'Three builds complete without external power',
      'Build time variance under 10% between first and third run',
    ],
    createdAt: '2026-09-05T13:20:00.000Z',
    finding:
      'Third build ran 34% slower than the first and the machine throttled at 71°C. The slowdown is the hardware, not the toolchain.',
  },
  {
    id: 'exp-2213',
    decisionId: 'dcn-5091',
    title: 'GATE preparation trial',
    hypothesis:
      'A full-time study schedule of six hours a day is sustainable for eleven months.',
    method:
      'Hold the intended study schedule for fourteen consecutive days while still employed, recording hours actually completed each day.',
    status: 'inconclusive',
    cost: { currency: 'INR', amount: 0, days: 14, effort: 'high' },
    informationGain: 58,
    targets: [],
    successCriteria: [
      'Six hours completed on at least twelve of fourteen days',
      'No decline in output at work',
    ],
    createdAt: '2026-08-22T05:45:00.000Z',
    finding:
      'Six hours held on nine of fourteen days, averaging 4.8 hours. Sustainable while employed is not the same as sustainable full time, so the trial does not settle the question.',
  },
  {
    id: 'exp-2201',
    decisionId: 'dcn-4812',
    title: 'Run a two-week paid build sprint with the prospective co-founder',
    hypothesis:
      'If we can ship a working prototype and resolve one real direction disagreement in two weeks, the partnership survives sustained pressure.',
    method:
      'Take unpaid leave for ten working days. Build to a fixed scope, hold a written decision log, and deliberately surface one contested product call.',
    status: 'running',
    cost: { currency: 'USD', amount: 0, days: 14, effort: 'high' },
    informationGain: 78,
    targets: ['asm-2'],
    successCriteria: [
      'A contested direction call is resolved in writing within 48 hours',
      'Prototype reaches five external users',
      'Neither party requires an outside mediator',
    ],
    createdAt: '2026-08-26T10:00:00.000Z',
  },
  {
    id: 'exp-2202',
    decisionId: 'dcn-4812',
    title: 'Test staff-level re-entry demand without leaving',
    hypothesis:
      'If three qualified staff-level conversations can be generated in three weeks, the re-entry assumption holds.',
    method:
      'Open to recruiter conversations for one month, take interviews to the offer-discussion stage, and record time-to-first-offer without accepting anything.',
    status: 'proposed',
    cost: { currency: 'USD', amount: 0, days: 21, effort: 'medium' },
    informationGain: 61,
    targets: ['asm-1'],
    successCriteria: [
      'Three staff-level processes reach final stage',
      'Median time from first contact to offer conversation under five weeks',
    ],
    createdAt: '2026-08-27T09:30:00.000Z',
  },
  {
    id: 'exp-2203',
    decisionId: 'dcn-4812',
    title: 'Model household burn against a 24-month zero-salary scenario',
    hypothesis:
      'The household can absorb 24 months without salary while keeping a six-month emergency reserve intact.',
    method:
      'Build a month-by-month cash model including replacement health coverage, then run it past the household as a joint decision rather than a projection.',
    status: 'validated',
    cost: { currency: 'USD', amount: 0, days: 3, effort: 'low' },
    informationGain: 52,
    targets: ['asm-3'],
    successCriteria: [
      'Reserve stays above six months of expenses in every modelled month',
      'Both household members sign off on the reversal trigger',
    ],
    createdAt: '2026-08-25T14:20:00.000Z',
    finding:
      'Runway holds for 19 months, not 24, once replacement health coverage is priced in. Reversal trigger set at month 15.',
  },
  {
    id: 'exp-2204',
    decisionId: 'dcn-4790',
    title: 'Shadow-read 5% of production retrieval traffic through the managed index',
    hypothesis:
      'Managed p99 retrieval latency stays under 180ms at production query distribution.',
    method:
      'Mirror 5% of live queries to the managed provider without serving results, and compare p50, p95 and p99 against the in-house index for fourteen days.',
    status: 'running',
    cost: { currency: 'USD', amount: 640, days: 14, effort: 'medium' },
    informationGain: 84,
    targets: ['asm-5'],
    successCriteria: [
      'p99 under 180ms across all fourteen days',
      'No result-quality divergence above 2% on the evaluation set',
    ],
    createdAt: '2026-08-14T08:00:00.000Z',
  },
  {
    id: 'exp-2205',
    decisionId: 'dcn-4790',
    title: 'Time-box an index rebuild at triple corpus size',
    hypothesis: 'Rebuild time and cost scale sub-linearly as the corpus triples.',
    method:
      'Generate a synthetic corpus at 3x current volume and run a full rebuild against both the managed and in-house index, recording wall-clock time and billed cost.',
    status: 'inconclusive',
    cost: { currency: 'USD', amount: 310, days: 4, effort: 'low' },
    informationGain: 47,
    targets: ['asm-7'],
    successCriteria: [
      'Rebuild completes inside the four-hour maintenance window',
      'Billed cost stays within 1.5x of current spend',
    ],
    createdAt: '2026-08-20T11:15:00.000Z',
    finding:
      'Synthetic corpus did not reproduce real embedding distribution, so rebuild timings were not comparable. Needs a sampled production corpus.',
  },
  {
    id: 'exp-2206',
    decisionId: 'dcn-4771',
    title: 'Document the win pattern across the last fifteen closed deals',
    hypothesis:
      'A repeatable motion already exists and can be written down from historical deals.',
    method:
      'Interview both founders on each of the last fifteen wins, extract trigger, buyer role and time-to-close, and test whether three or more deals share the same path.',
    status: 'proposed',
    cost: { currency: 'USD', amount: 0, days: 5, effort: 'medium' },
    informationGain: 91,
    targets: ['asm-8', 'asm-9'],
    successCriteria: [
      'At least eight of fifteen deals map to a single documented path',
      'One-page playbook produced that a non-founder could follow',
    ],
    createdAt: '2026-08-02T16:40:00.000Z',
  },
  {
    id: 'exp-2207',
    decisionId: 'dcn-4771',
    title: 'Hire a fractional sales leader for one quarter first',
    hypothesis:
      'A fractional leader can establish or disprove a repeatable motion for under 15% of the cost of a full VP commitment.',
    method:
      'Engage an experienced operator two days per week for twelve weeks with a single deliverable: a validated, documented motion or a written finding that none exists yet.',
    status: 'invalidated',
    cost: { currency: 'USD', amount: 28_000, days: 84, effort: 'low' },
    informationGain: 66,
    targets: ['asm-8', 'asm-10'],
    successCriteria: [
      'Documented motion validated by two non-founder-sourced wins',
      'Total spend under $30k',
    ],
    createdAt: '2026-08-05T09:50:00.000Z',
    finding:
      'No available fractional operator would commit to a documented-motion deliverable inside one quarter. Scope was rejected by all four candidates.',
  },
];

export function experimentsForDecision(decisionId: string): Experiment[] {
  return experiments.filter((experiment) => experiment.decisionId === decisionId);
}

export function findExperiment(id: string): Experiment | undefined {
  return experiments.find((experiment) => experiment.id === id);
}
