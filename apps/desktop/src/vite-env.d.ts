/// <reference types="vite/client" />

// node:* built-in modules used by the desktop app (tests + plugins)
// @types/node provides the real types; this declaration keeps tsc from dropping them.
declare module "node:*";
