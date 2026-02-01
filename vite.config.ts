import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import { resolve } from 'path';

export default defineConfig({
    plugins: [react()],
    base: './',
    root: 'src/renderer',
    envDir: '../../',
    envDir: '../../',
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
