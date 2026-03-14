# Static Website

This directory contains a standalone static website for Paperwise marketing content.

Generated product docs now live in `../docs-site` and are built with Starlight. Prefer
updating setup, support, and operational documentation there when possible.

## Files

- `index.html` - product showcase page
- `support.html` - legacy support / FAQ page
- `getting-started.html` - legacy getting-started page
- `styles.css` - shared styling

## Hosting

Host this directory on any static host (GitHub Pages, Netlify, Cloudflare Pages, S3 static hosting, etc.).

The site links back to the app at `/ui/documents`. If hosted on a different domain, update those links to the deployed app URL.
