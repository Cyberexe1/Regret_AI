# REGRET ENGINE — Demo Script (~4 minutes)

This is a story-driven walkthrough, not a feature tour. It uses the actual application, the actual deployed backend, and real (synthetic/labeled-as-demo) evidence — no fabricated screens, no invented threshold numbers. See [`docs/DEMO_DATA.md`](DEMO_DATA.md) for the exact decision text and evidence to use so this is reproducible.

**Scenario:** A founder asks whether to invest ₹5 lakh (INR 500,000) to start a cloud kitchen.

---

## 0:00–0:20 — Hook

> "Most AI tools tell you what decision to make.
>
> REGRET ENGINE asks a different question:
>
> What would have to be true for this decision to fail?"

Open on the landing page. Point at the one-line positioning ("Know what could make your decision fail") and the four-step loop shown there (Decision → Failure Condition → Threshold → Experiment). Don't linger — the landing page is meant to be understood in under 15 seconds.

## 0:20–0:50 — Create decision

Navigate to **New Decision**. Enter the cloud-kitchen decision text (see `docs/DEMO_DATA.md`):

- **Decision:** "Should I invest ₹5 lakh to start a cloud kitchen?"
- **Desired outcome:** reach a sustainable, profitable business without losing the full investment.
- **Constraints:** budget (₹5,00,000), 6-month breakeven timeline, location.
- **Beliefs:** repeat weekday lunch orders from nearby offices will be strong enough; platform commissions won't erode margins below viability.

Upload the pilot-week evidence file (clearly labeled `DEMO / SYNTHETIC DATA` in its own text, so nobody in the audience mistakes it for real market research).

Narration: *"This isn't a hypothetical prompt — it's a real decision with real constraints and a week of pilot data already attached."*

## 0:50–1:40 — Agent analysis

Click **Analyze**. Show the live analysis screen — the actual per-stage pipeline status (Decision Analyzer → Assumption Hunter → Blindspot Hunter → Evidence Agent → Devil's Advocate → Regret Simulator → Threshold Engine → Experiment Planner), each ticking to "completed" as the real backend reports it. Do **not** show or narrate any chain-of-thought — only the stage names and, once complete, the high-level outputs:

- A handful of assumptions the decision depends on.
- A blindspot nobody explicitly asked about.
- What the uploaded evidence actually supports or leaves unaddressed.
- A concrete challenge from the Devil's Advocate.
- A regret scenario describing one specific way this fails.

Narration: *"Every one of these came from a real call to Amazon Bedrock, orchestrated through the Strands Agents SDK — nine agents, each one only building on the structured output of the one before it."*

## 1:40–2:30 — The wow moment: the threshold

Open the Decision Report's Thresholds section. Show the **actual threshold** the Threshold Engine produced for this run — use whatever real variable and value it generated (commonly something like repeat-order rate, but report the number the application actually shows, never a pre-scripted one).

Narration (adapt the specific numbers to what's on screen):

> "The system didn't just say this looks risky. It found the variable that can break the decision — [the real variable shown, e.g. repeat-order rate] — and the specific point below which the economics stop working. Right now, that threshold is [validated / provisional], based on what's actually been tested so far."

If the run produced a qualitative (non-numeric) threshold instead of a number, say so honestly — that's still the same wow moment: *"the system is telling us exactly what's unproven, not inventing a false sense of precision."*

## 2:30–3:10 — Experiment

Scroll to the recommended experiment.

Narration: *"Instead of committing ₹5 lakh, REGRET ENGINE tells the founder what to test first."*

Show, from the real recommendation:

- **Hypothesis**
- **Steps** (the concrete method)
- **Success criteria** / **failure criteria**
- **Evidence to collect**
- **Decision rule** (what happens next depending on the outcome)

Narration: *"This isn't 'do more research.' The system is explicitly forbidden from recommending generic advice — every experiment has to name what to measure and what counts as pass or fail."*

## 3:10–3:40 — Re-evaluation

Go to the experiment's result form. Enter a realistic demo result (see `docs/DEMO_DATA.md` for the exact example — e.g. an extended pilot's repeat-order rate). Submit it.

Show the system update the decision assessment in real time — the before/after threshold comparison and the new `decision_assessment` status (strengthened / weakened / unchanged / inconclusive / requires more evidence), plus the `key_learning` and `recommended_next_step`.

Narration: *"The important part is that the analysis doesn't end here. We test the assumption in the real world, and the result feeds straight back into the system — deterministically, not another AI guess re-scoring the outcome."*

## 3:40–4:00 — Closing

Return to the Decision Report's summary view (or the updated assessment screen — whichever is the strongest visual on screen at that point).

> "REGRET ENGINE doesn't make the decision for you.
>
> It tells you what could break it,
>
> what evidence you're missing,
>
> and what to test before you commit."

End on that screen. Do not add additional feature callouts after this line — the closing line is the entire pitch.

---

## Production notes for whoever records this

- Use the live production URL (CloudFront), not localhost, so judges can independently verify the deployment.
- The analysis stage takes roughly 45–90 seconds against real Bedrock calls. Either record it at real speed to demonstrate it's genuinely live, or speed up only that segment in post — never fake the stage-by-stage progress with a mocked animation.
- If a run produces zero recommended experiments (the Experiment Planner is explicitly allowed to decline rather than fabricate one — see [`README.md` Limitations](../README.md#30-limitations)), re-run the analysis rather than improvising a fake experiment on screen. The demo data in `docs/DEMO_DATA.md` is chosen specifically because it reliably produces a rich threshold + experiment story.
- Clean up the demo decision after recording (`DELETE /decisions/{id}`) so the production database doesn't accumulate test data.
