/**
 * Which emulator is hosting this TUI, when the host tells us.
 *
 * `jarvis dashboard` spawns the TUI behind a PTY and mirrors it into xterm.js
 * in the browser; the bridge sets JARVIS_PTY_HOST=dashboard on the child
 * (jarvis_cli/pty_bridge.py — keep the two constants in sync). Native
 * terminals never set it.
 */
export const PTY_HOST_ENV = 'JARVIS_PTY_HOST'
export const PTY_HOST_DASHBOARD = 'dashboard'

export const isDashboardHosted = (env: NodeJS.ProcessEnv = process.env): boolean =>
  env[PTY_HOST_ENV] === PTY_HOST_DASHBOARD
