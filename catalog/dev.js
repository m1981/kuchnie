// catalog/dev.js
// Dev server: watch YAML + auto-rebuild + Vite HMR
// Uruchomienie: node catalog/dev.js

const { execSync, spawn } = require('child_process');
const fs = require('fs');
const path = require('path');

const MATERIALS_DIR = path.join(__dirname, '..', 'data', 'materials');
const BUILD_SCRIPT = path.join(MATERIALS_DIR, 'build.js');

let buildTimeout = null;

function build() {
  try {
    console.log('\n[build] Rebuilding catalog.json...');
    const env = { ...process.env, NODE_PATH: path.join(__dirname, 'node_modules') };
    execSync(`node "${BUILD_SCRIPT}"`, { stdio: 'inherit', cwd: path.join(__dirname, '..'), env });
    console.log('[build] Done\n');
  } catch (e) {
    console.error('[build] Failed:', e.message);
  }
}

// Watch YAML files for changes
function watchYaml() {
  const dirs = [
    path.join(MATERIALS_DIR, 'kronospan'),
    path.join(MATERIALS_DIR, 'swiss-krono'),
    path.join(MATERIALS_DIR, 'egger'),
    path.join(MATERIALS_DIR, 'shared'),
  ];

  dirs.forEach(dir => {
    if (!fs.existsSync(dir)) return;

    fs.watch(dir, { recursive: true }, (eventType, filename) => {
      if (!filename || !filename.endsWith('.yaml')) return;

      // Debounce: wait 300ms after last change
      if (buildTimeout) clearTimeout(buildTimeout);
      buildTimeout = setTimeout(() => {
        console.log(`[watch] Changed: ${filename}`);
        build();
      }, 300);
    });

    console.log(`[watch] Watching ${dir}`);
  });
}

// Initial build
build();

// Start watching
watchYaml();

// Start Vite
console.log('[vite] Starting Vite dev server...\n');
const viteBin = path.join(__dirname, 'node_modules', '.bin', 'vite');
const vite = spawn(viteBin, ['--config', 'catalog/vite.config.mjs'], {
  cwd: path.join(__dirname, '..'),
  stdio: 'inherit',
});

vite.on('close', (code) => {
  console.log(`[vite] Exited with code ${code}`);
  process.exit(code);
});

process.on('SIGINT', () => {
  vite.kill('SIGINT');
  process.exit(0);
});
