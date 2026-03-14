# Paperwise Docs

This directory contains the Starlight source for the Paperwise docs site.

Built static output is written to `../website/docs` so the generated docs can ship as part of
the main `website/` directory.

## Local development

```bash
cd docs-src
npm install
npm run dev
```

## Build

```bash
npm run build
```

The docs content lives in `src/content/docs`.
