# Klipr Evolution Engine — phased to-do list

Status: **END GOAL / NORTH STAR — this is where Klipr is headed.** The
phases below (E1–E5) are the path to get there, in order. Do not build a
phase until its gates pass and Matt approves it.

Source: Matt + ChatGPT conversation, 2026-11-07 (evening). Summarized and
assessed by Muse 2026-11-08. The concept is sound; the sequencing below is
Muse's honest read of what Klipr can actually support, and when.

## The concept (one paragraph)

Klipr becomes a self-optimizing creative platform: it learns how people
create, identifies friction, discovers what produces better results, and
continuously improves its own workflows. The Creative Brain makes videos;
the Evolution Brain learns how to make the making better. AI proposes
changes; a deterministic rules engine controls what gets deployed. No
unrestricted AI code rewriting, no autonomous changes to billing, access
controls, privacy settings, security policies, or production code.

## The five memory systems

- **User memory** — individual preferences and working habits.
- **Creative memory** — which characters, scenes, props, voices, hooks work together.
- **Production memory** — which workflows and generation settings succeed.
- **Performance memory** — which published creatives produce results.
- **Experiment memory** — what Klipr has tested, learned, and changed.

Klipr permanently retains authentic and generated assets, finished videos,
metadata, provenance, and usage history. The production brain reuses valuable
existing material rather than regenerating everything.

## What Klipr optimizes (hierarchy)

1. **Primary:** successful published creative per active creator.
2. **Secondary:** time from starting creation to publication.
3. **Quality:** user acceptance and creative performance.
4. **Efficiency:** generation costs and number of retries.
5. **Retention:** whether users return and continue creating.

Do NOT optimize views alone. A viral video that generates no customers is
worth less than a modest video that generates bookings. The existing
performance tracking (external_posts / metric_snapshots / inquiries) is the
source of truth for outcomes.

## The phases (in order — do not skip ahead)

### Phase E1 — Behavioral instrumentation (foundation)
**Fold into the rebuild. Start collecting data from day one.**

- Standardized behavioral event system. Every meaningful interaction in
  Build, Library, Create: open Create, select character, change scene,
  remove generated clip, regenerate, change duration, save, publish, view
  performance. Record the context, not just the action: what was recommended,
  what the user changed, how many iterations, was it published, what happened
  after publication.
- Event tracking, workflow completion tracking, generation
  acceptance/rejection, asset reuse history, abandonment tracking.
- **Deliverable:** Klipr can accurately describe how people use it.
- **Gate to start:** the rebuild is underway (Supabase storage + DB live).
- **Effort:** days. This is the one piece worth doing soon — you cannot learn
  from data you never collected.

### Phase E2 — Personal intelligence
**After the rebuild is live and Matt is using it daily.**

- Individual user preference models + brand-specific creative profiles.
  Preselect the preferred character, suggest consistent scenes, recommend
  previously successful footage, reduce unnecessary configuration steps,
  adjust generation recommendations. Most of this is most-recently-used +
  most-frequently-used + explicit defaults — it does not need AI to be useful.
- **Deliverable:** each user's experience becomes progressively personalized.
- **Gate to start:** rebuild live, Matt using it daily, E1 events flowing.
- **Effort:** a week or two. This is the piece that pays Matt back immediately.

### Phase E3 — Adaptive workflows
**Deferred until there is real behavior data to learn from.**

- The Adaptive Workflow Engine: Observe → Hypothesize → Experiment →
  Adopt or reject. AI proposes changes to Create workflow steps, default
  settings, asset recommendations, character/scene selection, Manual vs Auto
  mode, generation configs. A deterministic rules engine validates and deploys;
  approval flow + rollback required.
- Requires workflows defined as versioned data (not hardcoded logic).
- **Deliverable:** Klipr improves its own product experience without a
  developer changing every setting manually.
- **Gate to start:** E1 + E2 live, enough behavior data to learn from
  (months of real usage, not days). Do NOT build on one user's first week.
- **Effort:** weeks of real engineering.

### Phase E4 — Experimentation intelligence
**Deferred until Klipr has real users. Meaningless with one user.**

- Controlled experiments (A/B), outcome measurement, automatic promotion
  and rollback. Segmented by user type, brand, and creative objective.
  A tattoo creator and a food creator need different workflows.
- **Deliverable:** Klipr can prove which changes actually improve performance.
- **Gate to start:** multiple active users, enough events per variant to
  reach a meaningful result. With one user there is no control group —
  comparing you-against-you across time proves nothing.
- **Effort:** weeks, plus the user base. Do not build before the users exist.

### Phase E5 — Autonomous creative intelligence
**Last. The moat — but only once the data exists.**

- Connect behavioral learning, asset intelligence, creative blueprints, and
  published performance into a Creative Knowledge Graph: ingredients
  (character, scenes, voice, hook, transitions, CTA) associated with outcomes
  (engagement, retention, clicks, conversions/bookings). Klipr proposes and
  assembles increasingly effective creative productions.
- Requires hundreds of published videos with performance data, plus accurate
  attribution (did THIS video cause THIS booking?). Research-grade work.
- **Deliverable:** a creative production system that gets smarter with every
  completed production cycle.
- **Gate to start:** E1–E4 live, hundreds of published videos with measured
  outcomes, attribution working. This is months to a year for a funded team.
- **Effort:** the largest phase. Do not start it first.

## Proposed tables (design only — not built, not migrated)

behavior_events, user_preferences, creative_insights, workflow_versions,
experiments, experiment_assignments, experiment_results,
optimization_proposals, optimization_history.

Three boundaries: individual intelligence (per user), brand intelligence
(per brand/audience), platform intelligence (aggregated, permissioned).
Never assume one creator's preferences should become another's.

## Hard gates (all phases)

Before ANY Evolution Engine phase is trusted as a learning signal:

1. The rebuild is done (Supabase Storage + DB live, Library retrieval works
   via signed URLs, asset persistence is reliable).
2. The validation loop is closed: a video posted, metrics recorded,
   inquiries tracked. Do not claim Klipr is validated for bookings until then.
3. Generation retrieval and performance-event capture are reliable.
   The engine must not learn from incomplete data.

These are ChatGPT's own prerequisite, and they are not met yet (2026-11-08):
Library thumbnails are blank, the rebuild hasn't started, zero videos posted,
zero real performance data.

## Safety boundaries (non-negotiable)

- AI proposes; a deterministic rules engine deploys. No unrestricted AI code
  rewriting.
- Never autonomously change billing, access controls, privacy settings,
  security policies, or production code.
- Every optimization has an audit trail, confidence threshold, experiment
  controls, approval settings, and rollback mechanism.
- The Evolution Engine dashboard (patterns discovered, proposals, active
  experiments, approved optimizations) shows REAL numbers only. The example
  figures in the ChatGPT conversation (127 patterns, 18 proposals, 4
  experiments, 12 approved) are illustrative, not live measurements.

## The architectural test — for every significant new feature

(Added 2026-11-08, from ChatGPT's response to this doc.)

Before building any significant new feature, ask one question:

**Does this feature move Klipr closer to becoming a self-optimizing
creative intelligence platform?**

It does not have to deliver that capability immediately. But it should do at
least one of these:

- Generate useful learning signals.
- Improve creative execution.
- Build reusable intelligence.
- Enable controlled adaptation.
- Improve measurable outcomes.

If a feature does none of those, it is not moving Klipr toward the end goal
— reconsider it, or defer it.

## The real leap

The long-term vision is not software that follows instructions better. It is
software that learns, identifies opportunities, tests improvements, and
evolves — and eventually **discovers improvements that neither its
developers nor its users explicitly asked for**. That is the leap the
Evolution Engine exists to make. Every phase (E1–E5) is a step toward making
that destination increasingly inevitable, not just possible.

## Where this sits in the phase cycle

This is the end goal — the destination the whole product is building toward.
It is NOT Phase 1, 2, 3, 4, or 7 work. It is a later phase (E1–E5) that
begins once the product works and has usage data. E1 (instrumentation) is
folded into the rebuild so collection starts early; E2–E5 each need their own
go-ahead. The current work (rebuild, validation loop, manual editor) is the
path to this end goal, not a detour from it.
