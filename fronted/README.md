# AI OCR Studio — React

Production-ready React + TypeScript + Tailwind UI for OCR demo and dashboard. Swap the mock API with your FastAPI endpoints later.

## Stack
- React 18 + TypeScript
- Vite
- Tailwind CSS
- React Router
- Zustand (optional, not used yet)

## Quickstart
```bash
pnpm i   # or npm i / yarn
pnpm add -D @vitejs/plugin-react


pnpm dev # or npm run dev

or 
# inside ocr-react-app/
npm i         # or pnpm i / yarn
npm run dev   # vite dev server (http://localhost:5173)

```
Open http://localhost:5173

## Dummy Login
- Email: `admin@demo.dev`
- Password: `Pass@123`

## Where to wire FastAPI
Edit `src/services/api.ts` and replace the mocked functions with real `fetch` calls.
