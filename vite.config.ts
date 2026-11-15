import tailwindcss from '@tailwindcss/vite'
import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'
import { viteStaticCopy } from 'vite-plugin-static-copy'

const cesiumSource = 'node_modules/cesium/Build/Cesium'
const cesiumBaseUrl = 'cesiumStatic'
// Drop `node_modules/cesium/Build/Cesium` so files land at /cesiumStatic/Workers and so on.
const cesiumPathSegments = 4

function cesiumAssets(folder: string) {
  return {
    src: `${cesiumSource}/${folder}/**/*`,
    dest: cesiumBaseUrl,
    rename: { stripBase: cesiumPathSegments },
  }
}

// Cesium loads workers and textures from CESIUM_BASE_URL at runtime.
// The static copy plugin publishes those assets in dev and in the production build.
export default defineConfig({
  define: {
    CESIUM_BASE_URL: JSON.stringify(`/${cesiumBaseUrl}`),
  },
  build: {
    rollupOptions: {
      output: {
        manualChunks(id) {
          if (id.includes('node_modules/cesium') || id.includes('node_modules/@cesium')) return 'cesium'
        },
      },
    },
  },
  plugins: [
    react(),
    tailwindcss(),
    viteStaticCopy({
      targets: [
        cesiumAssets('ThirdParty'),
        cesiumAssets('Workers'),
        cesiumAssets('Assets'),
        cesiumAssets('Widgets'),
      ],
    }),
  ],
})
