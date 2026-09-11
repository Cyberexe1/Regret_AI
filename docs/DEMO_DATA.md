# REGRET ENGINE — Demo Data Checklist

REGRET ENGINE has no seeded demo data built into the application — every decision, every piece of evidence, and every analysis result is created live against the real backend and real Amazon Bedrock. This document records the exact synthetic demo data that has been used, in this project's own QA passes, to reliably reproduce a strong demo. It is **not** a guarantee: the analysis pipeline calls a real language model, so the specific assumptions, blindspots, threshold, and experiment it produces will vary between runs. Everything below is *expected/demo-oriented*, not a fixed script the system is hardcoded to output.

All evidence text below is explicitly synthetic and should be labeled as such in any recording or write-up — it is not real market research.

## Decision text

**Title:**
```
Should I invest Rs 5 lakh to start a cloud kitchen?
```

**Description:**
```
I am considering investing INR 500,000 of my savings to launch a
cloud-kitchen (delivery-only restaurant) specializing in North Indian
tiffin meals, operating out of a rented commercial kitchen in a
mid-sized city. The plan is to list on Swiggy and Zomato and rely on
repeat weekday lunch orders from nearby offices to reach breakeven
within 6 months.
```

**Desired outcome:**
```
Reach a sustainable, profitable cloud kitchen business without losing
my full investment.
```

**Budget:** `500000` **Currency:** `INR`
**Timeline:** `6 months to breakeven`
**Location:** `Pune, India` (or any mid-sized city — not load-bearing)
**Risk tolerance:** `medium`

**Beliefs:**
```
I believe repeat weekday lunch orders from nearby offices will be
strong enough to sustain the business, and that Swiggy/Zomato
commissions will not erode margins below viability.
```

## Evidence file to upload

Save as a `.txt` file (also valid as `.pdf`/`.docx` if you prefer to demo a document upload instead) and clearly label it as demo/synthetic in its own content, exactly as below:

```
[DEMO / SYNTHETIC DATA - for REGRET ENGINE demonstration purposes
only, not real market research]

Pilot week observations (informal, self-reported, 7 days of test
operation before committing to the full lease):
- Total orders placed via Swiggy/Zomato during pilot week: 62
- Repeat customers (ordered more than once in the 7-day window): 12
  out of 62 total orders, meaning a same-week repeat-order rate of
  roughly 19%.
- Average order value: INR 220
- Platform commission observed: 24% of order value (Swiggy) and 22%
  (Zomato)
- Weekday lunch orders (12pm-3pm window) accounted for about 70% of
  total volume, consistent with the office-lunch thesis.
- Kitchen rent quoted: INR 28,000/month for the commercial kitchen
  space under consideration.
```

## What to expect (not guaranteed)

Based on repeated real runs against this exact decision + evidence during this project's own QA testing:

| Report section | Typically expected |
|---|---|
| **Assumptions** | Something along the lines of: repeat weekday lunch demand from nearby offices will materialize as expected; platform commissions will stay near the observed 22–24%; kitchen rent won't increase materially during the initial period. |
| **Blindspots** | A question the decision text doesn't address directly — e.g. sensitivity of the business to a rent increase, or whether the pilot week's demand is representative of a normal week. |
| **Regret scenario** | A specific failure story tied to the repeat-order rate or margin structure staying below what's needed to sustain operations. |
| **Threshold** | Most often a variable tied to **repeat-order rate** or **operational cost sensitivity**, with a `validation_status` of `provisional` or `validated` depending on how much the uploaded evidence actually supports a specific number. The application has, in real runs, also produced a threshold framed around the fixed operational-cost budget itself — treat whichever variable and value the live run actually shows as the correct one to narrate, not a fixed script. |
| **Experiment** | Commonly a short (roughly 2-week) preorder or extended-pilot campaign measuring the repeat-order rate directly, with a decision rule tied back to the threshold. In rare runs, the Experiment Planner may recommend no experiment at all if it judges the evidence doesn't yet justify a well-designed one — this is intended behavior (see [`README.md` Limitations](../README.md#29-limitations)), not a failure; re-running the analysis is the correct response, not inventing an experiment on screen. |

## Example experiment result to submit

If the run recommends an experiment targeting a repeat-order-rate–style threshold, a realistic demo result to submit is:

```
Outcome: partial
Summary: Extended pilot data (demo): repeat-order rate over a longer
observation window came in at 21%, still below the safe threshold but
improved from the initial 19% pilot-week figure.
Observations:
  - Repeat-order rate measured at 21% over a 3-week extended pilot,
    up from 19% in week one.
  - Platform commissions confirmed at 22-24% as originally estimated.
Measured value: whichever key the real threshold's variable actually
uses (check the threshold's `variable` field on screen before
submitting, so the measured value maps to the same variable — the
system will honestly report "requires more evidence" rather than
fabricate a match if the key doesn't line up).
```

Label this result as demo data in the "notes" field of the submission form (e.g. `"Demo/synthetic data for REGRET ENGINE demonstration."`).

## Cleanup

After recording or demoing, delete the decision (`DELETE /api/v1/decisions/{id}`, or via the report's own delete action if the UI exposes one) so demo data doesn't accumulate in the production database.
