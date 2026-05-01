import { defineConfig } from 'vite'
import { devtools } from '@tanstack/devtools-vite'

import { tanstackStart } from '@tanstack/react-start/plugin/vite'

import viteReact from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

// Static rendering: prerender '/' at build time so the output is just HTML +
// JS + CSS, deployable to any static host.
const config = defineConfig({
  resolve: { tsconfigPaths: true },
  server: {
    port: process.env.PORT ? Number(process.env.PORT) : 3000,
    host: process.env.HOST || 'localhost',
  },
  plugins: [
    devtools(),
    tailwindcss(),
    tanstackStart({
      pages: [{ path: '/', prerender: { enabled: true } }],
    }),
    viteReact(),
  ],
})

export default config
