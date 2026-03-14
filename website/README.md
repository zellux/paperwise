# Static Website

This directory contains a standalone static website for Paperwise marketing content.

Generated product docs are published to `./docs`, with the Starlight source living in
the top-level `docs-src/` directory. Prefer updating setup, support, and operational
documentation in `../docs-src/`.

## Files

- `index.html` - product showcase page
- `support.html` - redirect shim to `./docs/support/`
- `getting-started.html` - redirect shim to `./docs/getting-started/`
- `docs/` - generated static docs output
- `styles.css` - shared styling

## Hosting

Host this directory on any static host (GitHub Pages, Netlify, Cloudflare Pages, S3 static hosting, etc.).

The site links back to the app at `/ui/documents`. If hosted on a different domain, update those links to the deployed app URL.
