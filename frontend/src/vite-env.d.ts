/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_API_BASE_URL: string
  readonly VITE_WS_BASE_URL: string
  readonly VITE_ENABLE_MEDIAPIPE: string
  readonly VITE_ENABLE_DEBUG_PANEL: string
  // readonly DEV: boolean;
  // readonly PROD: boolean;
  // readonly SSR: boolean;
}

interface ImportMeta {
  readonly env: ImportMetaEnv
}