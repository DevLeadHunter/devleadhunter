# devleadhunter - Frontend

Personal prospect research tool for freelance web developers. Built with Nuxt.js 4 and strict TypeScript.

## Features

- 🔐 Authentication (Login, Signup)
- 🔍 Prospect Search with filters (category, city, max results)
- 📧 Email Campaigns (create, manage, bulk send)
- 👤 User Profile Management
- 📱 Fully Responsive Design
- 🎨 Light & dark "Atelier" theme (black & white brand)

## Tech Stack

- **Framework**: Nuxt.js 4
- **Language**: TypeScript (strict mode)
- **State Management**: Pinia
- **Styling**: TailwindCSS v4
- **Icons**: Nuxt Icon
- **Desktop**: Tauri

## Project Structure

```
app/
├── assets/css/       # Design tokens (@theme) and global styles
├── components/       # ui/, demo-sites/ and dashboard/ carry an auto-import prefix
├── composables/      # Reusable composables
├── constants/        # Typed constant data
├── layouts/          # Layout components
├── middleware/       # Route middleware (auth)
├── pages/            # Application pages
├── plugins/          # Nuxt plugins
├── services/         # API service classes
├── stores/           # Pinia stores
├── types/            # TypeScript types — one file per component
└── utils/            # Pure helpers
public/               # Static assets
src-tauri/            # Desktop shell
```

## Getting Started

### Prerequisites

- Node.js 18+
- npm or pnpm

### Installation

```bash
# Install dependencies
npm install

# Start development server
npm run dev

# Build for production
npm run build

# Preview production build
npm run preview
```

### Environment Variables

Create a `.env` file in the root directory:

```env
API_BASE_URL=http://localhost:8000
```

## Development

### TypeScript

This project uses strict TypeScript. Every variable, prop, ref, computed, etc., must be strictly typed.

Example:

```typescript
const myRef: Ref<string> = ref('')
```

### Styling

- TailwindCSS v4, with the design tokens declared in the `@theme` block of `app/assets/css/main.css`
- Light and dark are both first-class: every surface must be checked in the two themes

### State Management

Pinia stores in `app/stores/`:

- `user` - Authentication and user data
- `prospectSearch` - Prospect search results and filters
- `campaigns` - Email campaigns
- `automations` - Automation rules and send policy
- `coverage` - Coverage map zones
- `drawerStack` - Stack of open drawers

### API Integration

Every call goes through a service class in `app/services/`, each wrapping `ApiClient`
(`app/services/api.ts`) — no component calls `$fetch` directly. The backend is mounted
under `/api/v1`; see `api/api/v1/routes/` for the authoritative endpoint list.

## Contributing

When contributing to this project, ensure:

1. All code is strictly typed
2. Add JSDoc comments to all functions, classes, and components
3. Follow [`STANDARDS_CODE_ET_ARCHITECTURE.md`](./STANDARDS_CODE_ET_ARCHITECTURE.md) — it is the source of truth
4. `npm run lint` must pass (Prettier, ESLint and the typecheck)

## License

MIT
