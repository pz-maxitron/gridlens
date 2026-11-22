# Deploying GridLens

GridLens is a fully static, client-side app (no backend, no environment
variables, no secrets) — `npm run build` produces a `dist/` folder that can
be served from literally any static host. There's no one "correct" way to
deploy it; pick whichever of these fits:

## GitHub Pages with a custom domain (gridlens.org) — this repo's actual setup

This is how gridlens.org is actually deployed, not a generic template:

1. `.github/workflows/deploy.yml` builds `dist/` (job `build`) and deploys it
   to GitHub Pages (job `deploy`) on every push to `main`, or by hand via
   "Run workflow". If only the deploy fails, "Re-run failed jobs" reuses
   the build.
2. `public/CNAME` contains `gridlens.org` (already in this repo) — Vite
   copies anything in `public/` into `dist/` unchanged, so GitHub Pages
   picks up the custom domain automatically from the deployed artifact.
3. One-time manual step (repo admin, GitHub UI): Settings → Pages → set
   **Source** to "GitHub Actions", and under **Custom domain** confirm/set
   it to `gridlens.org`, then check "Enforce HTTPS" once DNS has propagated
   (see below — HTTPS can't be enforced until the DNS records resolve).
4. DNS records to add wherever `gridlens.org` is registered (Squarespace
   Domains, in this case) — `gridlens.org` is an apex/root domain, so it
   needs **A records**, not a CNAME (CNAME isn't valid at the zone apex):

   | Type | Host | Value |
   |---|---|---|
   | A | @ | 185.199.108.153 |
   | A | @ | 185.199.109.153 |
   | A | @ | 185.199.110.153 |
   | A | @ | 185.199.111.153 |
   | AAAA (optional, IPv6) | @ | 2606:50c0:8000::153 |
   | AAAA (optional, IPv6) | @ | 2606:50c0:8001::153 |
   | AAAA (optional, IPv6) | @ | 2606:50c0:8002::153 |
   | AAAA (optional, IPv6) | @ | 2606:50c0:8003::153 |

   If you also want `www.gridlens.org` to work, add a CNAME record for host
   `www` pointing to `open-energy-transition.github.io` (GitHub will
   redirect it to the apex domain once the custom domain is confirmed).

5. DNS propagation typically takes anywhere from a few minutes to a few
   hours. Check with `dig gridlens.org +noall +answer` — once it resolves
   to the four IPs above, the GitHub Pages "Enforce HTTPS" checkbox becomes
   available (GitHub provisions the TLS certificate automatically via
   Let's Encrypt once it can verify the domain).

## Other static hosts (generic, for reference)

### Vercel / Netlify / Cloudflare Pages (also free tier, zero config)

All three auto-detect a Vite project. Point them at this repo, build
command `npm run build`, output directory `dist`. No environment variables
needed.

### Any other static host / CDN

```bash
npm run build
# upload the contents of dist/ to your host of choice
```

### GitHub Pages without a custom domain (`<org>.github.io/gridlens/`)

If serving from the default `github.io` project-page path instead of a
custom domain, add `base: '/gridlens/'` to `vite.config.ts`'s
`defineConfig` — otherwise asset paths will 404. Not needed for the
gridlens.org custom-domain setup above, since that serves from the root.

## What does NOT need to change between environments

Nothing — the dataset (`src/data/catalogue.json`) is bundled into the
build at build time, not fetched from an API at runtime. A new deploy is
required to publish a dataset update (run `npm run sync-data`, commit, then
redeploy) — there's no live database to update separately.
