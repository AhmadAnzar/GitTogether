import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig({
  plugins: [react()],
  // `npm run dev` proxies API calls to a locally running backend (uvicorn on :8000).
  server: { port: 5173, proxy: { '/api': 'http://localhost:8000' } },
});
