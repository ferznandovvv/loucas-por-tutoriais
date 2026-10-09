#!/usr/bin/env python3
"""Carrossel do @loucasportutoriais (modelo aprovado em 09/10/2026, referencia @marcioeugeniooficial).
Capa: foto em tela cheia, circulos com fotos extras, manchete condensada com tarja colorida, linha de apoio, rodape 'ENTENDA'.
Slides internos: estilo 'post de rede social' em fundo branco, cabecalho com perfil, texto narrativo com negrito e foto com cantos arredondados.
Uso: python3 carrossel.py pauta.json pasta_saida pasta_fotos [pasta_fotos2 ...]
pauta.json pode ter {"posts": [{"id": 1, "cover": {...}, "slides": [...]}, ...]} (gera post_01/, post_02/...)
ou ser um post solto {"cover": {...}, "slides": [...]}.
"""
import json, os, re, sys
from PIL import Image, ImageDraw, ImageFont, ImageFilter

W, H = 1080, 1350
HERE = os.path.dirname(os.path.abspath(__file__))
LIB = os.path.join(HERE, "fonts") + "/"
ACCENT = (226, 32, 98)       # rosa forte (tarja)
NAME = "Loucas por Tutoriais"
HANDLE = "@loucasportutoriais"


def F(kind, size):
    if kind == "cond":
        f = ImageFont.truetype(os.path.join(HERE, "fonts", "Oswald[wght].ttf"), size)
        f.set_variation_by_name("Bold")
        return f
    if kind == "condreg":
        f = ImageFont.truetype(os.path.join(HERE, "fonts", "Oswald[wght].ttf"), size)
        f.set_variation_by_name("Regular")
        return f
    return ImageFont.truetype(LIB + ("LiberationSans-Bold.ttf" if kind == "bold" else "LiberationSans-Regular.ttf"), size)


PHOTO_DIRS = []


def photo(name):
    if not name:
        return None
    for d in PHOTO_DIRS:
        p = os.path.join(d, name)
        if os.path.exists(p):
            return Image.open(p).convert("RGB")
    sys.stderr.write(f"AVISO: foto {name} nao encontrada\n")
    return None


def crop(img, w, h, fx=0.5, fy=0.4, zoom=1.0):
    iw, ih = img.size
    s = max(w / iw, h / ih) * zoom
    img = img.resize((int(iw * s + 1), int(ih * s + 1)), Image.LANCZOS)
    iw, ih = img.size
    x = int(max(0, min(iw - w, fx * iw - w / 2)))
    y = int(max(0, min(ih - h, fy * ih - h / 2)))
    return img.crop((x, y, x + w, y + h))


def toks(text):
    """[(palavra, negrito)] com quebras de paragrafo como ('\n', None)."""
    out = []
    for para_i, para in enumerate(text.split("\n\n")):
        if para_i:
            out.append(("\n", None))
        for part in re.split(r"(\*\*[^*]+\*\*)", para):
            if not part:
                continue
            b = part.startswith("**")
            for w in part.strip("*").split():
                out.append((w, b))
    return out


def wrap(tokens, fonts, maxw):
    lines, cur, curw = [], [], 0
    for w, b in tokens:
        if b is None:
            lines.append(cur)
            lines.append(None)  # paragrafo
            cur, curw = [], 0
            continue
        f = fonts[b]
        ww = f.getlength(w)
        sp = f.getlength(" ")
        add = ww + (sp if cur else 0)
        if cur and curw + add > maxw:
            lines.append(cur)
            cur, curw = [(w, b)], ww
        else:
            cur.append((w, b))
            curw += add
    if cur:
        lines.append(cur)
    return lines


# ---------------- capa ----------------
def gradient(img, start, amax=250):
    g = Image.new("L", (1, H))
    for y in range(H):
        t = max(0.0, (y - start) / (H - start))
        g.putpixel((0, y), int(amax * min(1.0, t * 1.5)))
    top = Image.new("L", (1, H))
    for y in range(H):
        top.putpixel((0, y), int(110 * max(0.0, 1 - y / 220)))
    g = Image.fromarray if False else g
    mask = Image.new("L", (W, H))
    mask.paste(g.resize((W, H)))
    from PIL import ImageChops
    mask = ImageChops.lighter(mask, top.resize((W, H)))
    return Image.composite(Image.new("RGB", (W, H), (0, 0, 0)), img, mask)


def circle(base, img, cx, cy, r, fx=0.5, fy=0.5, zoom=1.0):
    c = crop(img, 2 * r, 2 * r, fx, fy, zoom)
    m = Image.new("L", (2 * r * 2, 2 * r * 2), 0)
    ImageDraw.Draw(m).ellipse([0, 0, 4 * r - 1, 4 * r - 1], fill=255)
    m = m.resize((2 * r, 2 * r), Image.LANCZOS)
    sh = Image.new("L", (W, H), 0)
    ImageDraw.Draw(sh).ellipse([cx - r - 4, cy - r + 6, cx + r + 4, cy + r + 16], fill=140)
    sh = sh.filter(ImageFilter.GaussianBlur(14))
    base.paste((0, 0, 0), (0, 0), sh)
    ImageDraw.Draw(base).ellipse([cx - r - 7, cy - r - 7, cx + r + 7, cy + r + 7], fill=(255, 255, 255))
    base.paste(c, (cx - r, cy - r), m)


def headline(d, text, y_bottom, maxw=980, start=104, minimum=60, max_h=430):
    text = text.upper()
    size = start
    while True:
        f = F("cond", size)
        tk = [(w, b) for w, b in toks(text) if b is not None]
        lines = wrap(tk, {True: f, False: f}, maxw - 40)
        lh = int(size * 1.2)
        if (len(lines) * lh <= max_h and len(lines[-1]) >= 2) or size <= minimum:
            break
        size -= 2
    sp = f.getlength(" ")
    y = y_bottom - lh * len(lines)
    top_y = y
    pad = int(size * 0.13)
    for line in lines:
        widths = [f.getlength(w) for w, _ in line]
        lw = sum(widths) + sp * (len(line) - 1)
        x = (W - lw) / 2
        i = 0
        while i < len(line):
            if line[i][1]:
                j = i
                while j + 1 < len(line) and line[j + 1][1]:
                    j += 1
                bx = x + sum(widths[:i]) + sp * i
                bw = sum(widths[i:j + 1]) + sp * (j - i)
                _, gt, _, gb = f.getbbox("ÁH")
                d.rectangle([bx - pad, y + gt - pad * 0.6, bx + bw + pad, y + gb + pad * 0.9], fill=ACCENT)
                i = j + 1
            else:
                i += 1
        cx = x
        for (w, b), ww in zip(line, widths):
            d.text((cx, y), w, font=f, fill=(255, 255, 255))
            cx += ww + sp
        y += lh
    return top_y


def rich_center(d, text, y, size, color=(255, 255, 255)):
    tk = [(w, b) for w, b in toks(text) if b is not None]
    fonts = {True: F("bold", size), False: F("reg", size)}
    widths = [fonts[b].getlength(w) for w, b in tk]
    sp = fonts[False].getlength(" ")
    lw = sum(widths) + sp * (len(tk) - 1)
    x = (W - lw) / 2
    for (w, b), ww in zip(tk, widths):
        d.text((x, y), w, font=fonts[b], fill=color)
        x += ww + sp


def footer(img, d):
    col = (240, 240, 240)
    a, m = avatar(48)
    img.paste(a, (44, H - 84), m)
    d.text((104, H - 60), HANDLE, font=F("reg", 30), fill=col, anchor="lm")
    d.text((W - 118, H - 60), "ENTENDA", font=F("condreg", 34), fill=col, anchor="rm")
    d.line([W - 104, H - 60, W - 50, H - 60], fill=col, width=3)
    d.line([W - 64, H - 70, W - 50, H - 60], fill=col, width=3)
    d.line([W - 64, H - 50, W - 50, H - 60], fill=col, width=3)


def render_cover(c, out):
    img = crop(photo(c["photo"]), W, H, c.get("focus", 0.5), c.get("focus_y", 0.4), c.get("zoom", 1.0))
    img = gradient(img, int(H * 0.40))
    for ci in c.get("circles", []):
        p = photo(ci["photo"])
        if p:
            circle(img, p, ci["x"], ci["y"], ci.get("r", 150), ci.get("fx", 0.5), ci.get("fy", 0.5), ci.get("zoom", 1.0))
    d = ImageDraw.Draw(img)
    has_sub = bool(c.get("sub"))
    bottom = H - 190 if has_sub else H - 130
    headline(d, c["headline"], bottom)
    if has_sub:
        rich_center(d, c["sub"], H - 172, 42)
    footer(img, d)
    img.save(out, quality=94)


# ---------------- slides estilo post ----------------
AVATAR = os.path.join(HERE, "avatar.png")


def avatar(size):
    if os.path.exists(AVATAR):
        src = Image.open(AVATAR).convert("RGB")
        w, h = src.size
        c = int(min(w, h) * 0.86)
        src = src.crop(((w - c) // 2, (h - c) // 2 + int(h * 0.03), (w - c) // 2 + c, (h - c) // 2 + c + int(h * 0.03)))
        a = src.resize((size, size), Image.LANCZOS)
    else:
        a = Image.new("RGB", (size, size), ACCENT)
        ImageDraw.Draw(a).text((size / 2, size / 2), "L", font=F("bold", int(size * 0.5)), fill="white", anchor="mm")
    m = Image.new("L", (size * 4, size * 4), 0)
    ImageDraw.Draw(m).ellipse([0, 0, size * 4 - 1, size * 4 - 1], fill=255)
    return a, m.resize((size, size), Image.LANCZOS)


def verified(img, x, y, size):
    """Selo verificado azul (rosetinha com check branco)."""
    import math
    S = size * 4
    b = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    d = ImageDraw.Draw(b)
    cx = cy = S / 2
    pts = []
    for i in range(48):
        a = 2 * math.pi * i / 48
        r = S * (0.47 if i % 4 in (0, 1) else 0.40) if False else S * (0.44 + 0.05 * math.cos(8 * a))
        pts.append((cx + r * math.cos(a), cy + r * math.sin(a)))
    d.polygon(pts, fill=(29, 155, 240, 255))
    w = int(S * 0.09)
    d.line([(S * 0.29, S * 0.51), (S * 0.44, S * 0.65), (S * 0.71, S * 0.36)], fill="white", width=w, joint="curve")
    b = b.resize((size, size), Image.LANCZOS)
    img.paste(b, (int(x), int(y)), b)


def rounded(img, r):
    m = Image.new("L", (img.width * 2, img.height * 2), 0)
    ImageDraw.Draw(m).rounded_rectangle([0, 0, img.width * 2 - 1, img.height * 2 - 1], r * 2, fill=255)
    return m.resize(img.size, Image.LANCZOS)


def render_post(s, n, total, out):
    img = Image.new("RGB", (W, H), (255, 255, 255))
    d = ImageDraw.Draw(img)
    M = 50
    a, m = avatar(112)
    img.paste(a, (M, 48), m)
    d.text((M + 134, 62), NAME, font=F("bold", 46), fill=(20, 20, 20))
    verified(img, M + 134 + F("bold", 46).getlength(NAME) + 12, 66, 44)
    d.text((M + 134, 116), HANDLE, font=F("reg", 34), fill=(120, 120, 120))
    pass

    p = photo(s.get("photo"))
    text_top = 222
    min_ph = 400 if p else 0
    text_bottom = H - 40 - (min_ph + 40 if p else 0)
    size = s.get("size", 54)
    while size >= 36:
        fonts = {True: F("bold", size), False: F("reg", size)}
        lines = wrap(toks(s["text"]), fonts, W - 2 * M - 10)
        lh = int(size * 1.22)
        hh = sum(int(lh * 0.55) if l is None else lh for l in lines)
        if text_top + hh <= text_bottom:
            break
        size -= 2
    y = text_top
    for line in lines:
        if line is None:
            y += int(lh * 0.55)
            continue
        x = M
        for i, (w, b) in enumerate(line):
            f = fonts[b]
            d.text((x, y), w, font=f, fill=(25, 25, 25))
            x += f.getlength(w) + f.getlength(" ")
        y += lh
    if p:
        top = int(y + 34)
        ph_h = H - 40 - top
        ph = crop(p, W - 2 * M, ph_h, s.get("focus", 0.5), s.get("focus_y", 0.45), s.get("zoom", 1.0))
        img.paste(ph, (M, top), rounded(ph, 28))
    img.save(out, quality=94)


def render_post_set(post, outdir):
    os.makedirs(outdir, exist_ok=True)
    total = 1 + len(post["slides"])
    render_cover(post["cover"], os.path.join(outdir, "slide_01.jpg"))
    for i, s in enumerate(post["slides"], start=2):
        render_post(s, i, total, os.path.join(outdir, f"slide_{i:02d}.jpg"))
    return total


def main():
    data = json.load(open(sys.argv[1]))
    outdir = sys.argv[2]
    PHOTO_DIRS.extend(sys.argv[3:])
    posts = data.get("posts") or [dict(data, id=1)]
    for n, post in enumerate(posts, start=1):
        d = os.path.join(outdir, f"post_{int(post.get('id', n)):02d}")
        print(d, render_post_set(post, d), "slides")


if __name__ == "__main__":
    main()
