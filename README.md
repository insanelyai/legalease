# ⚖️ LegalEase — AI-Powered Indian Legal Assistant

> Making Indian law accessible to 1.4 billion people.

LegalEase is a vertical AI assistant deeply focused on three areas of Indian law — Consumer Protection, Labour & Employment, and Family Law. It gives citizens actionable legal clarity and gives lawyers a research accelerator.

[![Next.js](https://img.shields.io/badge/Next.js-14-black?logo=next.js)](https://nextjs.org/)
[![TypeScript](https://img.shields.io/badge/TypeScript-5-blue?logo=typescript)](https://www.typescriptlang.org/)
[![Prisma](https://img.shields.io/badge/Prisma-ORM-2D3748?logo=prisma)](https://www.prisma.io/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16-blue?logo=postgresql)](https://www.postgresql.org/)
[![Vercel](https://img.shields.io/badge/Deploy-Vercel-black?logo=vercel)](https://vercel.com/)

---

## Table of Contents

- [Overview](#overview)
- [Features](#features)
- [Tech Stack](#tech-stack)
- [Architecture](#architecture)
- [Database Schema](#database-schema)
- [API Reference](#api-reference)
- [AI Prompt Architecture](#ai-prompt-architecture)
- [Project Structure](#project-structure)
- [Getting Started](#getting-started)
- [Environment Variables](#environment-variables)
- [Integration Guide](#integration-guide)
- [Security & Compliance](#security--compliance)
- [Contributing](#contributing)
- [License](#license)

---

## Overview

India has **1.4 billion people** but only **~2 lawyers per 1,000 citizens**. Legal knowledge is locked behind dense Acts, court language, and unaffordable consultations. Citizens routinely lose rightful claims due to basic ignorance of their rights.

**LegalEase** solves this with two core flows:

| Flow | What it does |
|------|-------------|
| **AI Legal Chat** | Ask any legal question, get a structured answer citing real Indian statutes |
| **Document Analysis** | Upload a legal document, get a plain-language breakdown with flagged risks |

### Legal Areas

| Area | Acts & Topics Covered |
|------|----------------------|
| **Consumer Protection** | COPRA 2019, product liability, e-commerce disputes, deficiency of service, consumer forum filing |
| **Labour & Employment** | Industrial Disputes Act 1947, Payment of Wages Act, Gratuity Act, POSH Act, PF & ESI, wrongful termination |
| **Family Law** | Hindu Marriage Act 1955, Special Marriage Act, DVPA 2005, Section 125 CrPC maintenance, child custody |

---

## Features

- **AI Legal Chat** — Contextual, multi-turn chat with statute citations, streamed via SSE
- **Legal Area Selector** — User picks Consumer / Labour / Family before querying
- **Document Upload & Analysis** — PDF + DOCX upload, server-side text extraction, AI risk analysis
- **Document Risk Flagging** — Highlights unreasonable clauses, missed deadlines, and hidden obligations
- **Quick Question Chips** — Preset questions per legal area to reduce cold-start friction
- **Auth** — Email/password + Google OAuth
- **Chat History** — Persist and revisit past conversations with a sidebar
- **Hindi Language Support** — Query and respond in Hindi
- **Export to PDF** — Download chat or document analysis as a formatted PDF
- **Legal Notice Drafting** — AI-generated draft notices based on user situation
- **Usage Logging** — Anonymised action logs for observability (no PII)

---

## Tech Stack

### Frontend

| Layer | Choice | Reason |
|-------|--------|--------|
| Framework | Next.js 14 (App Router) | SSR for SEO on landing page, RSC for fast app shell |
| Language | TypeScript | Type safety is essential for a legal product |
| Styling | Tailwind CSS + shadcn/ui | Fast, consistent, accessible components |
| State | Zustand | Lightweight — no boilerplate for chat + doc state |
| File Upload | react-dropzone | Drag/drop, validation, chunked upload UX |
| PDF Preview | react-pdf | Render uploaded documents in-browser |
| Deploy | Vercel | Zero-config Next.js, edge functions, built-in analytics |

### Backend

| Layer | Choice | Reason |
|-------|--------|--------|
| Runtime | Node.js + Next.js API Routes | BFF pattern — LLM credentials never reach the client |
| AI / LLM | Any OpenAI-compatible endpoint | Works with Ollama, LM Studio, vLLM, or any local model |
| ORM | Prisma | Type-safe queries, auto-generated migrations, great DX |
| Database | PostgreSQL | Reliable, relational, supports pgvector for future RAG |
| Doc Parsing | pdf-parse + mammoth | Server-side text extraction from PDF and DOCX |
| File Storage | Local filesystem / S3-compatible | Docs stored under `/uploads/user-id/doc-id` |
| Background Jobs | Inngest / BullMQ | Async doc analysis without blocking the HTTP response |
| Rate Limiting | Upstash Redis | Per-user quota tracking |
| Email | Resend | Transactional email — OTP, alerts |

### Infrastructure

| Layer | Choice |
|-------|--------|
| Auth | NextAuth.js — email/password, Google OAuth, JWT sessions |
| Vector DB (future) | pgvector (PostgreSQL extension) for RAG on legal corpus |
| Monitoring | Sentry (errors) + Vercel Analytics + PostHog |
| CI/CD | GitHub Actions → Vercel preview deploys on every PR |

---

## Architecture

LegalEase follows a clean layered architecture. Next.js handles routing and SSR. API routes act as a secure backend-for-frontend (BFF). All LLM calls happen server-side — credentials never reach the client.

```
┌──────────────────────────────────────────────────────────┐
│                         Browser                          │
│    Next.js App (RSC + Client Components + Zustand)       │
└─────────────────────────┬────────────────────────────────┘
                          │ HTTPS / SSE
┌─────────────────────────▼────────────────────────────────┐
│               Next.js API Routes (BFF)                   │
│       Auth Middleware → Quota Check → Business Logic     │
└───────┬──────────────┬──────────────┬────────────────────┘
        │              │              │
┌───────▼──────┐ ┌─────▼──────┐ ┌────▼───────────┐
│  Local LLM   │ │ PostgreSQL │ │  Upstash Redis  │
│ (OpenAI API) │ │ via Prisma │ │  (Rate Limit +  │
│              │ │            │ │   Quota)        │
└──────────────┘ └────────────┘ └────────────────┘
                      │
               ┌──────▼──────┐
               │   Inngest   │
               │ (Async Jobs)│
               └─────────────┘
```

### AI Chat — Request Flow

```
1. Client      → POST /api/chat  { message, area, conversationId }
2. Middleware  → Validate JWT → extract userId
3. Quota Check → Redis: if quota exceeded → 429
4. Context     → Prisma: fetch last N messages → build history array
5. Prompt      → Inject area-specific system prompt from /prompts
6. LLM API     → Stream response from local model → pipe SSE to client
7. Persist     → Prisma: save user msg + AI response to messages table
8. Quota       → Increment usage counter in Redis
```

### Document Analysis — Request Flow

```
1. Upload    → POST /api/documents/upload (multipart)
2. Validate  → File type (PDF/DOCX/TXT), size ≤ 10MB
3. Store     → Save to /uploads/user-id/doc-id
4. Extract   → pdf-parse or mammoth extracts raw text
5. Chunk     → Split into ~2000-token chunks (avoid context overflow)
6. Analyse   → Send chunks to LLM with document analysis system prompt
7. Structure → LLM returns JSON: { type, keyFindings, risks, recommendations }
8. Persist   → Prisma: save analysis result to Document.analysis (Json field)
9. Respond   → Return analysis to client
```

---

## Database Schema

All models live in `prisma/schema.prisma`. Run `npx prisma migrate dev` to apply changes.

### `User`

```prisma
model User {
  id            String    @id @default(uuid())
  email         String    @unique
  fullName      String?
  passwordHash  String?
  googleId      String?   @unique
  createdAt     DateTime  @default(now())

  conversations Conversation[]
  documents     Document[]
  usageLogs     UsageLog[]
}
```

### `Conversation`

```prisma
model Conversation {
  id         String    @id @default(uuid())
  userId     String
  legalArea  String                         // consumer | labour | family
  title      String?
  createdAt  DateTime  @default(now())
  updatedAt  DateTime  @updatedAt

  user       User      @relation(fields: [userId], references: [id])
  messages   Message[]
}
```

### `Message`

```prisma
model Message {
  id               String       @id @default(uuid())
  conversationId   String
  userId           String
  role             String                   // user | assistant
  content          String
  tokensUsed       Int?
  createdAt        DateTime     @default(now())

  conversation     Conversation @relation(fields: [conversationId], references: [id])
}
```

### `Document`

```prisma
model Document {
  id             String    @id @default(uuid())
  userId         String
  legalArea      String
  fileName       String
  storagePath    String
  fileSize       Int
  mimeType       String
  extractedText  String?
  analysis       Json?                      // structured AI analysis result
  status         String    @default("pending") // pending | analyzing | done | failed
  createdAt      DateTime  @default(now())

  user           User      @relation(fields: [userId], references: [id])
}
```

### `UsageLog`

```prisma
model UsageLog {
  id         String    @id @default(uuid())
  userId     String
  action     String                         // chat_query | doc_analysis | export
  legalArea  String?
  tokensIn   Int?
  tokensOut  Int?
  createdAt  DateTime  @default(now())

  user       User      @relation(fields: [userId], references: [id])
}
```

---

## API Reference

All routes are Next.js API Routes, server-side only, protected by JWT middleware unless noted.

### Auth

| Method | Route | Description |
|--------|-------|-------------|
| `POST` | `/api/auth/signup` | Register with email + password |
| `POST` | `/api/auth/login` | Login → returns JWT |
| `GET` | `/api/auth/me` | Current user profile |
| `POST` | `/api/auth/logout` | Invalidate session |

### Chat

| Method | Route | Description |
|--------|-------|-------------|
| `POST` | `/api/chat` | Body: `{ message, area, conversationId? }` → streams SSE |
| `GET` | `/api/conversations` | List user's conversations (paginated) |
| `GET` | `/api/conversations/:id` | Single conversation with all messages |
| `DELETE` | `/api/conversations/:id` | Delete conversation + messages |

### Documents

| Method | Route | Description |
|--------|-------|-------------|
| `POST` | `/api/documents/upload` | Multipart upload → async analysis → returns `documentId` |
| `GET` | `/api/documents` | List user's documents with status |
| `GET` | `/api/documents/:id` | Single document with full analysis result |
| `DELETE` | `/api/documents/:id` | Delete record + file |
| `POST` | `/api/documents/:id/reanalyse` | Re-trigger analysis |

### Internal

| Method | Route | Description |
|--------|-------|-------------|
| `POST` | `/api/internal/analyse-doc` | Inngest background job handler for async doc analysis |

---

## AI Prompt Architecture

Each legal area has a dedicated system prompt in `/prompts`, version-controlled as TypeScript files. They can be updated by legal experts without touching application code.

### Common Rules (all areas)

- Always cite specific Act name, Section number, and Sub-section
- Give practical next steps — not just legal theory
- Distinguish between Central vs State law where applicable
- Mention the correct court or forum (District Court, High Court, Tribunal)
- Add a disclaimer when the matter needs a qualified lawyer
- **Never fabricate case law citations** — if a precedent is unknown, say so

### Document Analysis Output Schema

The LLM is instructed to return valid JSON matching this structure:

```typescript
{
  document_type: string              // e.g. "Legal Notice under COPRA 2019"
  summary: string                    // 2-3 sentence plain-language overview
  parties: { name: string; role: string }[]
  key_obligations: string[]
  critical_deadlines: { description: string; date: string }[]
  risk_flags: {
    severity: "high" | "medium" | "low"
    description: string
    clause_reference: string
  }[]
  recommended_actions: string[]
  relevant_laws: { act_name: string; section: string; relevance: string }[]
}
```

### Connecting a Local LLM

LegalEase uses the OpenAI-compatible chat completions API. Point `LLM_BASE_URL` at any compatible server:

| Runtime | Base URL |
|---------|----------|
| [Ollama](https://ollama.ai) | `http://localhost:11434/v1` |
| [LM Studio](https://lmstudio.ai) | `http://localhost:1234/v1` |
| [vLLM](https://github.com/vllm-project/vllm) | `http://localhost:8000/v1` |
| [Jan](https://jan.ai) | `http://localhost:1337/v1` |

Recommended models: `llama3`, `mistral`, `gemma2`, `phi3` — any model with strong instruction-following and at least 8K context.

---

## Project Structure

```
legalease/
├── app/                          # Next.js 14 App Router
│   ├── (auth)/                   # Login, signup pages
│   ├── (dashboard)/              # Protected app shell
│   │   ├── chat/                 # AI chat interface
│   │   └── documents/            # Upload & analysis UI
│   └── api/                      # API Routes (BFF)
│       ├── auth/
│       ├── chat/
│       ├── conversations/
│       ├── documents/
│       └── internal/
├── components/
│   ├── chat/
│   │   ├── ChatWindow.tsx
│   │   ├── MessageBubble.tsx
│   │   └── QuickChips.tsx
│   ├── documents/
│   │   ├── DropZone.tsx
│   │   ├── AnalysisCard.tsx
│   │   └── RiskBadge.tsx
│   └── ui/                       # shadcn/ui components
├── lib/
│   ├── llm.ts                    # OpenAI-compatible client (points to local model)
│   ├── auth.ts                   # JWT helpers
│   ├── redis.ts                  # Upstash quota helpers
│   └── parsers/
│       ├── pdf.ts                # pdf-parse wrapper
│       └── docx.ts               # mammoth wrapper
├── prisma/
│   ├── schema.prisma             # All models
│   └── migrations/               # Auto-generated migration files
├── prompts/                      # System prompts per legal area
│   ├── consumer.ts
│   ├── labour.ts
│   ├── family.ts
│   └── document-analysis.ts
├── store/                        # Zustand stores
│   ├── chatStore.ts
│   └── documentStore.ts
├── inngest/                      # Background job functions
│   └── analyseDocument.ts
├── types/
│   └── index.ts
└── uploads/                      # Document storage (swap with S3 as needed)
```

---

## Getting Started

### Prerequisites

- Node.js 18+
- PostgreSQL 14+ (local or remote)
- A local LLM server running an OpenAI-compatible API (e.g. Ollama)
- Upstash Redis (or a local Redis instance)

### Installation

```bash
# Clone the repository
git clone https://github.com/your-org/legalease.git
cd legalease

# Install dependencies
npm install

# Copy environment variables
cp .env.example .env.local
# → Fill in DATABASE_URL, LLM_BASE_URL, and other values

# Run Prisma migrations
npx prisma migrate dev

# (Optional) Seed the database
npx prisma db seed

# Start development server
npm run dev
```

Open [http://localhost:3000](http://localhost:3000).

### Running a Local LLM with Ollama

```bash
# Install Ollama
brew install ollama        # macOS
# or visit https://ollama.ai/download for other platforms

# Pull a model
ollama pull llama3

# Start the server — exposes OpenAI-compatible API on port 11434
ollama serve
```

Set `LLM_BASE_URL=http://localhost:11434/v1` and `LLM_MODEL=llama3` in `.env.local`.

---

## Environment Variables

```env
# Database (Prisma)
DATABASE_URL="postgresql://user:password@localhost:5432/legalease"

# Local LLM — OpenAI-compatible
LLM_BASE_URL=http://localhost:11434/v1
LLM_MODEL=llama3
LLM_API_KEY=ollama                 # Placeholder — most local servers ignore this

# Auth
NEXTAUTH_SECRET=
NEXTAUTH_URL=http://localhost:3000
GOOGLE_CLIENT_ID=
GOOGLE_CLIENT_SECRET=

# Upstash Redis (rate limiting & quota)
UPSTASH_REDIS_REST_URL=
UPSTASH_REDIS_REST_TOKEN=

# File Storage
UPLOAD_DIR=./uploads               # Local path — swap with S3_BUCKET etc. for prod

# Email
RESEND_API_KEY=

# Inngest (background jobs)
INNGEST_EVENT_KEY=
INNGEST_SIGNING_KEY=

# Monitoring
SENTRY_DSN=
NEXT_PUBLIC_POSTHOG_KEY=
```

---

## Integration Guide

How every feature connects to every other part of the system.

### Auth → Everything

JWT middleware runs before any business logic on every protected route. On signup, a `User` row is created in PostgreSQL via Prisma. All subsequent Prisma queries are scoped by `userId` — no row is ever accessible to the wrong user.

### Chat ↔ Prisma ↔ LLM

When a chat request arrives, the API fetches the last N messages for the conversation from Postgres via Prisma to build the history array. It then injects the area-specific system prompt and streams the LLM response back to the client over SSE. After streaming completes, both the user message and assistant response are written to the `Message` table asynchronously so the stream is never held up by a DB write.

### Document Upload ↔ Storage ↔ Analysis ↔ Prisma

After upload, the file is saved to the `uploads/` directory. The server extracts raw text using `pdf-parse` or `mammoth`, then enqueues an Inngest job. The Inngest function chunks the text, calls the LLM with the document analysis prompt, and writes the structured JSON result back to `Document.analysis` via Prisma. The `Document.status` field (`pending → analyzing → done`) drives UI polling on the client.

### Prompts ↔ Legal Area Selector

The `area` field from every chat and document request maps directly to a file in `/prompts`. The API route imports the matching prompt and injects it as the LLM system message. Legal experts can refine prompts as plain TypeScript without touching application code or requiring a schema change.

### LLM ↔ OpenAI-Compatible Client

`lib/llm.ts` wraps the OpenAI SDK pointed at `LLM_BASE_URL`. Swapping models or runtimes means changing two env vars — nothing else in the codebase changes. Streaming uses the standard `stream: true` path, which works identically across Ollama, vLLM, LM Studio, and any other compatible server.

### Usage Logs ↔ Observability

Every AI action writes a row to `UsageLog` (no PII — only `action`, `legalArea`, `tokensIn`, `tokensOut`). Sentry captures runtime errors. PostHog receives client-side events for funnel and retention analysis.

---

## Security & Compliance

- All API routes protected by JWT — no unauthenticated access to user data
- Prisma queries always scoped by `userId` — users can only access their own rows
- LLM calls happen server-side only — credentials never reach the browser
- Uploaded files stored in a server-only directory, served via signed temporary URLs
- Rate limiting: 60 req/min per IP on public routes, per-user quota on AI routes
- Input sanitised before passing to the LLM (strip prompt injection attempts)
- No PII stored in `UsageLog` — only action type and token counts

### Legal Disclaimers

Every AI response includes:
> *"This is legal information, not legal advice. Consult a qualified lawyer for your specific situation."*

Every document analysis includes:
> *"AI analysis may miss context. Do not rely solely on this for legal decisions."*

---

## Contributing

1. Fork the repo and create a feature branch: `git checkout -b feature/my-feature`
2. Run `npx prisma migrate dev` after any schema changes
3. Commit your changes: `git commit -m 'feat: add my feature'`
4. Push to the branch: `git push origin feature/my-feature`
5. Open a Pull Request — Vercel will auto-deploy a preview

Please follow the existing TypeScript conventions and add tests for any new API routes.

---

## License

Proprietary — LegalEase Confidential. Not for distribution.

---

*LegalEase is not a law firm and does not provide legal advice. Use of this product does not create a lawyer-client relationship.*
