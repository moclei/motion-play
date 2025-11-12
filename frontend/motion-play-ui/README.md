# Motion Play UI

Web interface for controlling the Motion Play device and viewing sensor data.

## Setup

1. Install dependencies:
   ```bash
   npm install
   ```

2. Create `.env` file from template:
   ```bash
   cp .env.example .env
   ```

3. Update `.env` with your AWS API Gateway endpoint

4. Start development server:
   ```bash
   npm run dev
   ```

5. Open http://localhost:5173 in your browser

## Project Structure

```
src/
├── components/         # React components
│   ├── DeviceStatus.tsx
│   ├── CollectionControl.tsx
│   ├── SessionList.tsx
│   └── SessionDetail.tsx
├── services/          # API client and utilities
│   ├── api.ts         # API Gateway client
│   └── types.ts       # TypeScript interfaces
├── hooks/             # Custom React hooks
├── App.tsx            # Main application component
└── main.tsx           # Entry point
```

## Available Scripts

- `npm run dev` - Start development server
- `npm run build` - Build for production
- `npm run preview` - Preview production build
- `npm run lint` - Run ESLint

## Technologies

- React 18
- TypeScript
- Vite
- TailwindCSS
- Recharts (data visualization)
- Axios (HTTP client)
