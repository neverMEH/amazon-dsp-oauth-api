# Amazon DSP OAuth UI

A modern React frontend for the Amazon DSP OAuth API, built with TypeScript, Vite, and shadcn/ui.

## Features

- 🔐 Secure OAuth 2.0 authentication flow
- 🎨 Beautiful UI with shadcn/ui components
- 🔄 Automatic token refresh
- 📋 Easy token copying and management
- 🌓 Dark mode support
- 📱 Responsive design

## Setup

1. Install dependencies:
```bash
cd frontend
npm install
```

2. Create a `.env` file:
```bash
cp .env.example .env
```

3. Update the `.env` file with your API URL:
```
VITE_API_URL=https://your-api-domain.railway.app
```

## Development

Run the development server:
```bash
npm run dev
```

The app will be available at http://localhost:3000

## Build

Build for production:
```bash
npm run build
```

## Deployment

### Vercel

1. Connect your GitHub repository to Vercel
2. Set the root directory to `frontend`
3. Add environment variable: `VITE_API_URL`
4. Deploy

### Netlify

1. Connect your GitHub repository to Netlify
2. Set build command: `npm run build`
3. Set publish directory: `dist`
4. Add environment variable: `VITE_API_URL`
5. Deploy

### Railway

1. Create a new service
2. Connect your GitHub repository
3. Set root directory to `frontend`
4. Add environment variable: `VITE_API_URL`
5. Deploy

## Environment Variables

- `VITE_API_URL`: The URL of your deployed Amazon DSP OAuth API

## Tech Stack

- React 18
- TypeScript
- Vite
- shadcn/ui
- Tailwind CSS
- React Router
- Lucide Icons