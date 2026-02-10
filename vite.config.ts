import { existsSync } from 'node:fs';
import { homedir } from 'node:os';
import { resolve } from 'node:path';
import react from '@vitejs/plugin-react';
import { type ConfigEnv, defineConfig, loadEnv } from 'vite';

// Plugin to load global .env from ~/.config/atlastrinity/
function globalEnvPlugin() {
  return {
    name: 'global-env',
    config(_config: unknown, { mode }: ConfigEnv) {
      const globalConfigPath = resolve(homedir(), '.config', 'atlastrinity', '.env');

      if (existsSync(globalConfigPath)) {
        console.log(`🌍 Loading global .env from: ${globalConfigPath}`);

        // Load and parse global .env
        const globalEnv = loadEnv(mode, resolve(homedir(), '.config', 'atlastrinity'), '');

        // Prepend global env to process.env
        Object.assign(process.env, globalEnv);
      }
    },
  };
}

export default defineConfig({
  plugins: [react(), globalEnvPlugin()],
  base: './',
  root: 'src/renderer',
  envDir: '../../', // Project root
  build: {
    outDir: '../../dist/renderer',
    emptyOutDir: true,
  },
  resolve: {
    alias: {
      '@': resolve(__dirname, 'src/renderer'),
      '@design': resolve(__dirname, 'design-system'),
    },
  },
  server: {
    port: 3000,
  },
});
