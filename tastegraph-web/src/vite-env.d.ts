/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_TASTEGRAPH_ENDPOINT?: string;
}
interface ImportMeta {
  readonly env: ImportMetaEnv;
}
