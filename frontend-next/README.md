# Muset - AI Learning Roadmap Frontend

A modern, personalized learning roadmap application built with Next.js 14, featuring AI-powered curriculum generation and an elegant Editorial Cream & Sage design system.

## Tech Stack

| Category | Technology |
|:---------|:-----------|
| Framework | Next.js 14 (App Router) |
| Language | TypeScript |
| UI Components | Shadcn/ui + Tailwind CSS |
| State Management | Zustand |
| Data Fetching | TanStack Query v5 |
| Streaming | Native SSE (Server-Sent Events) |
| Styling | Tailwind CSS + CSS Variables |

## Project Structure

```
frontend-next/
├── app/                    # Next.js App Router
│   ├── (app)/              # App route group (with AppLayout)
│   │   ├── dashboard/      # User dashboard
│   │   ├── new/            # Create new roadmap
│   │   ├── roadmap/[id]/   # Roadmap detail + learning view
│   │   └── settings/       # User settings
│   ├── methodology/        # Marketing - Methodology page
│   ├── pricing/            # Marketing - Pricing page
│   └── page.tsx            # Landing page
├── components/
│   ├── ui/                 # Shadcn/ui components
│   ├── layout/             # Layout components (AppShell, Sidebars)
│   ├── common/             # Common components (EmptyState, Spinner)
│   ├── roadmap/            # Roadmap-specific components
│   ├── learning/           # Learning view components
│   └── chat/               # AI chat components
├── lib/
│   ├── api/                # API client, SSE manager, endpoints
│   ├── store/              # Zustand stores
│   ├── hooks/              # Custom React hooks
│   └── utils.ts            # Utility functions
├── types/
│   ├── generated/          # Auto-generated from backend OpenAPI
│   └── custom/             # Frontend-specific types
└── styles/
    └── globals.css         # Global styles & CSS variables
```

## Getting Started

### Prerequisites

- Node.js 18+
- npm or pnpm
- Backend API running at http://localhost:8000

### Installation

```bash
# Install dependencies
npm install

# Generate TypeScript types from backend (requires backend to be running)
npm run generate:types

# Start development server
npm run dev
```

### Development Commands

```bash
npm run dev           # Start development server
npm run build         # Build for production
npm run start         # Start production server
npm run lint          # Run ESLint
npm run type-check    # Run TypeScript type checking
npm run generate:types # Generate types from backend OpenAPI schema
```

## Design System

This project uses the **Editorial Cream & Sage** design system:

- **Typography**: Playfair Display (headings) + Inter (body)
- **Colors**: Warm cream background (#FFFCF9) with sage green accents
- **Style**: Sophisticated, editorial, minimalist

### Key Design Tokens

```css
--background: 40 20% 99%;     /* Warm cream */
--foreground: 24 10% 10%;     /* Charcoal */
--sage: 140 15% 55%;          /* Sage green accent */
--primary: 24 10% 10%;        /* Primary = Foreground */
```

### Usage

```tsx
// Use semantic color classes
<div className="bg-background text-foreground">
  <h1 className="font-serif">Editorial Title</h1>
  <button className="bg-sage-600 text-white">Sage Button</button>
</div>
```

## Type System

Types are auto-generated from the backend OpenAPI schema using `openapi-typescript-codegen`.

### Generating Types

```bash
# Make sure backend is running at localhost:8000
npm run generate:types
```

### Using Types

```typescript
// Import generated types
import type { RoadmapFramework, Concept, LearningPreferences } from '@/types';

// Import custom frontend types
import type { ViewMode, ChatMessage } from '@/types/custom';
```

## State Management

Zustand stores are used for global state:

| Store | Purpose |
|:------|:--------|
| `useRoadmapStore` | Current roadmap data, generation state |
| `useChatStore` | AI chat messages, streaming state |
| `useUIStore` | Sidebar states, view modes, dialogs |
| `useLearningStore` | Learning progress, preferences |

### Example Usage

```typescript
import { useRoadmapStore, useUIStore } from '@/lib/store';

function MyComponent() {
  const currentRoadmap = useRoadmapStore((state) => state.currentRoadmap);
  const toggleSidebar = useUIStore((state) => state.toggleLeftSidebar);
  
  return (
    <button onClick={toggleSidebar}>Toggle Sidebar</button>
  );
}
```

## API Integration

### REST API

```typescript
import { getRoadmap, getLatestTutorial } from '@/lib/api';

// Fetch roadmap
const roadmap = await getRoadmap('roadmap-id');

// Fetch tutorial
const tutorial = await getLatestTutorial('roadmap-id', 'concept-id');
```

### SSE Streaming

```typescript
import { createGenerationStream } from '@/lib/api';

const stream = createGenerationStream(
  { user_request: { ... } },
  {
    onEvent: (event) => console.log('Event:', event),
    onComplete: () => console.log('Done'),
    onError: (error) => console.error('Error:', error),
  }
);

// Later: disconnect
stream.disconnect();
```

## Routes

| Route | Description |
|:------|:------------|
| `/` | Landing page |
| `/methodology` | Methodology explanation |
| `/pricing` | Pricing plans |
| `/app/dashboard` | User dashboard (roadmap list) |
| `/app/new` | Create new roadmap |
| `/app/roadmap/[id]` | Roadmap detail view |
| `/app/roadmap/[id]/learn/[conceptId]` | Learning view |
| `/app/settings` | User settings |

## Environment Variables

Create a `.env.local` file:

```env
NEXT_PUBLIC_API_URL=http://localhost:8000
OPENAPI_SCHEMA_URL=http://localhost:8000/openapi.json
NEXT_PUBLIC_ENABLE_DEBUG=true
```

## License

MIT

