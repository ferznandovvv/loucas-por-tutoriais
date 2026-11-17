#!/usr/bin/env python3
"""Carrossel EDITORIAL do @loucasportutoriais (aprovado em 16/11/2026).
Capa: fundo creme, titulo serifado (DM Serif Display) com palavras em italico rosa, fotos inteiras lado a lado.
Slides internos: formato de post de rede social (avatar, nome, selo, @), texto curto com **negrito**,
fotos INTEIRAS (sem corte) embaixo, rotulos discretos.
Uso: python3 editorial.py post.json pasta_saida pasta_fotos [pasta_fotos2 ...]

post.json:
{
 "cover": {"lines": [["Lateral", ""], ["fina", "i"], [" ou", ""], ["larga?", "i"]] ... ver exemplo em conteudo/,
           "sub": "...", "tag": "BIQUÍNI 101", "photos": [{"photo": "a.jpg", "label": "Fina"}, ...]},
 "slides": [
   {"text": "**No quadril:** texto curto", "photos": [{"photo": "x.jpg", "label": "Fina"}, ...]},
   {"text": "...", "grid": [{"photo": "y.jpg", "label": "Tangão"}, ...], "cols": 3}
 ],
 "final": {"text": "...", "photos": [...], "code": "LOUCAS15", "code_note": "15% off", "cta": "Link na bio"}
}
"""
import json, os, re, sys
from PIL import Image, ImageDraw, ImageFont, ImageFilter

W, H = 1080, 1350
HERE = os.path.dirname(os.path.abspath(__file__))
FONTS = os.path.join(HERE, "fonts")
INTER = "/usr/share/fonts/opentype/inter/"
BG, CARD, INK, ACC, MUTE = (243, 237, 230), (255, 255, 255), (36, 28, 25), (178, 74, 98), (128, 112, 106)
NAME, HANDLE = "Loucas por Tutoriais", "@loucasportutoriais"
DIRS = []


def F(kind, size):
    paths = {
        "serif": [os.path.join(FONTS, "DMSerifDisplay-Regular.ttf")],
        "serif_i": [os.path.join(FONTS, "DMSerifDisplay-Italic.ttf")],
        "reg": [INTER + "Inter-Regular.otf", os.path.join(FONTS, "LiberationSans-Regular.ttf")],
        "med": [INTER + "Inter-Medium.otf", os.path.join(FONTS, "LiberationSans-Regular.ttf")],
        "semi": [INTER + "Inter-SemiBold.otf", os.path.join(FONTS, "LiberationSans-Bold.ttf")],
        "bold": [INTER + "Inter-Bold.otf", os.path.join(FONTS, "LiberationSans-Bold.ttf")],
    }[kind]
    for p in paths:
        if os.path.exists(p):
            return ImageFont.truetype(p, size)
    raise FileNotFoundError(kind)


def load(name):
    for d in DIRS:
        p = os.path.join(d, name)
        if os.path.exists(p):
            return Image.open(p).convert("RGB")
    raise FileNotFoundError(name)


def sharpen_if_upscaled(src, out):
    if out.width > src.width * 1.05:
        return out.filter(ImageFilter.UnsharpMask(radius=2, percent=60, threshold=2))
    return out


def paste_round(img, ph, x, y, radius):
    if radius:
        m = Image.new("L", ph.size, 0)
        ImageDraw.Draw(m).rounded_rectangle([0, 0, ph.width - 1, ph.height - 1], radius=radius, fill=255)
        img.paste(ph, (x, y), m)
    else:
        img.paste(ph, (x, y))


def photos_row(img, photos, top, bottom, side=70, gap=16, radius=20, label_size=26):
    """Fotos INTEIRAS lado a lado, ocupando o maximo do espaco. Rotulo embaixo de cada uma."""
    d = ImageDraw.Draw(img)
    has_label = any(p.get("label") for p in photos)
    lab_h = 52 if has_label else 0
    srcs = [load(p["photo"]) for p in photos]
    ratios = [s.width / s.height for s in srcs]
    h = min(bottom - top - lab_h, (W - 2 * side - gap * (len(srcs) - 1)) / sum(ratios))
    ws = [int(h * r) for r in ratios]
    x = (W - sum(ws) - gap * (len(srcs) - 1)) // 2
    y = top + int((bottom - top - lab_h - h) // 2)
    lf = F("semi", label_size)
    for s, w, p in zip(srcs, ws, photos):
        ph = sharpen_if_upscaled(s, s.resize((w, int(h)), Image.LANCZOS))
        paste_round(img, ph, x, y, radius)
        if p.get("label"):
            lab = " ".join(p["label"].upper())
            d.text((x + w / 2, y + h + 16), lab, font=lf, fill=INK, anchor="ma")
        x += w + gap


def fill_crop(src, w, h, fx=0.5, fy=0.5):
    r = max(w / src.width, h / src.height)
    im = src.resize((int(src.width * r + 0.5), int(src.height * r + 0.5)), Image.LANCZOS)
    x, y = int((im.width - w) * fx), int((im.height - h) * fy)
    return sharpen_if_upscaled(src, im.crop((x, y, x + w, y + h)))


def grid(img, photos, top, bottom, cols, side=70, gap=14, radius=16):
    d = ImageDraw.Draw(img)
    rows = (len(photos) + cols - 1) // cols
    lab_h = 46
    cw = (W - 2 * side - gap * (cols - 1)) // cols
    ch = min(int(cw * 1.3), (bottom - top - rows * lab_h - gap * (rows - 1)) // rows)
    tot_w = cw * cols + gap * (cols - 1)
    x0 = (W - tot_w) // 2
    y0 = top + (bottom - top - (ch + lab_h) * rows - gap * (rows - 1)) // 2
    lf = F("semi", 22)
    for i, p in enumerate(photos):
        r, c = divmod(i, cols)
        x, y = x0 + c * (cw + gap), y0 + r * (ch + lab_h + gap)
        paste_round(img, fill_crop(load(p["photo"]), cw, ch, p.get("fx", 0.5), p.get("fy", 0.5)), x, y, radius)
        if p.get("label"):
            d.text((x + cw / 2, y + ch + 12), " ".join(p["label"].upper()), font=lf, fill=INK, anchor="ma")


# ---------------- texto com **negrito** ----------------
def rich_lines(d, text, size, maxw):
    fr, fb = F("reg", size), F("bold", size)
    words = []
    for part in re.split(r"(\*\*[^*]+\*\*)", text):
        if not part:
            continue
        bold = part.startswith("**")
        for w in part.strip("*").split():
            words.append((w, bold))
    lines, cur, cw = [], [], 0
    sp = d.textlength(" ", font=fr)
    for w, b in words:
        ww = d.textlength(w, font=fb if b else fr)
        if cur and cw + sp + ww > maxw:
            lines.append(cur)
            cur, cw = [], 0
        cw += (sp if cur else 0) + ww
        cur.append((w, b, ww))
    if cur:
        lines.append(cur)
    return lines, fr, fb, sp


def draw_rich(d, text, x, y, size=42, maxw=W - 140, lh=1.38, color=INK):
    out = []
    for para in text.split("\n"):
        if not para.strip():
            y += int(size * 0.6)
            continue
        lines, fr, fb, sp = rich_lines(d, para, size, maxw)
        for ln in lines:
            cx = x
            for w, b, ww in ln:
                d.text((cx, y), w, font=fb if b else fr, fill=color)
                cx += ww + sp
            y += int(size * lh)
    return y


# ---------------- cabecalho estilo post ----------------
def avatar(size):
    p = os.path.join(HERE, "avatar.png")
    if os.path.exists(p):
        src = Image.open(p).convert("RGB")
        w, h = src.size
        c = int(min(w, h) * 0.86)
        src = src.crop(((w - c) // 2, (h - c) // 2 + int(h * 0.03), (w - c) // 2 + c, (h - c) // 2 + c + int(h * 0.03)))
        a = src.resize((size, size), Image.LANCZOS)
    else:
        a = Image.new("RGB", (size, size), ACC)
    m = Image.new("L", (size, size), 0)
    ImageDraw.Draw(m).ellipse([0, 0, size - 1, size - 1], fill=255)
    return a, m


def badge(d, x, y, r=14):
    d.ellipse([x, y, x + 2 * r, y + 2 * r], fill=(29, 155, 240))
    d.line([(x + r * 0.55, y + r * 1.0), (x + r * 0.9, y + r * 1.35), (x + r * 1.5, y + r * 0.65)], fill=(255, 255, 255), width=4)


def header(img, n=None, total=None):
    d = ImageDraw.Draw(img)
    a, m = avatar(92)
    img.paste(a, (70, 64), m)
    fn = F("bold", 34)
    d.text((182, 70), NAME, font=fn, fill=INK)
    badge(d, 182 + d.textlength(NAME, font=fn) + 10, 74)
    d.text((182, 116), HANDLE, font=F("reg", 28), fill=MUTE)
    if n:
        d.text((W - 70, 78), f"{n}/{total}", font=F("med", 26), fill=MUTE, anchor="ra")
    return d


# ---------------- slides ----------------
def render_cover(c, out):
    img = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(img)
    small = F("semi", 24)
    d.text((64, 52), NAME.upper(), font=small, fill=MUTE)
    if c.get("tag"):
        d.text((W - 64, 52), c["tag"].upper(), font=small, fill=MUTE, anchor="ra")
    size = c.get("size", 132)
    f1, f2 = F("serif", size), F("serif_i", size)
    y = c.get("top", 110)
    for line in c["lines"]:  # cada linha: lista de [texto, "i" ou ""]
        x = 60
        for txt, st in line:
            f = f2 if st == "i" else f1
            d.text((x, y), txt, font=f, fill=ACC if st == "i" else INK)
            x += d.textlength(txt, font=f)
        y += int(size * 1.06)
    y += 34
    if c.get("sub"):
        d.text((64, y), c["sub"], font=F("reg", 34), fill=MUTE)
        y += 56
    photos_row(img, c["photos"], y + 24, H - 70, side=44)
    d.text((W - 64, H - 34), "arrasta  →", font=F("med", 26), fill=MUTE, anchor="rs")
    img.save(out, quality=94)


def render_post(s, n, total, out):
    img = Image.new("RGB", (W, H), BG)
    d = header(img, n, total)
    y = draw_rich(d, s["text"], 70, 200, s.get("size", 46))
    top = y + 34
    if s.get("grid"):
        grid(img, s["grid"], top, H - 50, s.get("cols", 3), side=50)
    elif s.get("photos"):
        photos_row(img, s["photos"], top, H - 50, side=44)
    img.save(out, quality=94)


def render_final(fz, n, total, out):
    img = Image.new("RGB", (W, H), BG)
    d = header(img, n, total)
    y = draw_rich(d, fz["text"], 70, 200, fz.get("size", 46))
    y += 30
    if fz.get("code"):
        fc = F("bold", 56)
        tw = d.textlength(fz["code"], font=fc)
        d.rounded_rectangle([70, y, 70 + tw + 64, y + 96], radius=18, fill=ACC)
        d.text((102, y + 16), fz["code"], font=fc, fill=(255, 255, 255))
        if fz.get("code_note"):
            d.text((70 + tw + 92, y + 28), fz["code_note"], font=F("bold", 38), fill=INK)
        y += 120
    if fz.get("cta"):
        d.text((70, y), fz["cta"], font=F("med", 34), fill=MUTE)
        y += 60
    if fz.get("photos"):
        photos_row(img, fz["photos"], y + 10, H - 50, side=44)
    img.save(out, quality=94)


def main():
    data = json.load(open(sys.argv[1], encoding="utf-8"))
    outdir = sys.argv[2]
    DIRS.extend(sys.argv[3:])
    os.makedirs(outdir, exist_ok=True)
    total = 1 + len(data["slides"]) + (1 if data.get("final") else 0)
    render_cover(data["cover"], os.path.join(outdir, "slide_01.jpg"))
    for i, s in enumerate(data["slides"]):
        render_post(s, i + 2, total, os.path.join(outdir, f"slide_{i + 2:02d}.jpg"))
    if data.get("final"):
        render_final(data["final"], total, total, os.path.join(outdir, f"slide_{total:02d}.jpg"))
    print(total, "slides em", outdir)


if __name__ == "__main__":
    main()
