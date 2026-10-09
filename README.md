# DevLeadHunter

**End-to-end prospecting automation for freelance web developers**

DevLeadHunter finds local businesses without a website, enriches their public data
(photos, reviews, hours), generates a real demo website in their name (Storyblok CMS,
one template repo per trade), reaches out by A/B cold email with throttled follow-ups,
tracks prospect behaviour (PostHog + lead scoring), and closes the sale via Stripe —
the delivered site then goes live on the client's own domain (Vercel). Teams can work
together: the prospect list is shared inside an organization, with per-member
reservations to avoid double outreach.

## Architecture

```
.
├── web/         # Nuxt 4 dashboard (+ landing) — Tauri desktop shell
├── api/         # FastAPI backend (scraping, campaigns, Storyblok, Stripe, orgs)
├── demo-host/   # Nuxt renderer for prospect demo sites (Vercel → demo.dibodev.fr)
└── docs/        # Documentation produit & technique
```

Website templates live in **separate GitHub repos** (`devleadhunter-template-<id>`),
consumed by `demo-host` via `extends` pinned by tag — see
[`docs/TEMPLATES_ARCHITECTURE.md`](./docs/TEMPLATES_ARCHITECTURE.md).

The second sellable product, the per-prospect multilingual **AI assistant**, is documented in
[`docs/ASSISTANT_MODULE.md`](./docs/ASSISTANT_MODULE.md).

## Stack

| Layer    | Technology                            |
| -------- | ------------------------------------- |
| Frontend | Nuxt 4, Vue 3.5, TypeScript (strict), Pinia, TailwindCSS v4 |
| Backend  | FastAPI, Pydantic v2, SQLAlchemy, MySQL |
| Desktop  | Tauri 2 + static Nuxt generate (auto-updater CI) |
| Scraping | nodriver (driven Chrome), BrightData  |
| CMS      | Storyblok (one space per client, publish webhook → content sync) |
| Email    | Resend (A/B campaigns, RFC 8058 unsubscribe), Gmail OAuth |
| Payments | Stripe (payment links + webhooks)     |
| Tracking | PostHog (demo behaviour → lead scoring, Groq AI summaries) |
| Hosting  | Vercel (demo host + delivered client sites by domain) |

## Prerequisites

- Node.js 22+
- Python 3.11+
- Rust stable (desktop builds only)

## Installation

```bash
# Frontend
cd web
npm install

# Backend
cd ../api
pip install -r requirements.txt
```

### Environment

`web/.env`:

```env
NUXT_PUBLIC_API_BASE=http://localhost:8000
```

`api/.env` — see `api/core/config.py` and `api/.env.example`.

## Development

```bash
# API
cd api
python main.py

# Web
cd web
npm run dev
```

- Web: http://localhost:3000
- API: http://localhost:8000 (Swagger: `/docs`)

## Desktop (Tauri)

```bash
cd web
npm run tauri:dev      # dev shell on port 1420
npm run tauri:build    # local release build
```

Desktop builds use `NUXT_DESKTOP_BUILD=1` (SSR off, static preset). The app talks to the remote API configured via `NUXT_PUBLIC_API_BASE`.

CI release workflow: `.github/workflows/desktop-release.yml` (Windows + macOS, auto-updater).

The desktop app is the PC-side worker of the prospect searches launched from any device (the iPad, a phone): it reads with the local Chrome the Facebook pages a search waits for. So it starts with Windows hidden in the notification area (`--minimized`, enabled once at the first launch, a Task Manager opt-out stays respected), closing its window only hides it, and the tray icon opens or quits it (`src-tauri/src/tray.rs`). While it runs, the activity it polls marks it online (`from_desktop_app=true`), and the other devices tell whether the PC is on to read the pages.

More generally, any work only the PC can do is left for it as a **desktop job** (`desktop_jobs` table, `api/services/desktop_job_relay.py`, routes `/desktop-jobs`): a device without the app posts `{kind, subject_id}`, the app looks for waiting jobs every 20 seconds (`GET /desktop-jobs/waiting`, `web/app/stores/desktopJobRelay.ts`), claims one, does it with its local tools, saves the result through the usual routes and closes the job (`done` / `fail`); a job abandoned by a closed app is offered again after 15 minutes. First kind: `prospect_enrichment` (the enrichment drawer and the grouped enrichment of « Mes prospects » hand the work to the PC when they run in a browser; the record shows « En cours… » meanwhile, the drawer says whether the PC is on and lets the request be withdrawn).

It also builds every prospection video, of demo sites and of receptionists: the server renders none, only the PC films a site with its Storyblok editor or a receptionist answering. In the desktop app, « Générer la vidéo » builds it at once with a progress window. Any other device (the iPad, a phone) leaves a request on the site or the receptionist; the app looks for requests every 20 seconds (`web/app/stores/desktopVideoRelay.ts`, oldest first, both kinds), takes one (`desktop-claim`), builds and publishes the video (`video-final`), or reports why it could not (`desktop-failure`). A site without its Storyblok space keeps its request until the space exists (« En attente de l'espace Storyblok du site »). With the module's automatic generation on, a new demo site or receptionist leaves its request by itself. A video published before the take in use was chosen reads « Faite avec un ancien clip ». The campaign page shows where the videos of its demo sites stand, whether the PC is on, and asks for the missing ones or for all of them from any device. Server side: `api/services/prospection_video_desktop_relay.py` (relay shared by both kinds), `api/services/campaign_videos_service.py`; the migration `fail_unfinished_server_videos` marks failed the videos the old server render left pending.

- `POST /demo-sites/{id}/video/desktop-request` / `DELETE`: leave or withdraw a site's request for the PC.
- `GET /demo-sites/video/desktop-requests`: the sites waiting for the PC, with their Storyblok space; marks the PC online.
- `POST /demo-sites/{id}/video/desktop-claim`, `POST /demo-sites/{id}/video/desktop-failure`: the PC takes a site's video, or gives it up with its reason.
- `GET /demo-sites/{id}/video/state`: where a site's video stands, polled by its page.
- `POST /ai-assistants/{id}/video/desktop-request` / `DELETE`: leave or withdraw a receptionist's request for the PC.
- `GET /ai-assistants/video/desktop-requests`: the receptionists waiting for the PC; marks the PC online.
- `POST /ai-assistants/{id}/video/desktop-claim`, `POST /ai-assistants/{id}/video/desktop-failure`: the PC takes a receptionist's video, or gives it up with its reason.
- `GET /ai-assistants/{id}/video/state`: where a receptionist's video stands, polled by its page.
- `GET /campaigns/{id}/videos`: the campaign's demo sites by video state (ready, older clip, building, waiting for the PC or the Storyblok space, failed, not asked) and whether the PC is on.
- `POST /campaigns/{id}/videos/requests` (`{"redo": false}`): ask the PC for the missing videos (`redo`: all of them); returns the count asked and the sites left aside with their reason.
- `demo_sites.video_desktop_requested_at`, `ai_assistants.video_desktop_requested_at`: when the video was asked from the PC, null once built, given up or withdrawn.
- `presenter_videos.in_use_since`: when the take was chosen for its module; a video published before it was made with an older clip.

## Installed app (PWA)

Installed from Safari or Chrome (« Sur l'écran d'accueil »), the dashboard opens on `/dashboard` with a bottom tab bar on phones, on iPads in portrait and on any touch screen: Campagnes, Notifications, the large « Rechercher des leads » button, Suivi des emails, Suivi des SMS. Pulling a page down from its top reloads it, the status bar takes the header's colour in both themes, and the session token renews itself twice a day while the app is used.

## Code quality

| Module | Standards |
| ------ | --------- |
| Web | [`web/STANDARDS_CODE_ET_ARCHITECTURE.md`](./web/STANDARDS_CODE_ET_ARCHITECTURE.md) |
| API | [`api/STANDARDS_CODE_ET_ARCHITECTURE.md`](./api/STANDARDS_CODE_ET_ARCHITECTURE.md) |
| Demo host | [`demo-host/STANDARDS_CODE_ET_ARCHITECTURE.md`](./demo-host/STANDARDS_CODE_ET_ARCHITECTURE.md) |

```bash
cd web
npm run lint        # prettier + eslint + vue-tsc
npm run lint:fix
```

Pre-commit hook (root): `npm --prefix web run lint`

## Demo site builder

Generate temporary client websites from templates (online on `demo.dibodev.fr/{slug}` for 21 days after the link is first sent):

- Dashboard stepper: `/dashboard/demo-sites/create`
- API: `POST /api/v1/demo-sites`
- Automatic personalisation: every craft site is written at creation in the business's own words and photos (hero sentence, « À propos », service cards, realizations, photo slots), from its enrichment and the vision labels of its photos (`MISTRAL_API_KEY`, Groq as fallback); `POST /api/v1/demo-sites/{id}/personalize` (« Plus » panel of the site page) writes a new proposal
- Public renderer: `demo-host/` (deploy to Vercel → `demo.dibodev.fr`)
- Storyblok: set `STORYBLOK_MANAGEMENT_TOKEN` on the API for live CMS spaces

```bash
# Create / upgrade DB schema
cd api && python migrations/run_migrations.py

# Run demo host locally
cd demo-host && npm install && npm run dev
```

## License

MIT
