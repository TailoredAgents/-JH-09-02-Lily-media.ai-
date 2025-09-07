import '@testing-library/jest-dom'

// Mock import.meta for Jest environment
global.importMeta = {
  env: {
    VITE_API_BASE_URL: process.env.VITE_API_BASE_URL || 'http://localhost:8000',
    VITE_WS_URL: process.env.VITE_WS_URL || 'ws://localhost:8000',
    MODE: 'test',
    DEV: false,
    PROD: false,
  },
}

// Polyfill for import.meta (compatible with Jest)
if (typeof global.import === 'undefined') {
  global.import = { meta: { env: global.importMeta || {} } }
}
