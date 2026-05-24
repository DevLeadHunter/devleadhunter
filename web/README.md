# devleadhunter - Frontend

Personal prospect research tool for freelance web developers. Built with Nuxt.js 4 and strict TypeScript.

## Features

- 🔐 Authentication (Login, Signup)
- 🔍 Prospect Search with filters (category, city, max results)
- 📧 Email Campaigns (create, manage, bulk send)
- 👤 User Profile Management
- 📱 Fully Responsive Design
- 🌙 Dark Theme (GitHub-like)

## Tech Stack

- **Framework**: Nuxt.js 4
- **Language**: TypeScript (strict mode)
- **State Management**: Pinia
- **Styling**: TailwindCSS
- **Icons**: Nuxt Icon
- **Forms**: FormKit

## Project Structure

```
/
├── assets/
│   └── css/          # Global styles and Tailwind
├── components/
│   └── ui/           # Reusable UI components
├── composables/      # Reusable composables
├── layouts/          # Layout components
├── middleware/       # Route middleware (auth)
├── pages/            # Application pages
├── services/          # API services
├── stores/           # Pinia stores
├── types/            # TypeScript types
└── public/           # Static assets
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

- Uses TailwindCSS with custom dark theme
- Colors inspired by GitHub dark theme
- Custom utility classes in `assets/css/main.css`

### State Management

Pinia stores are used for:

- `user` - Authentication and user data
- `prospects` - Prospect search results
- `campaigns` - Email campaigns

### API Integration

All API calls go through the services layer:

- `/services/api.ts` - Base API client
- `/services/emailService.ts` - Email sending

Backend API endpoints (to be implemented):

- `POST /api/auth/login` - User login
- `POST /api/auth/signup` - User signup
- `GET /api/auth/profile` - Get user profile
- `PUT /api/auth/profile` - Update profile
- `POST /api/prospects/search` - Search prospects
- `GET /api/campaigns` - List campaigns
- `POST /api/campaigns` - Create campaign
- `PUT /api/campaigns/:id` - Update campaign
- `POST /api/emails/send` - Send individual email
- `POST /api/emails/bulk` - Send bulk emails

## Contributing

When contributing to this project, ensure:

1. All code is strictly typed
2. Add JSDoc comments to all functions, classes, and components
3. Follow the existing code structure
4. Maintain the dark theme aesthetic

## License

MIT
