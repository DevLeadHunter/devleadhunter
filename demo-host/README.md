# DevLeadHunter Demo Host

Single Nuxt app deployed once on **demo.dibodev.fr**. Each client demo is served at:

```
https://demo.dibodev.fr/{slug}
```

## How it works

1. DevLeadHunter API provisions a demo site (Storyblok space + DB record).
2. This app fetches public content from `GET /api/v1/demo-sites/public/{slug}`.
3. The plumber-simple template is rendered server-side.
4. After 14 days the API cleanup job deletes the Storyblok space and marks the site expired.

## Local development

The demo host is always served from **https://demo.dibodev.fr** (Vercel), including when developing the API locally.

1. Deploy `demo-host` to Vercel and bind `demo.dibodev.fr`.
2. Set `NUXT_PUBLIC_API_BASE` on Vercel to your public API URL.
3. Set `DEMO_HOST_BASE_URL=https://demo.dibodev.fr` in the API `.env`.

After creating a demo site in the dashboard, open:

```
https://demo.dibodev.fr/{slug}
```

Optional: run `demo-host` locally only to work on the renderer UI (`npm run dev` on port 3001). Generated demo links still use `demo.dibodev.fr`.

## Vercel deployment

Deploy this folder as a standalone Vercel project bound to `demo.dibodev.fr`.

Environment variable:

```
NUXT_PUBLIC_API_BASE=https://api.devleadhunter.dibodev.fr
```

## Storyblok

When `STORYBLOK_MANAGEMENT_TOKEN` is configured on the API, each demo gets its own Storyblok space and collaborator invite. Without the token, the API runs in mock mode and stores `content_json` locally (still rendered by this host).
