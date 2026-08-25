# FlareSolverr

Proxy server that bypasses Cloudflare and DDoS-Guard protection. It runs a real headless
Chromium inside the container, drives it through the "Just a moment..." managed-challenge
interstitial, then hands back the resulting HTML, cookies, and headers over a small HTTP API.
Upstream: https://github.com/FlareSolverr/FlareSolverr

## Why this exists

Plain `fetch`/`curl` requests get stopped dead by Cloudflare's managed challenge (Turnstile/JS
challenge) on sites that require a real browser execution environment to pass the check.
FlareSolverr solves that by actually running the challenge in Chromium and returning the
post-challenge session so your scraper/automation can reuse the cookies.

Note: this is the same job **Byparr** does (Byparr is a Camoufox-based, fingerprint-hardened
FlareSolverr-API-compatible alternative). Deploy whichever one a given upstream tool expects —
some projects (Prowlarr, Jackett, Bazarr) specifically integrate against the FlareSolverr name/API
version, others are fine with either. If you're running both on the same host, they need
**different published ports** — they don't coexist on the same port.

## How to call it

FlareSolverr speaks its own wire protocol (same shape Byparr mirrors). POST to `/v1`:

```bash
curl -X POST http://flaresolverr:8191/v1 \
  -H "Content-Type: application/json" \
  -d '{
        "cmd": "request.get",
        "url": "https://example.com/",
        "maxTimeout": 60000
      }'
```

Response contains `solution.response` (HTML), `solution.cookies`, `solution.headers`, and
`solution.userAgent`. `maxTimeout` is in milliseconds — a real browser challenge solve isn't
instant, give it margin under load.

`GET /` on the base URL returns a JSON readiness payload (`{"msg":"FlareSolverr is ready!", ...}`)
— that's what the container healthcheck polls, and a quick way to confirm it's alive without
POSTing a real challenge request.

## Networking

- **Same docker network (preferred):** put your scraper/edge-function service on the same
  external `nat` network as this compose file and call it by container name/DNS —
  `http://flaresolverr:8191/v1`. No public port needed; leave `ports:` commented out (see
  `traefik/` variant) or drop it entirely.
- **Cross-host / netbird-only:** if the consumer isn't on the same Docker host/network but you
  still don't want it on the public internet, bind the published port to a specific internal
  interface instead of `0.0.0.0` — e.g. `"100.x.x.x:8191:8191"` (your netbird/tailnet IP) rather
  than `"8191:8191"`. Confirm with `ss -tlnp` that the listener shows your internal IP only, not
  `0.0.0.0`.
- **Public + Traefik:** use the `traefik/` variant and set a real hostname — only do this if you
  add auth in front of it (see Security notes).

## Setup

1. Pick `compose/` (ports published directly — edit to bind an internal-only IP if you don't want
   it reachable from outside your network) or `traefik/` (routed through Traefik, ports commented
   out) depending on how your consumer reaches it.
2. `docker compose up -d`
3. Confirm health: `docker inspect flaresolverr --format '{{.State.Health.Status}}'` or watch
   `docker ps` for `(healthy)`.

## Environment variables

| Var | Default | Notes |
| --- | --- | --- |
| `LOG_LEVEL` | `info` | `debug` \| `info` \| `warning` \| `error` |
| `LOG_HTML` | `false` | Dumps full challenge-page HTML to logs when `true` — verbose, debugging only |
| `CAPTCHA_SOLVER` | `none` | Set to a supported solver name to auto-solve CAPTCHAs upstream can't clear on its own (see upstream README for the current list and required extra env vars per solver) |
| `TZ` | `UTC` | Container timezone, affects log timestamps |

## Resource notes

- Runs full Chromium + Xvfb inside the container — give it real CPU/memory headroom on
  constrained VPS tiers, same class of resource need as Byparr's Camoufox/Firefox.
- Healthcheck hits `GET /` (not a dedicated `/health` route like Byparr) — confirmed from the
  readiness JSON payload the app returns on that route.
- `./config:/config` volume persists browser profile/session state across container restarts —
  without it, every restart starts from a completely clean browser.

## Security notes

- FlareSolverr has **no built-in auth**. Anyone who can reach the port can drive it as an open
  proxy to fetch arbitrary URLs through your egress IP. Do not publish the port to the public
  internet unauthenticated — keep it on the internal `nat` network only, bind to an internal-only
  IP (netbird/tailnet), or put it behind Traefik + an auth middleware (`authentik@file` label is
  stubbed in `traefik/docker-compose.yml`) if it must be externally reachable.
- A 200 back from it just means the challenge was cleared — don't treat that as proof the payload
  itself is legitimate; validate what your caller actually needed from the response.
- Runs Chromium in a container with no seccomp/AppArmor overrides applied by this compose file —
  don't add `privileged: true` or `--no-sandbox`-style host escapes beyond what upstream's own
  Dockerfile already sets internally.
