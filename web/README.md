# TaitaLumi Web

Vue 3 SPA for the TaitaLumi dictionary.

## Setup

### 1. Install dependencies

```bash
cd website/web
npm install
```

### 2. Configure environment

```bash
cp .env.example .env
```

Leave `VITE_API_BASE_URL` empty in dev — Vite proxies `/api/*` to `localhost:8000`
for you. In production, set it to your deployed API URL.

### 3. Run the dev server

```bash
npm run dev
```

App runs at http://localhost:5173

### 4. Build for production

```bash
npm run build
```

Output goes to `dist/`. Deploy this to Netlify.

## Project structure

```
web/
├── public/
│   └── favicon.svg
├── src/
│   ├── api/
│   │   └── client.js          — Axios instance with JWT interceptor
│   ├── assets/
│   │   └── main.css           — Tailwind entry
│   ├── components/
│   │   ├── AppNavbar.vue       — Top nav with route links
│   │   ├── AppFooter.vue       — Footer
│   │   └── PlaceholderPage.vue — Reusable "coming in Phase X" page
│   ├── pages/
│   │   ├── Home.vue           — Real page, calls /api/health
│   │   ├── Search.vue         — Placeholder (Phase 1)
│   │   ├── WordDetail.vue     — Placeholder (Phase 1)
│   │   ├── Suggest.vue        — Placeholder (Phase 3)
│   │   ├── Suggestions.vue    — Placeholder (Phase 3)
│   │   ├── SuggestionDetail.vue — Placeholder (Phase 3)
│   │   ├── Login.vue          — Placeholder (Phase 2)
│   │   ├── ReadingGuide.vue   — Placeholder (Phase 1)
│   │   ├── Donate.vue         — Placeholder (Phase 1)
│   │   ├── Profile.vue        — Placeholder (Phase 2)
│   │   ├── Admin.vue          — Placeholder (Phase 6)
│   │   └── NotFound.vue       — 404 page
│   ├── router/
│   │   └── index.js           — Vue Router with all routes
│   ├── stores/
│   │   └── auth.js            — Pinia auth store (stub for Phase 2)
│   ├── App.vue                — App shell (Navbar + RouterView + Footer)
│   └── main.js                — App bootstrap (Pinia + Router)
├── index.html
├── package.json
├── postcss.config.js
├── tailwind.config.js
├── vite.config.js
└── .env.example
```

## What's wired up

- **Tailwind** with the Taita earth palette from the mockup
- **Vue Router** with 11 routes (all 8 mockup pages + profile + admin + 404)
- **Pinia** for state management (auth store stub)
- **Axios** with JWT interceptor (reads `taitalumi_token` from localStorage)
- **Home page** calls `GET /api/health` and shows a green/orange/red dot
  based on whether the API is reachable — this is the Phase 0b proof
  that the frontend talks to the backend.

## What's a placeholder

Every page except Home is a stub that shows the page title, the phase it'll
be built in, and a link to the mockup for the intended design. This is
deliberate — Phase 0b is just the scaffold. Real implementations come in
later phases.

## Verification (Phase 0b success criteria)

1. `npm install` succeeds
2. `npm run dev` starts the Vite server on :5173
3. Home page loads, shows the TaitaLumi hero and Word of the Day placeholder
4. The API health dot at the bottom of Home turns green
   (requires the FastAPI app running on :8000)
5. Clicking nav links (Browse, Suggest, etc.) shows placeholder pages
6. `npm run build` produces a `dist/` folder without errors

## Next steps

- **Phase 0c:** Deploy both apps (Render for API, Netlify for SPA)
- **Phase 1:** Implement real Search, WordDetail, ReadingGuide, Donate
