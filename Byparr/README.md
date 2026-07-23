# Byparr

FlareSolverr-API-compatible Cloudflare Turnstile / managed-challenge solver. It runs a real,
fingerprint-hardened Firefox (via [Camoufox](https://camoufox.com/)) inside the container and
drives it headlessly to clear the "Just a moment..." interstitial, then hands back the resulting
HTML, cookies, and headers over a small HTTP API. Upstream: https://github.com/ThePhaseless/Byparr

## Why this exists

Plain `fetch`/`curl` requests — even from clean residential proxies — get stopped dead by
Cloudflare's managed challenge (Turnstile) on sites that require a real browser execution
environment to pass the JS check. Byparr solves that by actually running the challenge in a
browser and returning the post-challenge session.

**Confirmed via live testing against real Cloudflare-gated novel-metadata sites:**

- NovelUpdates — 403/challenge page cleared, ~7s response
- WebNovel.com — 403/challenge page cleared, ~7s response

It is used as a sidecar in front of scrapers that need those two sites (and anything else behind
the same class of managed challenge). Sites without Cloudflare (AniList API, Royal Road) don't
need it — only route the Cloudflare-gated ones through Byparr.

## Architecture / platform support

**Multi-arch: confirmed `linux/amd64` AND `linux/arm64`** — verified directly against the
`ghcr.io/thephaseless/byparr:latest` manifest list (`docker manifest inspect`), not just claimed
by the project. Safe to run on Oracle Linux ARM64 boxes (e.g. `swarm-1`) as well as amd64 hosts.
(This is a project-level exception to the "amd64-only image silently fails on ARM" pattern we've
been bitten by before — e.g. yt-dlp ENOENT — so it's worth double-checking on any *new* image you
add, this one specifically checks out.)

That said, upstream's own README is candid that ARM testing is limited to a single Ampere Oracle
VM they maintain — if you hit weirdness on ARM, it's a known thin-coverage area, not necessarily
something wrong with your host.

## How to call it

Byparr speaks the FlareSolverr wire protocol. POST to `/v1`:

```bash
curl -X POST http://byparr:8191/v1 \
  -H "Content-Type: application/json" \
  -d '{
        "cmd": "request.get",
        "url": "https://www.novelupdates.com/series/some-novel/",
        "maxTimeout": 60000
      }'
```

Response contains `solution.response` (HTML), `solution.cookies`, `solution.headers`, and
`solution.userAgent`. `maxTimeout` is in milliseconds — keep it well above ~10-15s since a real
browser challenge solve isn't instant (observed ~7s in testing, but give it margin under load).

Interactive API docs are also available at `http://<host>:8191/docs` once the container is up.

## Networking

Byparr has to be reachable by whatever is calling it:

- **Same docker network (preferred):** put your scraper/edge-function service on the same
  external `nat` network as this compose file and call it by container name/DNS —
  `http://byparr:8191/v1`. No public port needed; leave `ports:` commented out (see `traefik/`
  variant) or drop it entirely.
- **Cross-host:** if the consumer isn't on the same Docker host/network, it needs a routable
  `host:8191` — either publish the port (`compose/docker-compose.yml` does this by default) or
  front it with the Traefik labels in `traefik/docker-compose.yml`.

## Setup

1. Pick `compose/` (ports published directly) or `traefik/` (routed through Traefik, ports
   commented out) depending on how your consumer reaches it.
2. `docker compose up -d`
3. Confirm health: `docker exec byparr curl -sf http://127.0.0.1:8191/health` or watch
   `docker ps` for `(healthy)`.

## Environment variables

| Var | Default | Real? | Notes |
| --- | --- | --- | --- |
| `LOG_LEVEL` | `info` | ✅ upstream setting (`src/consts.py`) | `DEBUG`/`INFO`/`WARNING`/`ERROR` |
| `TZ` | `UTC` | Standard container/glibc var | Affects log timestamps; Byparr itself doesn't read it directly |
| `HEADLESS` | — | ❌ not a real Byparr setting | Left commented in the compose file as documented no-op. The image has no display — Camoufox always runs headless in the container. Requested for parity with the sidecar's env-var contract, but it does nothing here; don't spend time debugging it. |
| `PROXY_SERVER` / `PROXY_USERNAME` / `PROXY_PASSWORD` | none | ✅ upstream setting | Route Byparr's browser traffic through an upstream proxy |
| `HOST` / `PORT` | `0.0.0.0` / `8191` | ✅ upstream setting | Don't change `PORT` unless you also update the healthcheck and published port |

## Resource notes

- `mem_limit: 2g` — it's a real Firefox instance per active challenge, give it headroom.
- `shm_size: "1g"` — Camoufox uses shared memory; upstream's own troubleshooting docs call out
  `FileNotFoundError` from `multiprocessing.synchronize`/camoufox on Proxmox OCI/LXC hosts with
  too little shm. Bump higher if you see that.
- Healthcheck hits `GET /health` (confirmed from upstream's `Dockerfile`, not `/healthz` or
  assumed) — interval is intentionally long (15m) since it's a browser-backed check, not free.

## Security notes

- Byparr has **no built-in auth**. Anyone who can reach `:8191` can drive it as an open proxy to
  fetch arbitrary URLs through your egress IP. Do not publish the port to the public internet —
  keep it on the internal `nat` network only, or put it behind Traefik + an auth middleware
  (`authentik@file` label is stubbed in `traefik/docker-compose.yml`) if it must be externally
  reachable.
- It "does not guarantee" bypassing every challenge (upstream's own disclaimer) — don't treat a
  200 back from it as proof of legitimacy; validate the payload your caller actually needed.
- Runs as non-root (`USER 1000`) in the upstream image — don't override that.
