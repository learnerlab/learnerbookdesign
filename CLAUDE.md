# CLAUDE.md — Learner Score
> Read this entire file before writing any code. It is the product spec, the technical spec, and the working agreement for this project. Where it conflicts with a library default or a "best practice," this file wins. Anything marked `[FILL]` is owed by Trevor — ask for it, never invent it.
---
## 1. What we're building
**Learner Score** is a free, three-minute self-assessment at `learnerreport.com` — its own domain, built and branded as a Learner Lab product ("by The Learner Lab" in the header and footer; all content links go to thelearnerlab.com). A person answers ~24 questions, enters their email, and gets a personal Learner Score (0–100) with a visual profile across three measures, plus a report by email.
Naming: the number is the **Learner Score**; the results page and PDF are **your Learner Report**; the address is **learnerreport.com**. Use those three consistently and never invent a fourth name.
Its job, in priority order:
1. Give the person one honest, useful, beautiful result.
2. Grow The Learner Lab email list, segmented by what each person needs.
3. Point people at the right Learner Lab content (and, later, the book *Learner: Get Better at Getting Better*).
It is a tool, not a research study. It is not sold. Simplicity beats features every time.
**The three measures**
| Key | Measure | What it asks | Source |
|---|---|---|---|
| `growth` | Growth mindset | Do you believe abilities can be developed? | Dweck's implicit-theories scale (existing, validated) |
| `stress` | Stress mindset | Is stress enhancing or debilitating? | Crum's Stress Mindset Measure (existing, validated) |
| `actions` | Learner actions `[FILL: final name — "Learner Actions" / "Reps" / other]` | Are you actually stepping into learning situations? | Built in-house (see §4) |
Research context (for writing accurate copy, not for reproduction): the growth × stress combination comes from Yeager, Bryan, Gross et al., *Nature* (2022), the "synergistic mindsets" paper. Challenge-seeking as the behavioral definition of a "learner" comes from Rege, Dweck, Yeager et al., *American Psychologist* (2021). Feedback-seeking as a behavior comes from Ashford & Cummings (1983). Do not overstate: the stress mindset scale is validated and used verbatim; the growth mindset items are adapted from Dweck's validated scale (one word changed, see §4.2); the actions scale and the combined score are "built on the research." Only the stress scale may be described as "validated."
**Non-goals for v1:** accounts/login, payments, native app, AI-generated results copy, team dashboards (v2, see §12), multiple languages.
---
## 2. Stack (defaults — ask before deviating)
- **Domain:** `learnerreport.com` (Trevor owns it). `www` redirects to apex. Optionally point `score.thelearnerlab.com` at it as a redirect.
- **Framework:** Next.js (App Router) + TypeScript (strict) + Tailwind. Deployed on Vercel.
- **Database:** Postgres via Supabase (or Neon). ORM: Drizzle. Migrations checked in.
- **Charts:** hand-rolled SVG. No charting library. The radar is a single `<polygon>`; we want full control and fast loads.
- **Transactional email:** Resend (domain-verified `thelearnerlab.com` sender). Not Mailchimp Transactional.
- **Marketing email / list:** Mailchimp Marketing API (see §8). Nurture sequences live in Mailchimp, not in this app.
- **Share images:** `next/og` (`ImageResponse`).
- **PDF:** `@react-pdf/renderer`, server-side, on demand (phase 4).
- **Analytics:** PostHog (product events + funnel). UTM capture handled by us, not by PostHog alone.
- **Bot protection:** Cloudflare Turnstile at the email gate + rate limiting on `/api/submit`.
- **Cron:** Vercel Cron for nightly norms (phase 4).
- **Tests:** Vitest. Scoring logic must have unit tests before anything else is built on it.
No UI kits, no component libraries. No `localStorage` for anything except the in-progress quiz draft.
---
## 3. Product principles
- One question per screen. Big tappable answers. Never more than one decision per screen.
- No email until the end. The gate is the only friction, and it comes after the work is done.
- Results live at a permanent, unguessable URL. The email is a pointer to it, not a substitute.
- Everything a human might rewrite — questions, copy, content links, band thresholds, profile rules — is **data in config files**, not code.
- Scores are computed on the server only. Never in the browser.
- Store raw answers forever. They are the norms, the validity check, and future content.
- Mobile first. Most people will do this on a phone from a podcast link.
- Copy is sentence case, plain verbs, in Trevor's voice (see §10). Buttons say what they do.
---
## 4. The instrument
The full instrument lives in `config/instrument.json` (schema-validated with zod at build time). Every response is stamped with `instrument_version`. **Changing any item wording or count after public launch requires bumping the version** — norms are computed per version.
### 4.1 Config schema (shape)
```json
{
  "version": "1.0",
  "sections": [
    {
      "key": "growth",
      "name": "Growth mindset",
      "intro": "How much do you agree with each statement?",
      "scale": {
        "type": "agreement",
        "options": [
          { "value": 1, "label": "Strongly agree" },
          { "value": 2, "label": "Agree" },
          { "value": 3, "label": "Mostly agree" },
          { "value": 4, "label": "Mostly disagree" },
          { "value": 5, "label": "Disagree" },
          { "value": 6, "label": "Strongly disagree" }
        ]
      },
      "items": [
        { "id": "g1", "text": "[FILL]", "direction": "higher_is_better" }
      ]
    }
  ],
  "bonus": { "id": "bonus", "prompt": "...", "options": [ { "key": "easy", "label": "..." }, { "key": "hard", "label": "..." } ] }
}
```
`direction` is per item: `higher_is_better` means a larger numeric answer counts toward being a learner; `lower_is_better` is the reverse. This handles reverse-scored items and either scale orientation without special cases.
### 4.2 Section A — Growth mindset (`growth`)
- Source: Dweck's 3-item Growth Mindset Scale (Dweck 1999, 2006), as distributed free by Stanford SPARQ: https://sparqtools.org/mobility-measure/growth-mindset-scale/ (downloads on that page).
- Items: **[FILL]** — paste the three items from the SPARQ page, then make exactly one change: replace the word "intelligence" with "abilities" (and "basic intelligence" with "basic abilities") in each item. Nothing else changes. All three are fixed-mindset statements, so all three are `higher_is_better` (more disagreement = more growth mindset).
- Scale: 6-point agreement, values 1–6: 1 strongly agree, 2 agree, 3 mostly agree, 4 mostly disagree, 5 disagree, 6 strongly disagree. Section score = mean of the three, normalized to 0–100.
- The intelligence → abilities swap is a deliberate product decision by Trevor: adults read "intelligence" as IQ, and the tool is about skills that can be built. Domain-specific versions of Dweck's items are common in the literature, so this is an adaptation, not a new scale. Consequences: (1) the growth section is described as "adapted from" Dweck, never "validated"; (2) no other wording changes, ever — one swapped word keeps the adaptation honest; (3) any further edit is a new instrument version.
- Granularity note: three items on a 6-point scale give only 16 possible section scores (steps of ~6.7 points). That is fine; never display more precision than a whole number.
- Credit line (footer + PDF): "Growth mindset items adapted from Dweck, C. S. (2006). *Mindset: The New Psychology of Success.* Random House. Scale distributed by Stanford SPARQ."
### 4.3 Section B — Stress mindset (`stress`)
- Source: Stress Mindset Measure, adult/general version (Crum, Salovey & Achor 2013), from the Stanford Mind & Body Lab: https://mbl.stanford.edu/resources/measures/stress-mindset-measure-adult-version (the instructions doc with all eight items is linked there).
- Permission: the lab states the measure is copyrighted but that researchers, practitioners, and students may use it without permission provided the authors are credited. We are using it as practitioners, with credit. No further permission needed.
- Items: **[FILL]** — paste the eight items verbatim from the lab's document. The four "stress is debilitating" items (marked with an asterisk in the source) are `lower_is_better`; the four "stress is enhancing" items are `higher_is_better`.
- Scale: 5-point agreement, values 0–4: 0 strongly disagree → 4 strongly agree. Section score = mean of the eight after direction handling, normalized to 0–100. Higher = stress-is-enhancing mindset.
- Credit line (footer + PDF), exactly as the lab requests: "Stress mindset items: Crum, A. J., Salovey, P., & Achor, S. (2013). Rethinking stress: The role of mindsets in determining the stress response. *Journal of Personality and Social Psychology, 104*(4), 716."
### 4.4 Section C — Learner actions (`actions`) — v1.0 draft, ours to edit
Intro shown once before the section:
> Think about the last 30 days — work, sport, hobbies, parenting, anything you're trying to get better at. How often did you…
| id | Item text | behavior key | direction |
|---|---|---|---|
| a1 | Choose the harder option when an easier one would have gotten the job done? | `challenge` | higher_is_better |
| a2 | Do something you're not good at *yet* in front of other people? | `arena` | higher_is_better |
| a3 | Ask someone directly for feedback on how you could improve? | `feedback` | higher_is_better |
| a4 | Try a new way of doing something you already do well? | `experiment` | higher_is_better |
| a5 | After something went badly, take time to figure out what you'd do differently? | `reflect` | higher_is_better |
| a6 | Explain something you're still learning to someone else? | `teach` | higher_is_better |
| a7 | Use a coach, course, book, or expert specifically to get better at something? | `resources` | higher_is_better |
| a8 | Pass on a chance to do something because you weren't sure you'd be good at it? | `avoidance` | lower_is_better |
Scale: 5-point frequency, values 0–4: Never / Almost never / Sometimes / Fairly often / Very often.
Each `behavior` key maps to content links (§9). Optional ninth item if we want a second reverse-scored check: "Stick with the safe, familiar way even when a chance to stretch was right there?" (`comfort`, lower_is_better).
### 4.5 The bonus choice (stored, not scored)
Shown as the final screen before the email gate:
> One more thing. Pick your bonus:
> **A.** Three quick tips you can use today.
> **B.** One hard exercise most people quit.
Store `bonus_choice: "easy" | "hard"`. Do **not** include it in any score. Deliver the chosen bonus on the results page (`content/bonus-easy.md`, `content/bonus-hard.md`, both `[FILL]`). It is a behavioral challenge-seeking measure and our built-in validity check: the admin dashboard compares mean `actions` score by bonus choice.
### 4.6 Question order
Sections in order: growth → stress → actions → bonus. Items within a section in config order (no randomization in v1). Total ≈ 24 items + 1 choice. Target completion time: under 3 minutes.
---
## 5. Scoring (server-side, unit-tested)
For each item: normalize the answer to 0–1 "toward learner."
```
n = (answer - scale.min) / (scale.max - scale.min)
if direction == lower_is_better: n = 1 - n
```
Section score = mean of its items' normalized values × 100. Store two decimals; display as a whole number.
**Overall Learner Score** = mean of the three section scores, rounded to a whole number. (Equal weights. A geometric-mean variant that rewards balance is a possible v2 — keep the arithmetic mean as the only scoring path in v1, but structure the code so the aggregator is one swappable function.)
Also compute and store:
- `weakest`: the section with the lowest score. Tie-break order: `actions`, then `stress`, then `growth` (bias toward the most actionable content).
- `behavior_scores`: each of the eight action items as 0–100 (after direction handling).
- `lowest_behaviors`: the two lowest `behavior_scores` (used for "your two reps to add").
- `bands`: per section and overall, using thresholds from `config/bands.json`.
- `profile`: from `config/profiles.json` (see §6).
Every response stores the raw answers array, so all of the above can be recomputed later if config changes.
**Percentiles (phase 4):** once a section has ≥ 300 completed responses on the current instrument version (`config/norms.json → min_n`), display each score's percentile ("higher than 71% of people who've taken this"). Percentile = share of stored scores strictly below this one. Raw 0–100 is always stored and remains the underlying number; percentiles are a display layer and an optional axis mode for the radar.
---
## 6. Bands and profiles (all in config)
`config/bands.json` — default thresholds, same for every section in v1:
| band | range | name |
|---|---|---|
| `low` | 0–49 | `[FILL]` |
| `mid` | 50–74 | `[FILL]` |
| `high` | 75–100 | `[FILL]` |
`config/profiles.json` — evaluated top to bottom, first match wins. Defaults to be tuned once real data exists:
| key | rule | working name (Trevor to rename) |
|---|---|---|
| `learner_mode` | all three sections ≥ 70 | Learner Mode |
| `believer` | `actions` is weakest AND (mean of growth + stress) − actions ≥ 15 | Believer (knows it, isn't doing the reps) |
| `grinder` | `stress` is weakest AND `actions` ≥ 60 | Grinder (does the reps, dreads the stress) |
| `doubter` | `growth` is weakest | Doubter (hasn't bought the premise yet) |
| `builder` | everything else | Builder (mid across the board) |
Each profile has a copy file (§10) and a Mailchimp tag (§8).
---
## 7. Pages, flow, and data model
### 7.1 Routes
| Route | Purpose |
|---|---|
| `/` | Landing. Headline, "3 minutes," what you get, one button: **Start**. No email here. Captures UTM params + referrer into the session. |
| `/quiz` | The instrument. One item per screen, progress rule at top, back button, keyboard 1–6, draft autosaved to `localStorage` so a refresh doesn't lose progress. Section intros between sections. |
| `/quiz/finish` | Email gate: first name (optional), email (required), newsletter consent checkbox, privacy link, Turnstile. Button: **Show my results**. |
| `/r/[id]` | Results. Permanent, public (unguessable id). See §7.3. |
| `/r/[id]/pdf` | Streams the PDF report (phase 4). |
| `/api/submit` | POST answers + email + consent → scores → DB → Mailchimp → Resend → returns `{ id }`. |
| `/api/og/[id]` | Share image PNG (1200×630; `?format=square` for 1080×1080). |
| `/api/cron/norms` | Nightly percentile tables (phase 4). Protected by `CRON_SECRET`. |
| `/admin` | Basic-auth dashboard (phase 4). |
| `/privacy` | Link to `[FILL: privacy policy URL]` (can be the main site's). |
Session tracking: a `quiz_sessions` row is created on `/quiz` start (anonymous `session_id` cookie), updated with `last_item_index` as they answer, so drop-off per question is measurable without PostHog.
### 7.2 Tables (Drizzle)
```
quiz_sessions
  id (uuid pk), started_at, last_item_index int, completed bool,
  utm_source, utm_medium, utm_campaign, utm_content, referrer, user_agent, country
subscribers
  id (uuid pk), email (unique, lowercased), first_name,
  consent_newsletter bool, consent_at, consent_country,
  mailchimp_status text, mailchimp_synced_at,
  first_response_at, response_count int
responses
  id (text pk, nanoid 12, url-safe), created_at,
  session_id fk, subscriber_id fk,
  instrument_version text,
  answers jsonb            -- [{ item_id, value }]
  section_scores jsonb     -- { growth, stress, actions } (0–100, 2dp)
  overall_score int,
  behavior_scores jsonb,   -- { challenge, arena, feedback, ... }
  weakest text, lowest_behaviors text[],
  bands jsonb, profile text,
  bonus_choice text,
  percentiles jsonb null,  -- snapshot at view time once norms exist
  team_code text null      -- phase 5
norms
  instrument_version, section, computed_at, n int, distribution jsonb  -- sorted scores or a 101-bucket histogram
email_events
  id, response_id fk, type ('results_sent' | 'send_failed'), provider_id, created_at, error text
```
### 7.3 Results page (`/r/[id]`) — top to bottom
1. **Learner Score**: the overall number, large. The band name beneath it.
2. **Learner Shape**: the radar. Three axes (growth, stress, actions), 0–100, equilateral triangle, filled with the accent color at low opacity, stroked in ink. Axis labels outside the corners with each score. Once norms exist: a faint dashed "average" triangle underneath, and a toggle for raw vs percentile axes. On a retake (same subscriber, ≥ 2 responses): the previous shape drawn as a dashed outline, with deltas per axis.
3. **Three measures**: one short block each — score, band, the copy for that section × band (§10).
4. **Your reps**: horizontal bars for the eight behaviors, sorted lowest to highest, each labeled in plain language. The two lowest are flagged "add this rep" with a link each.
5. **Biggest opportunity**: a card for `weakest`, with 2–3 content links from §9, the profile copy, and a note about the book where relevant.
6. **Your bonus**: whichever they picked, with one line noting what the choice tends to say about people (light touch, never scolding).
7. **Share**: buttons for LinkedIn, X, copy link, and download image. Uses the OG image.
8. **Download your report** (PDF, phase 4) and **Retake in 30 days** (explains that scores move; we'll email a reminder).
9. Footer: the two credit lines from §4.2 and §4.3 verbatim, plus "Learner actions developed by The Learner Lab," plus the privacy link. The same credits appear in the PDF and the results email.
The page must render fully server-side (no loading spinners for the core content) and look right at 360px wide.
---
## 8. Mailchimp (Marketing API v3)
Env: `MAILCHIMP_API_KEY`, `MAILCHIMP_SERVER_PREFIX` (e.g. `us21`), `MAILCHIMP_AUDIENCE_ID`.
On every completed submission with `consent_newsletter = true`:
1. **Upsert member**: `PUT /3.0/lists/{audience}/members/{md5(lowercase email)}` with `status_if_new: "subscribed"` (`[FILL: or "pending" if Trevor wants double opt-in]`), `email_address`, and `merge_fields`.
2. **Apply tags**: `POST /3.0/lists/{audience}/members/{hash}/tags`.
Merge fields (create in Mailchimp first; tag names ≤ 10 chars):
| merge tag | value |
|---|---|
| `FNAME` | first name |
| `LSCORE` | overall score |
| `LSGROWTH` | growth score |
| `LSSTRESS` | stress score |
| `LSACTION` | actions score |
| `LSPROFILE` | profile key |
| `LSWEAK` | weakest section key |
| `LSURL` | results URL |
| `LSDATE` | completion date (YYYY-MM-DD) |
| `LSCOUNT` | number of times taken |
Tags:
- `learner-score` (everyone)
- `ls-profile:<profile>` — remove any previous `ls-profile:*` tag on retake
- `ls-weakest:<section>` — same
- `ls-band:<low|mid|high>` — same
- `ls-retake` — added on the second and later completions
Mailchimp then owns the nurture: one Customer Journey per `ls-weakest:*` tag (content for that area), plus a journey with a 30-day delay that sends the retake reminder. Those are built in Mailchimp by Trevor; this app only sets tags.
Rules:
- Mailchimp failures never block results. Log to `email_events`, retry once, show results anyway.
- If the member is `unsubscribed`, `cleaned`, or `archived`, do not change their status. Update merge fields only if the API allows; otherwise log and move on.
- Without consent: no Mailchimp call at all. They still get the results email (transactional) and the results page.
- Never send the raw answers to Mailchimp.
**Consent default (decide before launch):** the checkbox reads "Also send me The Learner Lab newsletter." Recommended: pre-checked for visitors outside the EU/UK, unchecked for EU/UK (use Vercel's `x-vercel-ip-country` header). `[FILL: confirm]`
---
## 9. Content links
`config/content.json` — Trevor's content library tagged by what it helps with. The results page pulls from it; nothing is hardcoded.
```json
[
  {
    "title": "[FILL]",
    "url": "https://thelearnerlab.com/[FILL]",
    "format": "video | article | podcast | essay | book-chapter",
    "section": "growth | stress | actions | null",
    "behavior": "challenge | arena | feedback | experiment | reflect | teach | resources | avoidance | null",
    "band": "low | mid | high | null",
    "priority": 1
  }
]
```
Selection rules: for the biggest-opportunity card, filter by `section = weakest` (and `band` if set), sort by priority, take 3. For each of the two lowest behaviors, filter by `behavior`, take 1. Never show the same link twice on a page. If nothing matches, fall back to `section` with `band = null`, then to a default link `[FILL]`.
---
## 10. Copy bank
All results copy lives in `content/copy/` as Markdown, one file each:
- `profile-<key>.md` (5 files)
- `<section>-<band>.md` (9 files: growth/stress/actions × low/mid/high)
- `behavior-<key>.md` (8 short files: one or two lines each, "what this rep is and why it matters")
- `bonus-easy.md`, `bonus-hard.md`
- `email-results.md` (the transactional email body, with `{{score}}`, `{{first_name}}`, `{{results_url}}`, `{{weakest_name}}` placeholders)
All `[FILL]` by Trevor. Until filled, use clearly marked placeholder text — never ship generated copy in his voice.
**Voice guide:** short, punchy sentences. First person. Direct and unpretentious. Show, then label. No corporate vocabulary ("leverage," "unlock," "journey"). Talk to one person. Never shame a low score — a low score is information, and the whole premise is that it moves.
---
## 11. Email (Resend)
Env: `RESEND_API_KEY`, `EMAIL_FROM` (`[FILL: e.g. trevor@thelearnerlab.com]`, domain verified with SPF/DKIM), `EMAIL_REPLY_TO`.
Send from **thelearnerlab.com**, not learnerreport.com. A brand-new domain has no sending reputation and its mail will land in spam; the established domain already has one. The email can still link to learnerreport.com.
One transactional email, sent immediately on submission:
- Subject: `Your Learner Score: {{score}}`
- Body: greeting, the score and band, the Learner Shape as an `<img>` pointing at `/api/og/[id]?format=email`, the three section scores, the biggest-opportunity paragraph with two links, a button **See your full results**, a line about retaking in 30 days. Plain HTML, table-based layout, no web fonts required (fall back gracefully), looks fine in Gmail on a phone.
- Log every attempt in `email_events`.
The newsletter and all follow-ups come from Mailchimp, never from this app.
---
## 12. Later phases (do not build in v1)
- **Percentiles / norms** (phase 4): nightly cron per section on the current instrument version.
- **Admin dashboard** (phase 4): completions, completion rate, drop-off per item, score histograms per section, item mean and SD (flag any item with SD < 0.8 — it isn't discriminating), mean `actions` score by bonus choice, retake count, CSV export. Basic auth via `ADMIN_PASSWORD`.
- **PDF report** (phase 4): same content as the results page, generated on demand, cached.
- **Team version** (phase 5): `teams` table (code, name, owner_email); `/t/[code]` starts a quiz tagged with the team; `/team/[code]` shows the owner an aggregate: average shape vs global, distribution, weakest areas — anonymized, hidden until n ≥ 5. Intended as a pre-workshop tool.
- **Geometric-mean score** as a "Learner Score 2.0" option.
---
## 13. Build phases and acceptance
Commit at the end of each phase. Do not start the next phase until the acceptance list passes.
**Phase 1 — Instrument, scoring, results with seed data (no DB, no email)**
- `config/instrument.json` validated by zod; `[FILL]` items present as placeholders.
- Scoring module with unit tests: normalization, reverse items, section means, overall rounding, weakest tie-break, profile rules, band assignment.
- `scripts/seed.ts` generates 500 realistic fake responses (mindsets skew high, actions spread lower) into a local JSON file.
- `/quiz` works end to end on a phone, with draft autosave.
- `/r/[id]` renders from seed data with the real Learner Shape, bars, and placeholder copy.
- Lighthouse mobile ≥ 90 performance, ≥ 95 accessibility.
**Phase 2 — Database, email gate, Mailchimp**
- Drizzle schema + migrations; `/api/submit` stores sessions, subscribers, responses.
- Turnstile + rate limiting on submit.
- Mailchimp upsert + tags with the failure rules in §8. Tested against a Mailchimp test audience.
- Consent stored with timestamp and country.
**Phase 3 — Results email and share images**
- Resend email per §11, logged in `email_events`.
- `/api/og/[id]` in three formats; share buttons on the results page.
- UTM + referrer captured on `/` and persisted through to `responses`.
- PostHog events: `quiz_started`, `item_answered` (index), `gate_viewed`, `email_submitted`, `results_viewed`, `share_clicked`, `link_clicked`, `retake_started`. No emails or answers in event properties; use the hashed subscriber id.
**Phase 4 — Norms, admin, PDF** (see §12)
**Phase 5 — Team version** (see §12)
---
## 14. Design direction
The main site (thelearnerlab.com) is an editorial, magazine-style build: cream / ink / yellow palette, Fraunces (display), Libre Franklin (body and UI), Caveat (handwritten accents). This app is the same house on its own address, not a generic quiz app: same palette and type, a small "by The Learner Lab" mark in the header and footer.
**Tokens** — pull exact values from the site's theme CSS and put them in `tailwind.config.ts`:
| token | role | value |
|---|---|---|
| `cream` | page background | `[FILL]` |
| `ink` | text, strokes | `[FILL]` |
| `ink-muted` | secondary text, rules | `[FILL]` |
| `yellow` | the one accent: shape fill, highlights, primary button | `[FILL]` |
| `rule` | hairlines | `[FILL]` |
Type: Fraunces for the score and headings only; Libre Franklin for everything else; Caveat only for hand-drawn annotations (an arrow and a few words next to the shape: "your biggest opportunity"). Caveat is the signature, not the wallpaper — three uses per page, maximum.
**Signature element:** the Learner Shape, drawn like a figure in a scientific textbook — thin ink axes, a small tick scale, the filled triangle, a caption in italics beneath — with one handwritten annotation. Everything else on the page is quiet.
**Do not:** use drop-shadowed cards, gradients, progress rings, confetti, emoji, or a second accent color. No animation beyond a single reveal of the shape on the results page (respect `prefers-reduced-motion`). The quiz screens are large type on cream, five answer buttons, a thin progress rule, nothing else.
**Copy in the interface:** sentence case; buttons say what they do ("Start," "Show my results," "Copy link"); errors say what happened and what to do; the empty state before results is never blank.
---
## 15. Working agreements
- Read this file first every session. Ask about anything ambiguous before building it.
- Ask before adding a dependency not listed in §2.
- Config and content are data; if you find yourself hardcoding an item, a threshold, a link, or a paragraph, stop and move it to config.
- Scoring changes require updated tests in the same commit.
- Never compute or expose scores client-side; never expose raw answers on any public route.
- Keep `.env.example` current: `DATABASE_URL`, `MAILCHIMP_API_KEY`, `MAILCHIMP_SERVER_PREFIX`, `MAILCHIMP_AUDIENCE_ID`, `RESEND_API_KEY`, `EMAIL_FROM`, `EMAIL_REPLY_TO`, `NEXT_PUBLIC_SITE_URL`, `TURNSTILE_SITE_KEY`, `TURNSTILE_SECRET_KEY`, `NEXT_PUBLIC_POSTHOG_KEY`, `ADMIN_PASSWORD`, `CRON_SECRET`.
- Bump `instrument_version` for any change to item text, count, order, or scale. Norms are per version.
- Mobile first, keyboard accessible, visible focus states, reduced motion respected. No exceptions.
- When in doubt, cut the feature. The score, the shape, the link, the email. That's the product.
---
## 16. Open items Trevor owes before launch
- [ ] Growth mindset items + directions (§4.2)
- [ ] Stress mindset items + directions (§4.3)
- [ ] Final name for the third measure (§1) and any wording edits to a1–a8 (§4.4)
- [ ] Band names and profile names (§6)
- [ ] Bonus content: easy and hard (§4.5)
- [ ] Copy bank: 5 profile files, 9 section × band files, 8 behavior lines, results email (§10)
- [ ] `config/content.json`: content library tagged by section / behavior / band (§9)
- [ ] Design tokens from the theme CSS (§14)
- [ ] Mailchimp: audience id, merge fields created, double opt-in decision, consent default (§8)
- [ ] Resend: sender address and domain verification (§11)
- [ ] Privacy policy URL (§7.1)
- [ ] Permissions: Stress Mindset Measure is cleared for practitioner use with credit (§4.3). The Growth Mindset Scale is distributed free by Stanford SPARQ; a one-line courtesy note to Dweck's office is optional, not a blocker.
- [ ] Lock items 1.0 and pilot with ~25 people before public launch; review item spread and bonus-choice split in the admin dashboard
