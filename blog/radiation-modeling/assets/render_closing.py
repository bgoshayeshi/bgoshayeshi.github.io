"""Renders Fig. 7: the Utah teapot and the Stanford dragon in a small room, path traced with Mitsuba 3 on the
GPU (Metal on Apple silicon, CUDA elsewhere), plus the same scene as each radiation model would get it.

  rt      full path tracing, every bounce — the reference
  direct  "no exchange": light straight from the lamp only (one bounce)
  p1      the lamp's light arrives as a smooth glow: the lamp is smeared over a ball of point sources, so sharp
          shadows melt away; the exchange between surfaces is kept
  dom     the lamp's light leaves only along the 24 directions of an S4 level-symmetric set (the ray effect);
          the exchange between surfaces is kept

usage: python3 render_closing.py teapot.obj dragon.ply outdir [--spp 16384] [--size 1440x900] [--models rt,direct,p1,dom]
writes outdir/glaze-<model>.webp and, when rt is rendered in the same run, outdir/stats.json
(mean |luminance - reference| / mean reference luminance)
"""
import argparse, json, math, os, time
import numpy as np
import mitsuba as mi
import drjit as dr
from PIL import Image

for v in ("metal_ad_rgb", "cuda_ad_rgb", "llvm_ad_rgb"):
    if v in mi.variants():
        try:
            mi.set_variant(v)
            break
        except Exception:
            pass
print("variant:", mi.variant())
T = mi.ScalarTransform4f

# room: floor y=0, ceiling y=H, red wall x=-W, green wall x=+W, back wall z=B, a wall behind the camera z=F
W, H, B, F = 1.3, 1.7, -1.3, 2.6
LAMP = mi.ScalarPoint3f(0.0, H - 0.32, -0.35)
LAMP_R = 0.045
LAMP_POWER = 9.0            # watts-ish; the exposure below is tuned to it
EXPOSURE = 1.9


def diffuse(rgb):
    return {"type": "diffuse", "reflectance": {"type": "rgb", "value": rgb}}


def glaze(rgb, rough=0.08):
    return {"type": "roughplastic", "distribution": "ggx", "alpha": rough, "int_ior": 1.52,
            "diffuse_reflectance": {"type": "rgb", "value": rgb}}


def fit(shape_dict, height, base, yaw):
    """Scale a y-up mesh to `height`, rotate about y by `yaw`, and stand it on the floor at `base`."""
    bb = mi.load_dict(shape_dict).bbox()
    c = (bb.min + bb.max) * 0.5
    s = height / (bb.max.y - bb.min.y)
    return (T().translate(base) @ T().rotate([0, 1, 0], yaw) @ T().scale(s)
            @ T().translate([-c.x, -bb.min.y, -c.z]))


def room():
    wall = lambda to_world, rgb: {"type": "rectangle", "to_world": to_world, "bsdf": diffuse(rgb)}
    white, red, green = [0.72, 0.70, 0.66], [0.62, 0.07, 0.05], [0.10, 0.45, 0.10]
    d, cz = F - B, (F + B) / 2
    return {
        "floor": wall(T().translate([0, 0, cz]) @ T().rotate([1, 0, 0], -90) @ T().scale([W, d / 2, 1]), white),
        "ceiling": wall(T().translate([0, H, cz]) @ T().rotate([1, 0, 0], 90) @ T().scale([W, d / 2, 1]), white),
        "back": wall(T().translate([0, H / 2, B]) @ T().scale([W, H / 2, 1]), white),
        "front": wall(T().translate([0, H / 2, F]) @ T().rotate([0, 1, 0], 180) @ T().scale([W, H / 2, 1]), white),
        "left": wall(T().translate([-W, H / 2, cz]) @ T().rotate([0, 1, 0], 90) @ T().scale([d / 2, H / 2, 1]), red),
        "right": wall(T().translate([W, H / 2, cz]) @ T().rotate([0, 1, 0], -90) @ T().scale([d / 2, H / 2, 1]), green),
    }


def s4_directions():
    """The 24 directions of the S4 level-symmetric quadrature: every permutation and sign of (mu1, mu1, mu2)."""
    m1, m2 = 0.2958759, 0.9082483
    dirs = []
    for p in ((m1, m1, m2), (m1, m2, m1), (m2, m1, m1)):
        for sx in (-1, 1):
            for sy in (-1, 1):
                for sz in (-1, 1):
                    dirs.append((sx * p[0], sy * p[1], sz * p[2]))
    return dirs


def lamp_emitters(model):
    """The lamp as each model delivers it. Total power is the same in every case."""
    if model in ("rt", "direct"):
        # small spherical lamp: power = radiance * pi * area
        L = LAMP_POWER / (math.pi * 4 * math.pi * LAMP_R ** 2)
        return {"lamp": {"type": "sphere", "center": LAMP, "radius": LAMP_R,
                         "emitter": {"type": "area", "radiance": {"type": "rgb", "value": [L, 0.93 * L, 0.82 * L]}}}}
    col = np.array([1.0, 0.93, 0.82])
    if model == "p1":
        # smeared source: 96 point lights filling a ball around the lamp
        rng = np.random.default_rng(1)
        pts = []
        while len(pts) < 96:
            p = rng.uniform(-1, 1, 3)
            if p @ p <= 1:
                pts.append(p)
        R = np.array([0.95, 0.20, 0.75])           # clipped to stay inside the room
        I = LAMP_POWER / (4 * math.pi) / len(pts)
        return {f"p1_{i}": {"type": "point", "position": (np.array(LAMP) + R * p).tolist(),
                            "intensity": {"type": "rgb", "value": (I * col).tolist()}} for i, p in enumerate(pts)}
    if model == "dom":
        # 24 narrow beams; each carries 1/24 of the power
        cutoff, beam = 9.0, 6.0
        # solid angle of Mitsuba's spot profile (flat to `beam`, then linear falloff in angle to `cutoff`)
        th = np.linspace(0, math.radians(cutoff), 4000)
        prof = np.clip((math.radians(cutoff) - th) / math.radians(cutoff - beam), 0, 1)
        omega = np.trapezoid(prof * 2 * math.pi * np.sin(th), th)
        I = LAMP_POWER / 24 / omega
        out = {}
        for i, d in enumerate(s4_directions()):
            tgt = [LAMP[0] + d[0], LAMP[1] + d[1], LAMP[2] + d[2]]
            up = [0, 1, 0] if abs(d[1]) < 0.9 else [1, 0, 0]
            out[f"dom_{i}"] = {"type": "spot", "cutoff_angle": cutoff, "beam_width": beam,
                               "intensity": {"type": "rgb", "value": (I * col).tolist()},
                               "to_world": T().look_at(origin=LAMP, target=tgt, up=up)}
        return out
    raise ValueError(model)


def scene(model, teapot, dragon, size, max_depth=None):
    w, h = size
    tea = {"type": "obj", "filename": teapot}
    dra = {"type": "ply", "filename": dragon}
    d = {
        "type": "scene",
        "integrator": {"type": "path", "max_depth": max_depth or (2 if model == "direct" else 12), "rr_depth": 6},
        "sensor": {"type": "perspective", "fov": 52, "fov_axis": "x",
                   "to_world": T().look_at(origin=[0, 0.82, 2.3], target=[0, 0.66, -0.3], up=[0, 1, 0]),
                   "film": {"type": "hdrfilm", "width": w, "height": h, "rfilter": {"type": "gaussian"}},
                   "sampler": {"type": "independent"}},
        "teapot": dict(tea, to_world=fit(tea, 0.50, [-0.46, 0, -0.10], 205),
                       bsdf=glaze([0.80, 0.76, 0.68])),
        "dragon": dict(dra, to_world=fit(dra, 0.64, [0.48, 0, -0.25], -30),
                       bsdf=glaze([0.16, 0.36, 0.52])),
        **room(),
        **lamp_emitters(model),
    }
    return mi.load_dict(d)


def render(sc, spp, chunk=1024):
    acc, n, seed = None, 0, 0
    while n < spp:
        k = min(chunk, spp - n)
        img = mi.render(sc, spp=k, seed=seed)
        img = np.array(img, dtype=np.float64) * k
        acc = img if acc is None else acc + img
        n, seed = n + k, seed + 1
    return acc / spp


def lamp_mask(teapot, dragon, size):
    """Radiance of the visible lamp alone (depth 1 = emitters seen directly), composited into the model images
    that do not have it."""
    return render(scene("rt", teapot, dragon, size, max_depth=1), 256)


def tonemap(x):
    x = np.clip(x * EXPOSURE, 0, None)
    x = x / (1 + x / 6.0)                       # gentle shoulder so the lamp does not clip hard
    srgb = np.where(x <= 0.0031308, 12.92 * x, 1.055 * np.power(x, 1 / 2.4) - 0.055)
    return (np.clip(srgb, 0, 1) * 255 + 0.5).astype(np.uint8)


def lum(x):
    return x @ np.array([0.2126, 0.7152, 0.0722])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("teapot"); ap.add_argument("dragon"); ap.add_argument("outdir")
    ap.add_argument("--spp", type=int, default=16384)
    ap.add_argument("--size", default="1440x900")
    ap.add_argument("--models", default="rt,direct,p1,dom")
    ap.add_argument("--ext", default="webp")
    a = ap.parse_args()
    size = tuple(int(v) for v in a.size.split("x"))
    os.makedirs(a.outdir, exist_ok=True)

    imgs = {}
    glyph = None
    for m in a.models.split(","):
        t = time.time()
        img = render(scene(m, a.teapot, a.dragon, size), a.spp)
        if m in ("p1", "dom"):
            if glyph is None:
                glyph = lamp_mask(a.teapot, a.dragon, size)
            img = img + glyph
        imgs[m] = img
        Image.fromarray(tonemap(img)).save(os.path.join(a.outdir, f"glaze-{m}.{a.ext}"), quality=88)
        print(f"{m}: {time.time() - t:.1f}s  mean lum {lum(img).mean():.4f}", flush=True)

    stats_path = os.path.join(a.outdir, "stats.json")
    stats = json.load(open(stats_path)) if os.path.exists(stats_path) else {}
    ref = imgs.get("rt")
    if ref is not None:
        lr = lum(ref)
        for m, img in imgs.items():
            if m != "rt":
                stats[f"glaze-{m}"] = round(float(np.abs(lum(img) - lr).mean() / lr.mean()), 4)
        json.dump(stats, open(stats_path, "w"), indent=2)
        print(stats)


if __name__ == "__main__":
    main()
