"""Turntable GIF renderer: numpy + PIL, painter's algorithm on small triangles,
Blinn-Phong shading with a fixed light while the model spins.

usage: python3 turntable.py mesh.(stl|ply) out.gif [--frames 48] [--size 720x480]
       [--color r,g,b] [--up z|y] [--elev 22] [--zoom 1.0] [--spin 1]
"""
import sys, struct, math, argparse
import numpy as np
COLORS = 64
from PIL import Image, ImageDraw, ImageFilter


# ----------------------------------------------------------------- loaders
def load_stl(path):
    data = open(path, "rb").read()
    if data[:5] == b"solid" and b"facet" in data[:400]:
        tris = []
        for line in data.decode("ascii", "ignore").splitlines():
            t = line.split()
            if t and t[0] == "vertex":
                tris.append([float(t[1]), float(t[2]), float(t[3])])
        return np.array(tris, dtype=np.float64).reshape(-1, 3, 3)
    n = struct.unpack("<I", data[80:84])[0]
    rec = np.frombuffer(data[84:84 + n * 50], dtype=np.dtype([("n", "<f4", 3), ("v", "<f4", (3, 3)), ("a", "<u2")]))
    return rec["v"].astype(np.float64)


def load_ply(path):
    f = open(path, "rb")
    header = []
    while True:
        line = f.readline().decode("ascii").strip()
        header.append(line)
        if line == "end_header":
            break
    fmt = [h for h in header if h.startswith("format")][0].split()[1]
    elems, cur = [], None
    for h in header:
        t = h.split()
        if t[0] == "element":
            cur = {"name": t[1], "count": int(t[2]), "props": []}
            elems.append(cur)
        elif t[0] == "property":
            cur["props"].append(t[1:])
    verts = faces = None
    if fmt == "ascii":
        toks = f.read().split()
        pos = 0
        for e in elems:
            if e["name"] == "vertex":
                np_ = len(e["props"])
                arr = np.array(toks[pos:pos + e["count"] * np_], dtype=np.float64).reshape(-1, np_)
                pos += e["count"] * np_
                verts = arr[:, :3]
            elif e["name"] == "face":
                fl = []
                for _ in range(e["count"]):
                    k = int(toks[pos]); idx = toks[pos + 1:pos + 1 + k]; pos += 1 + k
                    for j in range(1, k - 1):
                        fl.append((int(idx[0]), int(idx[j]), int(idx[j + 1])))
                faces = np.array(fl, dtype=np.int64)
            else:
                pos += e["count"] * len(e["props"])
    else:
        endian = "<" if fmt == "binary_little_endian" else ">"
        tmap = {"float": "f4", "float32": "f4", "double": "f8", "int": "i4", "uint": "u4",
                "uchar": "u1", "char": "i1", "short": "i2", "ushort": "u2", "int32": "i4", "uint8": "u1"}
        buf = f.read(); pos = 0
        for e in elems:
            if e["name"] == "vertex":
                dt = np.dtype([(f"p{i}", endian + tmap[p[0]]) for i, p in enumerate(e["props"])])
                arr = np.frombuffer(buf, dtype=dt, count=e["count"], offset=pos); pos += e["count"] * dt.itemsize
                verts = np.stack([arr["p0"], arr["p1"], arr["p2"]], 1).astype(np.float64)
            elif e["name"] == "face":
                lp = e["props"][0]  # ['list', ctype, itype, name]
                ct, it = np.dtype(endian + tmap[lp[1]]), np.dtype(endian + tmap[lp[2]])
                fl = []
                for _ in range(e["count"]):
                    k = int(np.frombuffer(buf, ct, 1, pos)[0]); pos += ct.itemsize
                    idx = np.frombuffer(buf, it, k, pos); pos += k * it.itemsize
                    for j in range(1, k - 1):
                        fl.append((idx[0], idx[j], idx[j + 1]))
                faces = np.array(fl, dtype=np.int64)
    return verts[faces]


# ---------------------------------------------------------------- renderer
def render(tris, out, frames, W, H, color, up, elev, zoom, spin, ss=2):
    tris = tris.copy()
    if up == "y":  # convert y-up to z-up
        tris = tris[:, :, [0, 2, 1]] * np.array([1, -1, 1])
    c = (tris.reshape(-1, 3).min(0) + tris.reshape(-1, 3).max(0)) / 2
    tris -= c
    r = np.linalg.norm(tris.reshape(-1, 3), axis=1).max()
    tris /= r
    n = np.cross(tris[:, 1] - tris[:, 0], tris[:, 2] - tris[:, 0])
    nl = np.linalg.norm(n, axis=1, keepdims=True); nl[nl == 0] = 1
    n /= nl
    base = np.array(color, dtype=np.float64) / 255.0

    W2, H2 = W * ss, H * ss
    bg = (251, 250, 246)  # site --card
    light = np.array([-0.45, -0.6, 0.65]); light /= np.linalg.norm(light)   # fixed, upper-left-front
    el = math.radians(elev)
    imgs = []
    for fi in range(frames):
        th = 2 * math.pi * fi / frames * spin
        # rotate model about z
        cz, sz = math.cos(th), math.sin(th)
        Rz = np.array([[cz, -sz, 0], [sz, cz, 0], [0, 0, 1]])
        v = tris @ Rz.T
        nn = n @ Rz.T
        # camera: looking along +y (into the screen), tilted down by elev
        ce, se = math.cos(el), math.sin(el)
        Rx = np.array([[1, 0, 0], [0, ce, -se], [0, se, ce]])
        v = v @ Rx.T; nn = nn @ Rx.T
        # screen coords: x right, z up, y depth
        depth = v[:, :, 1].mean(1)
        # backface cull (camera looks along +y, so visible normals have ny < 0)
        vis = nn[:, 1] < 0.05
        # perspective
        d = 3.2
        yy = v[:, :, 1] + d
        sx = v[:, :, 0] / yy * (d * 0.62 * zoom)
        sy = v[:, :, 2] / yy * (d * 0.62 * zoom)
        px = (sx * H2 * 0.5 + W2 / 2)
        py = (-sy * H2 * 0.5 + H2 / 2 + H2 * 0.03)
        # shading (Blinn-Phong)
        ndl = np.clip(nn @ light, 0, 1)
        view = np.array([0, -1, 0.0])
        h = light + view; h /= np.linalg.norm(h)
        spec = np.clip(nn @ h, 0, 1) ** 40
        amb = 0.28
        rgb = base[None, :] * (amb + 0.72 * ndl[:, None]) + 0.45 * spec[:, None]
        rgb = np.clip(rgb, 0, 1)
        rgb8 = (rgb * 255).astype(np.uint8)
        order = np.argsort(-depth)  # far first
        order = order[vis[order]]
        im = Image.new("RGB", (W2, H2), bg)
        # soft ground shadow
        sh = Image.new("L", (W2, H2), 0)
        ImageDraw.Draw(sh).ellipse([W2 * 0.22, H2 * 0.80, W2 * 0.78, H2 * 0.93], fill=70)
        sh = sh.filter(ImageFilter.GaussianBlur(H2 * 0.03))
        im.paste((215, 212, 204), mask=sh)
        dr = ImageDraw.Draw(im)
        pxs, pys = px[order], py[order]
        cols = rgb8[order]
        for i in range(len(order)):
            col = (int(cols[i, 0]), int(cols[i, 1]), int(cols[i, 2]))
            dr.polygon([(pxs[i, 0], pys[i, 0]), (pxs[i, 1], pys[i, 1]), (pxs[i, 2], pys[i, 2])], fill=col, outline=col)
        im = im.resize((W, H), Image.LANCZOS)
        imgs.append(im)
        print(f"frame {fi + 1}/{frames}", file=sys.stderr)
    # quantize with a shared palette for a smaller, flicker-free gif
    pal = imgs[len(imgs)//3].convert("P", palette=Image.ADAPTIVE, colors=COLORS)
    q = [im.quantize(palette=pal, dither=Image.NONE) for im in imgs]
    q[0].save(out, save_all=True, append_images=q[1:], duration=int(1000 * 4 / frames), loop=0, optimize=True)
    imgs[0].save(out.replace(".gif", "-poster.png"))


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("mesh"); ap.add_argument("out")
    ap.add_argument("--frames", type=int, default=48)
    ap.add_argument("--size", default="720x480")
    ap.add_argument("--color", default="120,170,235")
    ap.add_argument("--up", default="z")
    ap.add_argument("--elev", type=float, default=22)
    ap.add_argument("--zoom", type=float, default=1.0)
    ap.add_argument("--spin", type=float, default=1)
    ap.add_argument("--colors", type=int, default=64)
    a = ap.parse_args()
    COLORS = a.colors
    tris = load_stl(a.mesh) if a.mesh.lower().endswith(".stl") else load_ply(a.mesh)
    print(f"{len(tris)} triangles", file=sys.stderr)
    W, H = map(int, a.size.split("x"))
    render(tris, a.out, a.frames, W, H, tuple(map(int, a.color.split(","))), a.up, a.elev, a.zoom, a.spin)
