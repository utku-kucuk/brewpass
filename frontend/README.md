# BrewPass Web

React 19 + TypeScript + Vite client. In development `/api` is proxied to the gateway on `:8080` (`docker compose up`).

```bash
npm install
npm run dev            # http://localhost:5173
npm test               # Vitest + Testing Library
npm run lint && npm run format:check && npm run build
```

## Structure

| Path | What |
| ---- | ---- |
| `src/styles/tokens.css` | Brand tokens (Espresso & Terracotta palette, Fraunces / Inter, spacing, radius), light and dark |
| `src/lib/api.ts` | `api()` client: unwraps the `{success, data, error}` envelope, throws `ApiError`, attaches the access token and refreshes it once on 401 (shared across concurrent requests) |
| `src/lib/auth-store.ts` | Session state (Zustand, persisted) |
| `src/api/*` | Typed endpoint functions |
| `src/components/ui` | Button, TextField, Card, Spinner, Logo, Loading / Error / Empty states |
| `src/components/layout` | App shell (header nav on desktop, bottom tabs on mobile, skip link) and route guards |
| `src/pages` | Sign-in (phone → code), welcome (profile completion), home, profile, 404 |

Server state uses TanStack Query; 4xx errors are not retried. Routes that need a session redirect to `/sign-in?next=…`, and members without a name go through `/welcome` first.

## Accessibility

Labels and error messages are tied to inputs (`aria-describedby`, `aria-invalid`), errors use `role="alert"`, loading uses `role="status"`, a skip link jumps to the main content, focus rings are always visible, motion respects `prefers-reduced-motion`, and button and link colours meet WCAG AA contrast in both themes.
