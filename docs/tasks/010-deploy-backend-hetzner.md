# 010 — Deploy Backend to Hetzner

**Status:** Done
**Priority:** High
**Component:** Backend → Deployment

## Problem

The PixelVault backend runs on `localhost:8000`. Live WordPress sites cannot reach it. Need to deploy to a public server.

## Plan

- Server: Hetzner VPS (user's choice from earlier sessions)
- Domain: TBD (e.g., `api.pixelvault.io`)
- Stack: FastAPI + uvicorn behind nginx, systemd service
- Database: Already on Supabase (no DB to deploy)
- Storage: Local disk initially, Cloudflare R2 later
- SSL: Let's Encrypt via certbot

## Steps

1. Set up Hetzner VPS (Ubuntu 22.04)
2. Install Python 3.11+, nginx, certbot
3. Clone repo, install deps, configure .env
4. Set up systemd service for uvicorn
5. Configure nginx reverse proxy with SSL
6. Point domain DNS to Hetzner IP
7. Update WP plugin default API URL
8. Test from live WordPress site

## Prerequisites

- Domain purchased and DNS accessible
- Hetzner account set up

## Acceptance Criteria

- [x] Backend accessible at `https://vaultapi.noleemits.com/health`
- [x] All API endpoints work with API key auth
- [ ] WP plugin connects from live site (update plugin default URL)
- [x] SSL certificate valid (expires 2026-07-07, auto-renews)
- [x] Auto-restart on crash (systemd)

## Deployment Details

- **Server:** Hetzner CPX11 (2 vCPU, 2GB RAM, Ashburn VA)
- **IP:** 87.99.158.225
- **Domain:** vaultapi.noleemits.com (Cloudflare DNS, gray cloud)
- **Stack:** Ubuntu 24.04, Python 3.12, uvicorn (2 workers), nginx, certbot
- **Service:** `systemctl {start|stop|restart|status} pixelvault`
- **Logs:** `journalctl -u pixelvault -f`
- **App dir:** `/opt/pixelvault`
- **Deploy update:** `cd /opt/pixelvault && git pull && systemctl restart pixelvault`
