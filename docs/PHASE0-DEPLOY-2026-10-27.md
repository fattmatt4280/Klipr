# Phase 0 deploy — 2026-10-27

Bundle: ~/workspace/klipr-deploy.tar.gz (43K, rebuilt 2026-10-27 with phase0-finish.sh)
Muse storage link: https://muse.ai/files/1252972744555096/2378908172852871/rnz07m4teqxpdbfsq54j9wo1/klipr-deploy.tar.gz
Expires: 2026-10-29T10:12:14Z (06:12 EDT Oct 29). Anyone with the link can download it.
Bundle contains NO secrets: .env.example only, no .env, no admin token, no DB password.
Do not post the link publicly — treat it as a private download link.

Deploy route: Termius to Contabo VPS 217.216.94.215 as root, paste master block
(BUNDLE_URL + DB_PASSWORD + KLIPR_DOMAIN), script does: apt deps, postgres,
klipr + klipr_staging DBs, schema, klipr_app role, .env (600), admin token seed
(printed once), systemd klipr-api + klipr-worker, daily backup cron, Caddy if domain set,
verification (health + RLS count 23).

Still open by design after deploy: production OAuth (local admin token only),
S3/R2/B2, Redis swap, offsite backup remote, Next.js front end.
Next after deploy: DWW mount hidden page + Lovable Publish, then Phase 1 reference set.
