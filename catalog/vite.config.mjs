import { defineConfig } from 'vite';
import { resolve } from 'path';
import { fileURLToPath } from 'url';

const __dirname = fileURLToPath(new URL('.', import.meta.url));

export default defineConfig({
  root: __dirname,
  publicDir: resolve(__dirname, 'public'),
  server: {
    port: 5173,
    open: true,
  },
  build: {
    outDir: 'dist',
  },
});
