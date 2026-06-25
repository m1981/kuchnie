import { defineConfig } from 'vite';
import { resolve } from 'path';
import { fileURLToPath } from 'url';

const __dirname = fileURLToPath(new URL('.', import.meta.url));

export default defineConfig({
  root: __dirname,
  publicDir: resolve(__dirname, '..', 'data', 'dist'),
  server: {
    port: 5173,
    open: true,
    watch: {
      // Watch dist/catalog.json for changes (rebuilt by build.js)
      ignored: ['!**/data/dist/**'],
    },
  },
  build: {
    outDir: 'dist',
  },
});
