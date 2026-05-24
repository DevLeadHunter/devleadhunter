# DevLeadHunter

**Personal prospect research tool for freelance web developers**

Full-stack application for finding and managing business prospects without websites.

## Architecture

```
.
├── web/     # Nuxt 4 frontend (+ Tauri desktop shell)
└── api/     # FastAPI backend
```

## Stack

| Layer    | Technology                          |
| -------- | ----------------------------------- |
| Frontend | Nuxt 4, Vue 3.5, TypeScript (strict) |
| Backend  | FastAPI, Pydantic v2, SQLAlchemy    |
| Desktop  | Tauri 2 + static Nuxt generate      |
| State    | Pinia                               |
| Styling  | TailwindCSS                         |

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
playwright install chromium
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

Required GitHub secrets (same pattern as GoupixDex):

- `TAURI_UPDATER_PUBKEY`
- `TAURI_SIGNING_PRIVATE_KEY`
- `TAURI_SIGNING_PRIVATE_KEY_PASSWORD`
- `NUXT_PUBLIC_API_BASE`

## Code quality

Standards: [`STANDARDS_CODE_ET_ARCHITECTURE.md`](./STANDARDS_CODE_ET_ARCHITECTURE.md)

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
