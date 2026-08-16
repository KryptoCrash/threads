# Threads sync — how it's wired

The app (`threads.html`) syncs whole-state through a small token-gated HTTP
endpoint, merging per-thread (newest edit wins) with tombstones so deletions
propagate. Two interchangeable backends exist; the devbox server is the live one.

## Primary: devbox server (running now)

`threads-server.py` runs as a systemd user service (`threads-server`, linger
enabled, port 8790). It serves the app at `/` and the sync API at `/api`,
writing **`threads.json` in this directory** — so Claude sessions on the devbox
see every change by just reading that file.

- Token: `~/.config/threads-server/token` (currently `40a276f8d5df63efbcc92a4cd0817279`)
- Logs: `journalctl --user -u threads-server`
- Restart: `systemctl --user restart threads-server`

Reaching it from your devices, pick one:

1. **Tailscale (recommended, private):** log the devbox in (Claude hands you the
   auth URL), install/sign-in Tailscale on Mac + phone, then the app lives at
   `https://devbox.<tailnet>.ts.net/` (exact URL printed after login;
   `tailscale serve` fronts port 8790 with HTTPS). Nothing is exposed publicly.
2. **Public GCP firewall (works without Tailscale on devices):** from your Mac:
   `gcloud compute firewall-rules create allow-threads --project=eric-yachbes --direction=INGRESS --action=ALLOW --rules=tcp:8790 --source-ranges=0.0.0.0/0`
   then use `http://35.239.153.45:8790/`. Plain HTTP + token gate; fine, but
   Tailscale is strictly nicer.

**Connecting a device:** open the app URL once with the device link
(`<app-url>#sync=%2Fapi%7C<token>` — sync endpoint `/api`, same origin), or use
Data ▾ → Connect and enter `/api` + the token. From a connected device,
Data ▾ → Drive sync settings → **Copy device link** reproduces it.

## Optional: Google Drive copy

mlaude (the Max-config Claude) has the claude.ai Google Drive connector with
full read/write, so a Drive mirror of `threads.json` is one headless call:
`env -u ANTHROPIC_API_KEY CLAUDE_CONFIG_DIR=$HOME/.claude-max claude -p "create or update threads.json in my Drive with the contents of <path>"` —
ask Claude to set up a cron if you want it continuous.

## Alternative backend: Apps Script bridge (no devbox dependency)

If you ever want sync that doesn't depend on the devbox being up: deploy
`drive-bridge.gs` at script.google.com (New project → paste → Deploy → Web app,
execute as **Me**, access **Anyone**), then connect the app to the `/exec` URL
with the same token. It keeps `threads.json` in your Drive; Claude reads it via
`curl -sL "<exec-url>?token=<token>"` or the Drive connector.

## Reading the data (for Claude / scripts)

- On devbox: `cat ~/Documents/research/afp/aug2026/derisking/threads.json`
- Over the network: `curl -s "<app-url>api?token=<token>"`
- Markdown digest: open the app → Data ▾ → Export Markdown.
