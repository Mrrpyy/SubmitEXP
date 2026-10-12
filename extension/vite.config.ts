import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

// Relative paths let the production build load inside chrome-extension:// URLs.
export default defineConfig({
  plugins: [react()],
  base: './',
  build: { outDir: 'dist', emptyOutDir: true },
});
