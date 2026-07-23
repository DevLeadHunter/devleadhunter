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

Generate temporary client websites from templates (14-day hosting on `demo.dibodev.fr/{slug}`):

- Dashboard stepper: `/dashboard/demo-sites/create`
- API: `POST /api/v1/demo-sites`
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
