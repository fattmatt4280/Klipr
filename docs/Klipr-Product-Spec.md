# Klipr — Product Spec

Oct 25, 2026 · @Matt

## Overview

Klipr turns a few photos or raw clips into a finished, post-ready short video, using a template for each content type. It merges a generation studio (avatars, scenes, b-roll) with a CapCut-style editor, so users can auto-edit first and fine-tune second.

- **Who it's for:** creators running one or more accounts. That includes tattoo artists, UGC creators, small brands, and personal brands.
- **First user:** Matt, across Shyftd.ink, fattmatt444, FridgeSpy, Budder Buddy, and The Quiet Discipline.
- **Strategy:** build it as a module inside DreamOps Command Center on the VPS, test it on real accounts, then repackage it as a standalone public app. Every decision is made as if multi-tenant from day one, so shipping is a repackage, not a rewrite.
- **Problem it solves:** raw footage posted with no edits, sound, or b-roll underperforms. Klipr makes the edited version the default output.

Build order: the working machine first. Landing pages and marketing get built around the live product once it works.

## Experience principles

Klipr has to feel smooth, natural, and personal from the first tap. These rules apply to every screen and outrank feature count.

- **Chat is home.** The app opens to the chat, like Claude or ChatGPT. Everything else (library, editor, feed) is one tap away, never in the way.
- **Personal from day one.** The app learns each user's brands, style profile, favorite templates, scenes, fonts, and posting habits, and puts them first. Defaults are always "what this user usually picks."
- **Fewer decisions.** Suggest, don't ask. Every question comes with tappable answers; free text is always allowed but never required.
- **Never lose work.** Autosave everything: chats, briefs, edits, uploads. Leaving mid-task and coming back resumes exactly where the user left off.
- **Instant feedback.** Every tap responds immediately. Long jobs show live progress with a preview, run in the background, and notify when done.
- **Thumb-friendly.** Built for one-handed phone use: bottom navigation, bottom sheets, large tap targets, and swipe gestures.
- **Plain language.** No technical terms in the UI (EDL, render queue, model names stay behind the scenes).

## Architecture & hosting

The VPS runs the app, database, storage, job queue, and FFmpeg renders. It has no GPU, so all generation goes out to APIs as queued jobs.

&#91;embedded content: Klipr architecture · clients, VPS, external services\]

The job queue is the core: every analyze, b-roll, avatar, and render step is a job with a status, retry policy, and credit cost.

- **Module now, app later:** Klipr is its own app with its own database schema and routes. The command center embeds it; it never depends on command center internals. Shipping means pointing a new domain at it.
- **Stack (suggested, Muse can adjust):** Next.js front end, AI calls through the existing OpenRouter connection, Voicebox for voice, Postgres with row-level security (Supabase fits, since it's already in the toolset), S3-compatible object storage, a Redis-backed job queue, and FFmpeg workers.
- **Scaling path:** when render load outgrows the VPS, move the workers to rented GPU or render nodes. The queue and the API stay where they are.

## Data model

Every row carries a `user_id` and, where it applies, a `brand_id`. Row-level security is on from day one, so the command center version is already multi-tenant.

| Entity | Belongs to | Key fields |
| --- | --- | --- |
| User | — | OAuth identity, role (admin or user), plan, credit balance, data opt-ins |
| Brand | User | name, sources (site, socials), brand kit, voice guide, business facts, default avatar, voice, scenes, CTA |
| Social connection | Brand | platform, OAuth token, verified owner |
| Memory | User or Brand | remembered fact or preference, source thread, editable |
| Style profile rule | Brand | rule text, source feedback IDs, pinned |
| Thread | Brand | messages, attachments, status (in progress or finished), linked project |
| Brief | Thread | compiled plan fields, version, approved at |
| Avatar | User (assigned to brands) | consent record ID, source video, provider model ID, preview |
| Voice | User (paired to avatar) | consent record ID, Voicebox model ID, sample clip |
| Consent record | User | selfie video, spoken phrase audio, liveness result, timestamp |
| Scene | User or Community | category (shop, kitchen, studio), stills or clips, linked ambiance, tags, visibility |
| Asset | User or Brand | type (photo, clip, sticker, font), storage path, description, AI shot tags |
| Audio track | System, User, or Community | type (music, ambient, SFX, composed), mood, BPM, license |
| Template | System, User, or Community | recipe JSON, content type, version, remix-of ID |
| Reference video | Template (admin only) | source, trait breakdown |
| Project | Brand | brief ID, template ID, input assets, edit decision list (EDL), render status |
| Render | Project | aspect ratio, file path, credits spent, cost, time to render |
| Feedback | Render, Post, or App | loop (style, quality, app), rating, tags, notes, video timestamp |
| Post | Project | visibility (private or community), likes, upvotes, comments, remix count, contest ID |
| Subscription | User | follower, followed creator |
| Contest | System | theme, rules, start and end dates, prize, winners |
| Credit ledger | User | amount, reason, job ID |

The **edit decision list (EDL)** is the heart of a project. Auto-edit writes it, the editor modifies it, and the renderer reads it. Nothing is ever baked into a video until render time.

## Auto-edit pipeline

One pipeline serves every content type; the template changes the recipe, not the code.

1. **Ingest.** The user drops 1–10 photos or clips into a brand, with either a one-line note or a brief from the planning chat ("cover-up, 3 sessions, client loves neon"). Files go to object storage; the job is queued.
2. **Analyze.** A vision model tags each shot by type (stencil, linework, wipe, reveal, face, product, hands, ambiance). It also scores sharpness, lighting, and motion, and transcribes any speech with Voicebox STT. It writes the results to the asset's shot tags.
3. **Plan.** The selected template's recipe fills its shot slots from the tagged shots. Empty slots are flagged for b-roll. The output is a draft EDL.
4. **Generate b-roll.**
   - **Real-photo motion:** push-ins, parallax, reframes, and lighting sweeps built from the user's own stills.
   - **Scene b-roll:** clips pulled from the brand's scene library.
   - **Generative ambiance:** only when a slot allows it and the template permits.
5. **Finish.** Captions come from the brand kit's style. Music is picked by the template's mood. An optional voiceover uses the avatar's voice. Transitions follow the recipe.
6. **Render.** FFmpeg renders 9:16 by default, plus 1:1 or 16:9 if requested. A preview is shown before credits are spent on the final render.
7. **Hand off.** The user opens it in the editor or approves it. Approved renders go to a staging folder Muse reads for captions and posting; the public version exports or posts directly.

**Tattoo rule:** templates with `content_type: tattoo` block generative models from creating or altering tattoo detail. B-roll there is motion built from real photos or scene ambiance only.

## Quality bar

A template ships only when its output is as good as the best real videos in its category. "Good" is defined by a reference set, not by opinion in the moment.

1. **Reference set:** for each template, collect 20–30 videos that nail that format, chosen by Matt for tattoo content. Store them in an admin-only library.
2. **Breakdown:** an AI pass, reviewed by Matt, breaks each reference into measurable traits: hook length, cut rhythm (average shot length), camera moves, caption size, position, and timing, music energy curve, and where the payoff lands.
3. **Recipe:** the template recipe is written from the traits the references share, not invented from scratch.
4. **Test set:** a fixed set of raw uploads (good footage and bad) is run through every template change.
5. **Pass test:** Matt watches the new output next to the references and the previous version. A change ships only if it is better, and only when he would post the result without re-editing.

The reference set grows over time: any Klipr video that performs well, or that Matt marks as a standout, can be added to it.

## Capture guidance

The best edit can't fix glare, bad light, or shaky footage, so Klipr coaches the user while they shoot. This is where 26 years of tattoo knowledge becomes the product's edge.

- **Shot list from the brief:** once a plan is approved, the agent lists exactly which shots it needs ("slow wipe, left to right," "10 s macro of the shading," "full arm, natural light").
- **In-app camera:** guides overlay the screen for each shot: framing, angle, distance, and a progress check as shots are captured.
- **Live checks:** warnings for glare, low light, blur, shake, and wrong orientation, with a one-line fix ("tilt 15° to kill the glare").
- **Tattoo know-how:** built-in guides for fresh versus healed photography, controlling shine on fresh work, lighting color work, wipe technique, and skin tone exposure.
- **Gap check:** before generating, the agent flags missing or weak shots and offers to reshoot, use photo motion instead, or swap the template.

Other content types get their own capture guides later (product UGC, talking head, kitchen).

## Templates

A template is a JSON recipe, not code. That means new content types, user templates, and community remixes are all just new rows.

```json
{
  "id": "tattoo-reveal",
  "content_type": "tattoo",
  "length_sec": [8, 15],
  "aspect": "9:16",
  "hook": { "style": "text_overlay", "max_sec": 1.5, "prompts": ["Wait for it", "{note}"] },
  "slots": [
    { "role": "wipe", "accepts": ["wipe", "process"], "sec": 2, "fallback": "photo_push_in" },
    { "role": "macro", "accepts": ["detail"], "sec": 3, "motion": "slow_push" },
    { "role": "full", "accepts": ["full_piece"], "sec": 3 },
    { "role": "flex", "accepts": ["flex", "spin"], "sec": 2, "optional": true }
  ],
  "broll": { "allowed": ["photo_motion", "scene"], "generative": false },
  "captions": { "preset": "brand_default", "position": "lower_third" },
  "music": { "mood": "dark_build", "beat_sync": true },
  "transitions": ["whip", "flash", "zoom_punch"],
  "cta": "brand_default"
}
```

| Template | Content type | Length | Structure | Generative b-roll |
| --- | --- | --- | --- | --- |
| Tattoo Reveal | Tattoo | 8–15 s | wipe → slow macro push-in → full piece → flex or spin | No |
| Tattoo Process | Tattoo | 15–30 s | stencil → lines → shading → color, sped up → fresh or healed | No |
| Cover-up / Before→After | Tattoo | 8–15 s | "what it was" hook → swipe or split → after → detail | No |
| UGC Product | UGC | 15–30 s | problem hook → demo → result → CTA | Yes, ambiance |
| Talking Head | Personal brand | 20–60 s | auto-captions, b-roll cutaway every 3–5 s, end card | Yes, cutaways |
| Faceless VO | Faceless | 30–60 s | voiceover script → scene or generated b-roll → kinetic text | Yes |

## Brand onboarding

Every brand starts with an import: the user gives a website and social accounts, the AI builds a draft brand profile, and a walkthrough confirms it. The same flow runs for every brand, any time, from a "+ New brand" button.

1. **Sources:** the user enters a website URL and connects or names social accounts (IG, TikTok, YouTube, Facebook). No website is fine; the walkthrough fills gaps by chat.
2. **Import:** the AI reads the sources and pulls:
   - **Visual identity:** logo, icons and favicon, color palette, and fonts (from the site's styles)
   - **Voice:** tone, vocabulary, phrases used often, emoji and hashtag habits, caption length
   - **Business:** what they sell or do, services, location, audience, and their usual CTA
   - **Content style:** top-performing posts, common formats, hook styles, posting frequency
   - **Assets:** the brand's own photos and videos, saved to that brand's library
3. **Walkthrough:** the agent presents each part as a card ("Here's your palette — right?") with keep, edit, or swap options and an Idk button. Voice can be approved by picking from sample captions written in each candidate tone.
4. **Compile:** the confirmed results become the brand profile: brand kit (logo, palette, fonts, caption presets), voice guide, business facts, a starting style profile, and suggested templates and scenes.
5. **Next steps:** the agent offers to set up an avatar and voice for the brand and to make a first video.

**Refresh anytime:** "Re-scan sources" re-runs the import and shows only what changed, for the user to accept or skip.

**Ownership and access:** brands are imported only from accounts the user connects through official logins or a website they can verify (a DNS record or file upload). Socials are read through their official APIs, not scraped. This stops users from cloning someone else's brand and keeps Klipr inside each platform's terms.

## The Klipr agent

Klipr is run by one agent that wraps every tool into a single flow. The user talks to it; it plans, remembers, learns, and drives the libraries, Composer, avatars, editor, publishing, and connected MCP servers on the user's behalf.

- **Persistent memory:** the agent remembers each user and each brand across threads: who they are, their audience, past videos, what worked, what they rejected, and running ideas. A new thread starts already knowing all of it. Users can view, edit, or delete anything it remembers.
- **Self-learning:** the three feedback loops plus what the user approves, edits, and posts continuously update memory and the brand style profile. Each plan should need fewer questions than the last.
- **Agentic, with checkpoints:** the agent does the work itself (picks assets, drafts scripts, matches templates, queues jobs), but stops at two checkpoints for the user: approving the plan and approving the final video. That is the "semi-seamless" part.
- **Voice chat:** planning works by voice as well as text. Push-to-talk or hands-free, transcribed with Voicebox STT, with optional spoken replies through Voicebox TTS. The transcript stays in the thread like typed messages.
- **One flow for every tool:** the user never has to open a separate tool to finish a video. If something is needed (a scene, a song, an avatar shot, a keyword from RNKR), the agent gets it inside the conversation.

## Planning chat & creative brief

Before anything is generated, the user plans the video in a chat. The chat ends in a compiled **creative brief**, and the brief, not a single prompt, drives the whole generation.

1. **Kickoff:** the user picks a brand and says what they want ("cover-up reveal for Shyftd.ink"), optionally attaching assets.
2. **Back-and-forth:** the planner asks only what it needs: goal, audience, hook, length, tone, which avatar or scene, CTA. It offers clickable suggestions (hook options, template matches, trending formats from the community feed) instead of open questions where it can.
3. **Compile:** when the user says go, the planner writes the brief: goal, platform, template, hook, beat-by-beat shot plan, script or VO lines, caption style, music mood, avatar, scene, CTA, and which uploaded assets fill which slots.
4. **Review:** the brief shows as an editable card. The user can tweak any field or jump back into the chat.
5. **Generate:** the brief becomes the job input. Every pipeline step (plan, b-roll prompts, captions, VO) reads from the full brief, so the output reflects the whole conversation.

Briefs are saved with the project, so a video can be regenerated, varied, or remixed from the same brief later. A one-line note still works for quick edits; the planner is for anything bigger.

### Plan first, generate second

No AI generation happens until the plan is complete and the user approves the brief. During planning the agent can show existing library items (scenes, sounds, templates, past videos) as examples, but it creates nothing new.

A full planning session works through every part of the video, and a progress strip at the top of the chat shows what's settled and what's left:

| Part | What gets decided |
| --- | --- |
| Purpose | goal, audience, platform, and what the viewer should do |
| Feel | tone, energy, pacing, and reference videos |
| Hook | the first 1–2 seconds, picked from several options |
| Story | beat-by-beat shot plan, using the user's uploads |
| Visuals | template, scene, avatar, b-roll style, transitions |
| Words | script or VO, on-screen text, caption style |
| Sound | library track or Composer, ambient, SFX, voice |
| Finish | CTA, length, aspect ratios, posting time |

The agent skips anything memory already answers and confirms it in one line instead ("Using your usual bold yellow captions").

### "Idk" (Surprise me)

Every question in planning has an **Idk** button next to the suggested answers.

- **One question:** the agent picks for the user, based on the brand style profile, what has performed best, and the rest of the plan, and states its pick and why in one line.
- **Whole plan:** a Surprise me option fills in every remaining part at once, then shows the full brief for review.
- **Control:** any surprise pick can be rerolled or locked. Picks the user keeps count as positive feedback; rerolls count as negative.

### Chat layout & threads

- **Single dialog:** one continuous conversation per thread, with the full backlog scrollable above, the same feel as Claude or ChatGPT. Uploads, suggestions, the brief card, render progress, and the finished video all appear inline in the conversation.
- **Thread menu:** a hamburger (☰) button opens a side drawer of past threads, newest first, searchable, and filterable by brand. Each thread shows its title, brand, date, and a thumbnail if it produced a video.
- **Finished threads:** when a thread reached a final video, the video sits right in the thread with actions to edit, publish, remix, or make a variation. The full conversation that led to it stays above it.
- **Unfinished threads:** if a thread stopped before a video, the chat stays exactly as it was, and the user can pick it up and keep going. The drawer marks these as in progress.
- **New chat:** one tap from the drawer or the top bar, pre-set to the brand the user was last working on.
- **Thread actions:** rename, pin, duplicate (start a new thread from the same brief), and delete.

## Feedback loop

Klipr runs three feedback loops. The first tunes each brand's own output. The second tells the admin where generation quality is failing across all users. The third measures how people feel about the app itself.

### 1. Brand style loop (per user)

Every output gets rated and noted, and those notes reshape the prompts for that brand's future generations, so each brand needs fewer tweaks over time.

1. **Capture:** after each render, quick reactions (keep, tweak, reject) plus a notes field ("hook too slow," "captions too big," "love the push-in on the detail"). Thumbs up or down can also be tapped on individual beats, captions, transitions, and b-roll clips.
2. **Track edits:** every change made in the editor after auto-edit is logged as implicit feedback (trimmed the hook, swapped the music, deleted a b-roll clip).
3. **Distill:** after each project, an AI pass turns notes and edits into short rules, stored in a **brand style profile** ("hooks under 1 s," "no zoom transitions," "bold yellow captions"). Duplicates merge; contradicting rules flag for review.
4. **Apply:** the planner and every pipeline prompt load the brand style profile automatically, so new briefs and generations start from what has worked.
5. **Control:** the profile is visible and editable. Rules can be pinned, edited, or deleted, and each one links to the feedback that created it.

Profiles are per brand, since what works for Shyftd.ink won't fit FridgeSpy. Real performance data (views, likes, saves from the community feed and connected socials) feeds the same profile once available.

### 2. Generation quality loop (platform-wide)

The same ratings, rolled up across all users, show the admin which templates, models, and pipeline steps produce bad output.

- **Quality report on any render:** a "Something's off" button with tags (blurry, wrong cut, bad caption timing, artifacts, wrong subject, audio issue) plus a notes field and the timestamp where it happens.
- **Admin quality dashboard:** reject and tweak rates by template, model, step, and content type, with the worst renders and their notes one tap away.
- **Fix and verify:** when the admin changes a template, model, or prompt, the dashboard compares quality before and after the change.
- **Privacy:** user content is used to improve their own brand profile by default. Using it to improve platform-wide prompts needs a clear opt-in at signup.

### 3. App experience loop

This tracks satisfaction with the app's layout, ease of use, and features, separate from video quality.

- **Feedback button everywhere:** a small, always-available button that captures the current screen, a 1–5 satisfaction rating, a category (layout, speed, a feature, a bug, an idea), and a notes field for recommendations.
- **Short check-ins:** a one-question satisfaction prompt after key moments (first render, fifth project, first publish), with an optional "What would make this better?" note. It's capped so users aren't nagged.
- **Feature requests:** recommendations are grouped by theme on an admin board, so the most requested changes rise to the top.
- **Close the loop:** when a requested change ships, users who asked for it get a notification.

All three loops log to the CRM next to usage data, so feedback can be matched to what each user actually did.

## Editor

The editor is mobile-first, with a CapCut-style layout, and it edits the EDL rather than raw video. Ease of use beats feature count: anything a user does twice should be one tap.

**Layout (phone):** preview on top, scrubber in the middle, and a layered timeline below. A bottom toolbar holds Edit, Text, Audio, Effects, Transitions, Avatar, and Scene. Each tool opens a bottom sheet, not a new screen.

**Core tools (Phase 3):**

- Trim, split, reorder, speed (including ramps), crop or reframe, and replace a clip from the library
- Text layers with font packs, caption presets, word-by-word highlight, and keyframed position and scale
- Audio: music library, beat markers, voiceover recording, Voicebox TTS, and auto-ducking
- Transitions: whip, zoom punch, flash, glitch, bounce, mesh warp, morph, and blur slide
- Effects: shake, RGB split, glow, film grain, and freeze frame
- Undo/redo, autosave, and version history (each save is an EDL snapshot)

**Font packs:** licensed or open-source fonts bundled in themed packs (Bold Caption, Neon, Clean, Grunge). Brand kits pin a default. Only fonts with commercial redistribution rights ship in the public app.

**Build approach:** render previews in the browser with a code-driven video framework (Remotion or similar; check the commercial license before the public launch). Final renders run on the server with FFmpeg from the same EDL. Transitions and effects are shader or preset modules, so new ones can be added without touching the timeline.

### Uploads

- **Multi-select upload:** many photos and clips at once, from camera roll, files, or a Drive folder, with batch progress. Uploads are compressed on the phone, resumable over spotty cell data, and keep going in the background. Assets can be reordered and tagged before a project starts.
- **Per-upload details:** every photo or video gets an optional description field ("client is the one on the left," "swap my shirt for the black Shyftd tee"). The planner and edit tools read it.

### AI edit tools

Users point at what to change and say how, in plain words.

- **Highlight tool:** brush, lasso, or tap-to-select (auto-segments a person, object, or background) on an image or a video frame. On video, the selection tracks the object across frames.
- **Instruction field:** fill-in prompts like "Swap \_\_\_ with \_\_\_" or "Change \_\_\_ to \_\_\_," plus free text. The edit applies only inside the highlighted area.
- **Background swap:** replace the background behind a person or product with a scene from the library, an upload, or a generated one. Lighting and edges are matched.
- **Character swap:** replace a person in a photo or video with one of the user's own avatars, or with a fictional or generated character. Swapping in any real person requires that person's consent record, same rule as avatars.
- **Object edits:** remove, recolor, restyle, or add an object inside the highlight.
- **Every AI edit is non-destructive:** it becomes a new layer in the EDL with before and after toggles, and it can be undone or regenerated.

On tattoo content, AI edits stay off the tattoo itself unless the user highlights it and explicitly confirms.

## Audio

Every sound in Klipr is cleared for commercial use, so any export can be posted or used in ads without a takedown. Popular copyrighted tracks are never bundled; an "export without music" option lets users add trending sounds inside TikTok or IG instead.

| Library | What's in it | How it's used |
| --- | --- | --- |
| Music | Royalty-free tracks tagged by mood, genre, BPM, and energy | Templates pick by mood; beat markers sync cuts |
| Ambient | Nature (rain, ocean, birds, wind), city (traffic, cafe, crowd), interiors (tattoo shop, kitchen, office) | Linked to scenes, so the shop scene brings shop ambiance |
| Sound effects | Whooshes, pops, risers, impacts, clicks, glitches, notification dings, tattoo machine buzz | Auto-placed on transitions and text pops; draggable on the timeline |
| Voice | Voicebox TTS and cloned voices | Voiceover from the brief's script |

### Composer

The Composer generates a custom song for the video, in the style of AI music platforms like Suno or Udio.

- **Inputs from the brief:** mood, genre, tempo, length, and instruments, plus optional lyrics or a hook line.
- **Fits the edit:** the track is generated to the video's exact length, with drops and accents lined up with the main beats (the reveal, the CTA).
- **Options:** instrumental or vocal, multiple variations per request, regenerate a section, and stems (drums, bass, melody, vocals) for mixing in the editor.
- **Library:** generated tracks save to the user's music library for reuse, and can be shared to the community.
- **Provider:** goes through the same adapter as other AI models. Pick a provider whose terms grant commercial-use rights to generated tracks, and confirm it offers an API before building on it.

## Avatars, voice & consent

Users can only clone themselves, and they must prove it with a live check. This is the gate that keeps the public app off deepfake blocklists, so it cannot be skipped.

**Avatar library:** each user keeps multiple avatars (different looks, outfits, or styles). Each avatar is paired with a Voicebox voice and assigned as the default for one or more brands. The user picks one per project or per scene.

**Consent flow (required before any clone):**

1. Record a live selfie video in-app (no uploads), following on-screen head-turn prompts.
2. Read a randomized consent phrase aloud: "I'm \[name\], and I authorize Klipr to create my digital likeness on \[date\]."
3. Run a liveness check, and match the face in the video to the face in the source footage.
4. Match the voice in the phrase to the voice samples used for cloning.
5. Store the consent record; every avatar and voice links to one.

**Hard rules:**

- No cloning from uploaded photos or videos of anyone else, including celebrities.
- Generated videos carry an invisible watermark and an "AI-generated" label in metadata.
- Users can delete an avatar and its consent record at any time; the model is deleted with it.
- Reported misuse freezes the avatar pending review.

**Providers:** avatar generation goes through an API provider. Voices run on Voicebox. Provider model IDs are stored per avatar, so providers can be swapped without users redoing setup.

## Community & competitions

Everything is private by default; publishing to the community is a per-post choice. The community's core loop is **remix**, because a template someone can reuse in one tap spreads faster than a video anyone can only watch.

- **Feed:** a TikTok-style full-screen vertical scroll of public generations, autoplaying. Tabs for For You (ranked) and Following (newest from subscriptions).
- **Interactions:** like, upvote, comment (threaded), share, save to a personal idea board, and subscribe to a creator.
- **Remix button:** opens the same template and brief with the remixer's own assets, crediting the original.
- **Browse for ideas:** search and filter by content type, template, scene, and trending; tapping "use this idea" starts a planning chat seeded with that post's brief.
- **Profiles:** each user's public posts, templates, and subscriber count, with optional links to their real social handles.
- **Template marketplace:** users publish templates and scene packs; remixes credit the original. Paid templates can come later.
- **Competitions:** themed contests ("Best neon reveal," "30-second kitchen hack") with start and end dates and rules. Entries are posts tagged with the contest ID; winners are picked by votes, a judge, or both.
- **Real numbers only:** every count (likes, upvotes, subscribers, views) starts at zero. No seeded accounts, bot engagement, or padded stats.
- **Moderation:** report button on every post and comment, auto-flags on uploads for nudity and violence, and a review queue. Avatars in public posts must belong to the poster.

## MCP

Klipr runs its own MCP server, so any agent (Muse, Claude, the command center) can drive it the same way a user does. It can also call out to other MCP servers as tools.

**Klipr as an MCP server (tools it exposes):**

- `list_brands`, `list_templates`, `list_assets`, `list_scenes`, `list_avatars`
- `upload_asset`, `create_brief`, `start_planning_chat`, `send_planning_message`
- `create_project`, `generate` (from a brief), `get_job_status`, `get_render`
- `publish_post`, `get_feed`, `get_post_stats`

Every MCP call is authenticated per user via OAuth, respects the same permissions and credit rules as the app, and is logged to the CRM.

**Klipr as an MCP client:** the planner and pipeline can call connected MCP servers, for example the command center (RNKR keywords for hooks and captions), Google Drive (pull assets from the folder Muse already uses), and calendar (schedule a posting plan). Users connect their own servers in settings once the app is public.

## Publishing, coaching & engagement

- **Content coach:** the planning chat opens with "what should I post next?" It suggests ideas based on the brand's style profile, recent posts, gaps in the posting schedule, and what's trending in the community feed. This brings back Klipr's original content-coach idea.
- **Direct publishing:** connect IG, TikTok, YouTube, and Facebook accounts per brand. Post now or schedule, with captions, hashtags, and location tags per platform.
- **Content calendar:** a week and month view of scheduled and published posts across all brands, with drag to reschedule.
- **Onboarding:** the brand onboarding import and walkthrough, then a guided sample project, so a new user has a finished video within five minutes.
- **Notifications:** push and in-app alerts for render done, comments, new subscribers, contest results, and shipped feature requests.

## Platform essentials

These are required before anyone other than Matt uses Klipr.

- **Backups:** automated daily backups of the database and file storage to a separate provider, with a tested restore. The VPS is a single point of failure.
- **Storage:** files live in cheap S3-compatible object storage (Cloudflare R2 or Backblaze B2), not on the VPS disk. The editor uses low-res proxies; raw uploads are archived or deleted after a set retention period, with users warned first.
- **Staging environment:** a separate copy of the app and database for testing changes before they go live.
- **Monitoring:** error tracking, alerts on failed jobs, render queue health, and a daily AI spend summary.
- **Security:** rate limits on uploads, generation, and MCP calls, abuse detection, and secrets kept out of the codebase.
- **Legal:** terms of service, privacy policy, content policy, DMCA takedown process, and an 18+ age gate for avatars and character swap.
- **Account control:** users can export all their data and delete their account and everything in it. App stores require this.

## Credits & cost control

Only AI calls cost money. Editing, rendering, and Voicebox voice are free to run, and AI already routes through the command center's OpenRouter connection. So credits only gate AI work, and the ledger still exists from Phase 1 so the public version can bill for it.

**No paywall until launch.** Billing is built but switched off by a `billing_enabled` flag. Until Phase 7 (public launch), nothing is blocked; every action is still metered and logged.

- **Admin role:** Matt's account is `admin`, with unlimited credits, access to every feature flag, and an admin panel to edit templates, recipes, font packs, scenes, and credit costs live without redeploying.
- **Test as a regular user:** a "view as plan" toggle lets the admin preview the app as Free, Pro, or any tier, so the paywall can be tested before it goes live.
- **Everything tracked:** every signup, project, render, AI call, and credit spend feeds the CRM, same setup as FridgeSpy. That gives real cost and usage numbers to price the plans from.

| Action | Cost to run | Credits |
| --- | --- | --- |
| Upload, edit, preview, render (FFmpeg) | Free | 0 |
| Photo-motion b-roll, transitions, effects, captions | Free | 0 |
| Voicebox voice clone, TTS, and transcription | Free | 0 |
| Shot analysis (vision model via OpenRouter) | Small, per image | Low |
| AI-generated template or script | Small, per call | Low |
| Generative b-roll clip | Paid model | Medium |
| Avatar video | Paid model | High |

Credit amounts get set from actual OpenRouter and provider pricing. During testing, the admin account bypasses credits entirely. If a video or avatar model isn't available on OpenRouter, it plugs into the same adapter as a direct provider.

- **Show cost before spending:** every generate button shows its credit cost, and a full render shows the total.
- **Cache everything:** a generated b-roll clip is stored and reused, never regenerated for the same input.
- **Limits:** per-user daily caps on generation, plus a hard monthly spend cap on each provider account.
- **Plans:** free tier with monthly credits; paid tiers add credits, avatars, and storage. Credit packs can be bought on top.

## Roadmap

Klipr is built in eight phases, in the order a real product needs them. Phase 1 is a thin slice: one brand, one template, upload to posted video. Every later phase adds to a slice that already works. Phases 0–5 run inside DreamOps for Matt; Phase 6 opens it to invited artists; Phase 7 is the public launch.

&#91;embedded content: Roadmap · 8 phases, 7 gates\]

No dates yet; each phase starts when the gate above it passes, not on a calendar.

## Handoff notes for Muse

Build in phase order, and don't start a phase until the gate above it passes. Start with Phase 0 and Phase 1 only. Klipr is a self-contained module the command center mounts, never part of command center internals.

**Phase 0 · Foundation**

- [ ] Create a separate `klipr` app folder, database schema, and env file. The command center links to it; it never imports command center code.
- [ ] Stand up a staging environment next to production.
- [ ] Use object storage for all media from day one, not the VPS disk.
- [ ] Set up daily offsite backups of the database and storage, and test one restore.
- [ ] Add OAuth (the same system the public app will use), the admin role on Matt's account, and the `billing_enabled` flag set to off.
- [ ] Turn on row-level security for every table at creation.
- [ ] Build the job queue. Route every AI call through the OpenRouter adapter, meter it in the credit ledger, and log it to the CRM.
- [ ] Put each capability (vision, video, avatar, music) behind its own adapter so providers can be swapped.

**Phase 1 · First real video**

- [ ] Set up Shyftd.ink as a brand by hand. Brand import comes in Phase 4.
- [ ] Build the Tattoo Reveal reference set with Matt and write the recipe from its breakdown.
- [ ] Store templates as JSON rows in the database, not as hardcoded logic.
- [ ] Use a simple brief form for now. The full planning chat comes in Phase 2.
- [ ] Build the pipeline: analyze, plan, photo-motion b-roll, captions, starter royalty-free music, FFmpeg render.
- [ ] Add keep, tweak, or reject with notes on every render.
- [ ] Send approved renders to the Drive folder Muse posts from.
- [ ] Report for every video: AI cost, time from upload to finished render, and any upload failures. Also report the VPS specs and anything in this spec that doesn't fit the VPS.
