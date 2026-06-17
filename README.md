# bgoshayeshi.github.io

Personal site for **Babak Goshayeshi, Ph.D.**: Scientific Computing & AI Platform Leader.

## Structure

```
.
├── index.html                         # Home: full one-page portfolio
├── styles.css                         # All styling (design tokens at top)
├── script.js                          # Nav, mobile menu, scroll-reveal (progressive enhancement)
├── assets/
│   ├── temperature-hero.mp4           # Combustion-chamber CFD loop (hero, 900px, muted, ~8 MB)
│   ├── logos/                         # DiPhyx & dxflow logos (Ventures section)
│   └── compute-viz/                   # Animated HPC→pipelines visualization (iframed into About)
└── projects/
    ├── odt/                           # Ph.D. work: Two-Phase One-Dimensional Turbulence model (linked from Work)
    └── computational-science/         # Animated computational-pipelines visualization (currently unlinked)
```

The ODT page is a self-contained page linked from the **Work** section, with a
"← Babak Goshayeshi" link back to home. The `computational-science/` page still ships but is
no longer linked from the homepage; delete it or re-link it as needed.

## Deploy with GitHub Pages

1. Commit and push to the `main` branch of `bgoshayeshi/bgoshayeshi.github.io`.
2. On GitHub: **Settings → Pages → Build and deployment → Source: Deploy from a branch**,
   branch `main`, folder `/ (root)`.
3. The site publishes at **https://bgoshayeshi.github.io/** (no build step; it's static).

> The hero video is `temperature-hero.mp4` (~8 MB, 900 px, muted, faststart), a web-optimized
> loop derived from the full-resolution combustion simulation. Keep large source media out of the
> repo (GitHub warns above 50 MB).

