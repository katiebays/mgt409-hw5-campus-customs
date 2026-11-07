import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// The board talks straight to the back end on port 8000 (see src/api.ts).
// Host 127.0.0.1 makes both http://localhost:5173 and http://127.0.0.1:5173 work.
export default defineConfig({
  plugins: [react()],
  server: { host: '127.0.0.1', port: 5173, strictPort: true },
})
