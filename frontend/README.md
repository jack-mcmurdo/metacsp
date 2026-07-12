# metacsp viz frontend

Vite + React + TypeScript + Tailwind + shadcn/ui frontend for `metacsp.viz`'s browser-based
live viewer. See [`docs/VIZ.md`](../docs/VIZ.md) for the wire protocol it consumes.

```bash
npm install
npm run dev      # dev server, proxies /ws to ws://127.0.0.1:8722
npm run build    # outputs to ../src/metacsp/viz/static/, shipped inside the wheel
```

End users installing `metacsp[viz]` from PyPI never need Node -- release wheels ship a
prebuilt `static/` (see `.github/workflows/release.yml`).
