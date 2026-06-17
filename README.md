# bgoshayeshi.github.io

Personal site for **Babak Goshayeshi, Ph.D.**: Scientific Computing & AI Platform Leader.

A static, dependency-free site (plain HTML/CSS/JS) hosted on GitHub Pages. Visual language
is referenced from [anthropic.com](https://www.anthropic.com/): warm ivory paper background,
clay/terracotta accent, editorial serif (Fraunces) + clean sans (Inter).

## Structure

```
.
├── index.html                         # Home: full one-page portfolio
├── styles.css                         # All styling (design tokens at top)
├── script.js                          # Nav, mobile menu, scroll-reveal (progressive enhancement)
├── assets/
│   ├── temperature-hero.mp4           # Combustion-chamber CFD loop (hero, 900px, muted, ~8 MB)
│   └── logos/                         # DiPhyx & dxflow logos (Ventures section)
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

## Customization checklist (TODO before publishing)

Search the codebase for `data-todo` and `TODO` to find every placeholder. Specifically:

- [ ] **LinkedIn** URL (nav/contact/footer placeholders)
- [ ] **GitHub** link (currently points to `github.com/bgoshayeshi`)
- [ ] Confirm DiPhyx title: "Founder & CEO", "Founder & CTO", or both
- [ ] Add `assets/og-image.png` (1200×630) and uncomment the `og:image` meta tag in `index.html`
- [ ] Optional: professional headshot, project screenshots/architecture diagrams
- [ ] Optional future pages from the original brief: **Books** and **Blog** (not built in this first draft)

DiPhyx (`https://www.diphyx.com/`) and dxflow (`https://dxflow.ai/`) links are live in the
**Building** section; no CV is hosted on the site (resumes are tailored per application).

## Local preview

```bash
cd bgoshayeshi.github.io
python3 -m http.server 8000
# open http://localhost:8000
```

## Notes

- No frameworks, no build, no dependencies, easy to maintain.
- Responsive (desktop → mobile), accessible headings/landmarks, alt text, and
  `prefers-reduced-motion` respected.
- Content follows the brief in `../Babak materials/`: no invented metrics, no proprietary
  Merck details.
