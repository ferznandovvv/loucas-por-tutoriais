#!/usr/bin/env python3
"""Carrossel de PRODUTO do @loucasportutoriais: foto em tela cheia em todos os slides, pouco texto.
Uso: python3 produto.py post.json pasta_saida pasta_fotos [pasta_fotos2 ...]

post.json:
{
 "cover": {"photos": [{"photo": "a.jpg", "fy": 0.3}, ...] (1 a 3 fotos lado a lado),
           "headline": "QUAL **BIQUÍNI** ESCOLHER?", "sub": "linha curta"},
 "slides": [
   {"photo": "x.jpg", "fy": 0.25, "fx": 0.5, "kicker": "Quer sustentação?", "title": "Meia taça",
    "text": "uma frase curta", "pos": "bottom" | "top"}
 ],
 "final": {"photo": "y.jpg", "fy": 0.3, "title": "...", "text": "...", "code": "LOUCAS10", "cta": "..."}
}
**palavra** na manchete da capa ganha a tarja rosa.
"""
import json, os, re, sys
from PIL import Image, ImageDraw, ImageFont, ImageFilter

W, H = 1080, 1350
HERE = os.path.dirname(os.path.abspath(__file__))
PINK = (226, 32, 98)
HANDLE = "@loucasportutoriais"
DIRS = []


def F(kind, size):
    if kind in ("cond", "condreg"):
        f = ImageFont.truetype(os.path.join(HERE, "fonts", "Oswald[wght].ttf"), size)
        f.set_variation_by_name("Bold" if kind == "cond" else "Regular")
        return f
    name = "LiberationSans-Bold.ttf" if kind == "bold" else "LiberationSans-Regular.ttf"
    return ImageFont.truetype(os.path.join(HERE, "fonts", name), size)


def load(name):
    for d in DIRS:
        p = os.path.join(d, name)
        if os.path.exists(p):
            return Image.open(p).convert("RGB")
    raise FileNotFoundError(name)


def fill(img, w, h, fx=0.5, fy=0.3, zoom=1.0):
    r = max(w / img.width, h / img.height) * zoom
    im = img.resize((int(img.width * r + 0.5), int(img.height * r + 0.5)), Image.LANCZOS)
    x = int((im.width - w) * fx)
    y = int((im.height - h) * fy)
    im = im.crop((x, y, x + w, y + h))
    if r > 1.05:  # foto ampliada: devolve um pouco de nitidez
        im = im.filter(ImageFilter.UnsharpMask(radius=2, percent=70, threshold=2))
    return im


def shade(img, top_frac=0.0, bottom_frac=0.42, strength=235, top_strength=150):
    w, h = img.size
    m = Image.new("L", (1, h), 0)
    for y in range(h):
        v = 0
        b0 = h * (1 - bottom_frac)
        if y > b0:
            v = max(v, int(strength * ((y - b0) / (h - b0)) ** 1.3))
        t1 = h * top_frac
        if top_frac and y < t1:
            v = max(v, int(top_strength * (1 - y / t1) ** 1.5))
        m.putpixel((0, y), v)
    m = m.resize((w, h))
    dark = Image.new("RGB", (w, h), (12, 8, 10))
    return Image.composite(dark, img, m)


def txt(d, xy, text, font, fill=(255, 255, 255)):
    x, y = xy
    for dx, dy in ((2, 2), (0, 2), (2, 0), (-1, 1)):
        d.text((x + dx, y + dy), text, font=font, fill=(10, 6, 8))
    d.text((x, y), text, font=font, fill=fill)


def wrap(d, text, font, maxw):
    words, lines, cur = text.split(), [], ""
    for wd in words:
        t = (cur + " " + wd).strip()
        if d.textlength(t, font=font) <= maxw or not cur:
            cur = t
        else:
            lines.append(cur)
            cur = wd
    if cur:
        lines.append(cur)
    return lines


def tarja(d, x, y, text, font, pad=14, fill=PINK, color=(255, 255, 255)):
    tw = d.textlength(text, font=font)
    asc, desc = font.getmetrics()
    d.rectangle([x, y, x + tw + 2 * pad, y + asc + desc + 6], fill=fill)
    d.text((x + pad, y + 2), text, font=font, fill=color)
    return y + asc + desc + 6


def headline_rich(d, text, y_bottom, size=104, maxw=W - 120):
    """Manchete centralizada em caixa alta; trechos **assim** ganham tarja rosa. Desenha de baixo pra cima."""
    f = F("cond", size)
    parts = re.split(r"(\*\*[^*]+\*\*)", text.upper())
    toks = []
    for p in parts:
        if not p:
            continue
        hi = p.startswith("**")
        for wd in p.strip("*").split():
            toks.append((wd, hi))
    lines, cur = [], []
    for t in toks:
        trial = " ".join(w for w, _ in cur + [t])
        if cur and d.textlength(trial, font=f) > maxw:
            lines.append(cur)
            cur = [t]
        else:
            cur.append(t)
    lines.append(cur)
    lh = int(size * 1.08)
    y = y_bottom - lh * len(lines)
    top = y
    sp = d.textlength(" ", font=f)
    for ln in lines:
        tw = d.textlength(" ".join(w for w, _ in ln), font=f)
        x = (W - tw) / 2
        for wd, hi in ln:
            ww = d.textlength(wd, font=f)
            if hi:
                d.rectangle([x - 10, y + int(size * 0.16), x + ww + 10, y + lh + int(size * 0.06)], fill=PINK)
            d.text((x, y), wd, font=f, fill=(255, 255, 255))
            x += ww + sp
        y += lh
    return top


def handle(d, light=True, y=56):
    d.text((60, y), HANDLE, font=F("bold", 30), fill=(255, 255, 255) if light else (30, 30, 30))


def counter(d, n, total, y=56):
    s = f"{n}/{total}"
    f = F("bold", 30)
    d.text((W - 60 - d.textlength(s, font=f), y), s, font=f, fill=(255, 255, 255))


def rounded_paste(bg, ph, x, y, radius=26):
    sh = Image.new("L", bg.size, 0)
    ImageDraw.Draw(sh).rounded_rectangle([x + 6, y + 10, x + ph.width + 6, y + ph.height + 10], radius=radius, fill=150)
    sh = sh.filter(ImageFilter.GaussianBlur(14))
    bg = Image.composite(Image.new("RGB", bg.size, (0, 0, 0)), bg, sh)
    m = Image.new("L", ph.size, 0)
    ImageDraw.Draw(m).rounded_rectangle([0, 0, ph.width, ph.height], radius=radius, fill=255)
    bg.paste(ph, (x, y), m)
    return bg


def render_cover_full(c, out):
    """Manchete no alto e as fotos INTEIRAS lado a lado embaixo."""
    srcs = [load(p["photo"]) for p in c["photos"]]
    bg = fill(srcs[0], W, H, 0.5, 0.5).filter(ImageFilter.GaussianBlur(40))
    bg = Image.blend(bg, Image.new("RGB", (W, H), (12, 8, 10)), 0.55)
    d = ImageDraw.Draw(bg)
    handle(d, y=40)
    hb = c.get("head_bottom", 330)
    top = headline_rich(d, c["headline"], hb, c.get("size", 116))
    y_sub = hb + 34
    if c.get("sub"):
        f = F("bold", 40)
        d.text(((W - d.textlength(c["sub"], font=f)) / 2, y_sub), c["sub"], font=f, fill=(255, 255, 255))
    gap, side = 26, 40
    area_top, area_bot = hb + 100, H - 90
    ratios = [im.width / im.height for im in srcs]
    h = min(area_bot - area_top, (W - 2 * side - gap * (len(srcs) - 1)) / sum(ratios))
    ws = [int(h * r) for r in ratios]
    x = (W - sum(ws) - gap * (len(srcs) - 1)) // 2
    y = area_top + int((area_bot - area_top - h) // 2)
    for im, w, p in zip(srcs, ws, c["photos"]):
        ph = im.resize((w, int(h)), Image.LANCZOS)
        bg = rounded_paste(bg, ph, x, y)
        if p.get("label"):
            pill(ImageDraw.Draw(bg), x + 16, y + 16, p["label"].upper(), size=46)
        x += w + gap
    d = ImageDraw.Draw(bg)
    f = F("condreg", 34)
    d.text((W - 120, H - 34), "ARRASTA", font=f, fill=(255, 255, 255), anchor="rs")
    ay = H - 48
    d.line([W - 108, ay, W - 60, ay], fill=(255, 255, 255), width=3)
    d.line([W - 74, ay - 12, W - 60, ay], fill=(255, 255, 255), width=3)
    d.line([W - 74, ay + 12, W - 60, ay], fill=(255, 255, 255), width=3)
    bg.save(out, quality=94)


def render_cover(c, out):
    if c.get("full"):
        return render_cover_full(c, out)
    ph = c["photos"]
    n = len(ph)
    gap = 8
    sw = (W - gap * (n - 1)) // n
    img = Image.new("RGB", (W, H), (255, 255, 255))
    for i, p in enumerate(ph):
        tile = fill(load(p["photo"]), sw if i < n - 1 else W - (sw + gap) * (n - 1), H, p.get("fx", 0.5), p.get("fy", 0.3), p.get("zoom", 1.0))
        img.paste(tile, (i * (sw + gap), 0))
    img = shade(img, top_frac=0.14, bottom_frac=0.45)
    d = ImageDraw.Draw(img)
    handle(d)
    sub_y = H - 120
    top = headline_rich(d, c["headline"], sub_y - 24, c.get("size", 112))
    if c.get("sub"):
        f = F("bold", 40)
        tw = d.textlength(c["sub"], font=f)
        d.text(((W - tw) / 2, sub_y), c["sub"], font=f, fill=(255, 255, 255))
    f = F("condreg", 34)
    d.text((W - 120, H - 40), "ARRASTA", font=f, fill=(255, 255, 255), anchor="rs")
    ay = H - 54
    d.line([W - 108, ay, W - 60, ay], fill=(255, 255, 255), width=3)
    d.line([W - 74, ay - 12, W - 60, ay], fill=(255, 255, 255), width=3)
    d.line([W - 74, ay + 12, W - 60, ay], fill=(255, 255, 255), width=3)
    img.save(out, quality=94)


def full_photo(name, top, bottom_margin=40, side=40, radius=26):
    """Foto INTEIRA (sem corte) sobre fundo desfocado da propria foto."""
    src = load(name)
    bg = fill(src, W, H, 0.5, 0.5).filter(ImageFilter.GaussianBlur(40))
    bg = Image.blend(bg, Image.new("RGB", (W, H), (12, 8, 10)), 0.55)
    box_w, box_h = W - 2 * side, H - top - bottom_margin
    r = min(box_w / src.width, box_h / src.height)
    ph = src.resize((int(src.width * r), int(src.height * r)), Image.LANCZOS)
    if r > 1.05:
        ph = ph.filter(ImageFilter.UnsharpMask(radius=2, percent=70, threshold=2))
    x, y = (W - ph.width) // 2, top + (box_h - ph.height) // 2
    sh = Image.new("L", (W, H), 0)
    ImageDraw.Draw(sh).rounded_rectangle([x + 6, y + 10, x + ph.width + 6, y + ph.height + 10], radius=radius, fill=150)
    sh = sh.filter(ImageFilter.GaussianBlur(14))
    bg = Image.composite(Image.new("RGB", (W, H), (0, 0, 0)), bg, sh)
    m = Image.new("L", ph.size, 0)
    ImageDraw.Draw(m).rounded_rectangle([0, 0, ph.width, ph.height], radius=radius, fill=255)
    bg.paste(ph, (x, y), m)
    return bg


def render_slide_full(s, n, total, out):
    """Texto numa faixa no alto, foto inteira embaixo."""
    tmp = ImageDraw.Draw(Image.new("RGB", (W, H)))
    fk, ft, fx = F("cond", 42), F("cond", 96), F("reg", 36)
    lines = wrap(tmp, s.get("text", ""), fx, W - 120) if s.get("text") else []
    asc, desc = ft.getmetrics()
    title_h = asc + desc - 12
    text_top = 110
    band = text_top + 62 + title_h + len(lines) * 46 + 26
    img = full_photo(s["photo"], band)
    d = ImageDraw.Draw(img)
    handle(d, y=40)
    counter(d, n, total, y=40)
    y = text_top
    if s.get("kicker"):
        tarja(d, 60, y, s["kicker"].upper(), fk)
    y += 62
    txt(d, (56, y - 12), s["title"].upper(), ft)
    y += title_h
    for ln in lines:
        txt(d, (60, y), ln, fx, (245, 240, 242))
        y += 46
    img.save(out, quality=94)


# ---------------- tipos extras: faixa de texto + pares, grade, linhas de medida, tabela ----------------
def band_metrics(s):
    tmp = ImageDraw.Draw(Image.new("RGB", (W, H)))
    fk, ft, fx = F("cond", 42), F("cond", s.get("title_size", 96)), F("reg", 36)
    lines = wrap(tmp, s.get("text", ""), fx, W - 120) if s.get("text") else []
    asc, desc = ft.getmetrics()
    title_lines = wrap(tmp, s["title"].upper(), ft, W - 120)
    title_h = (asc + desc - 12) * len(title_lines)
    band = 110 + (62 if s.get("kicker") else 0) + title_h + len(lines) * 46 + 26
    return band, (fk, ft, fx, lines, title_lines, asc + desc - 12)


def draw_band(img, s, n, total):
    band, (fk, ft, fx, lines, tlines, tlh) = band_metrics(s)
    d = ImageDraw.Draw(img)
    handle(d, y=40)
    if n:
        counter(d, n, total, y=40)
    y = 110
    if s.get("kicker"):
        tarja(d, 60, y, s["kicker"].upper(), fk)
        y += 62
    for tl in tlines:
        txt(d, (56, y - 12), tl, ft)
        y += tlh
    for ln in lines:
        txt(d, (60, y), ln, fx, (245, 240, 242))
        y += 46
    return d


def blur_bg(src):
    bg = fill(src, W, H, 0.5, 0.5).filter(ImageFilter.GaussianBlur(40))
    return Image.blend(bg, Image.new("RGB", (W, H), (12, 8, 10)), 0.55)


def pill(d, x, y, text, size=34, fill=PINK, color=(255, 255, 255), anchor_right=False):
    f = F("cond", size)
    tw = d.textlength(text, font=f)
    asc, desc = f.getmetrics()
    if anchor_right:
        x = x - tw - 28
    d.rounded_rectangle([x, y, x + tw + 28, y + asc + desc - 2], radius=10, fill=fill)
    d.text((x + 14, y - 3), text, font=f, fill=color)


def render_pair(s, n, total, out):
    srcs = [load(p["photo"]) for p in s["photos"]]
    band, _ = band_metrics(s)
    img = blur_bg(srcs[0])
    gap, side = 22, 36
    area_top, area_bot = band, H - 40
    ratios = [im.width / im.height for im in srcs]
    h = min(area_bot - area_top, (W - 2 * side - gap * (len(srcs) - 1)) / sum(ratios))
    ws = [int(h * r) for r in ratios]
    x = (W - sum(ws) - gap * (len(srcs) - 1)) // 2
    y = area_top + int((area_bot - area_top - h) // 2)
    for im, w, p in zip(srcs, ws, s["photos"]):
        ph = im.resize((w, int(h)), Image.LANCZOS)
        if im.width < w:
            ph = ph.filter(ImageFilter.UnsharpMask(radius=2, percent=60, threshold=2))
        img = rounded_paste(img, ph, x, y)
        if p.get("label"):
            pill(ImageDraw.Draw(img), x + 16, y + 16, p["label"].upper(), fill=p.get("color") and tuple(p["color"]) or PINK)
        x += w + gap
    draw_band(img, s, n, total)
    img.save(out, quality=94)


def render_grid(s, n, total, out):
    ph = s["photos"]
    band, _ = band_metrics(s)
    img = blur_bg(load(ph[0]["photo"]))
    cols = s.get("cols", 3 if len(ph) > 4 else 2)
    rows = (len(ph) + cols - 1) // cols
    gap, side = 18, 36
    area_top, area_bot = band, H - 40
    cw = (W - 2 * side - gap * (cols - 1)) // cols
    ch = min(int(cw * 1.33), (area_bot - area_top - gap * (rows - 1)) // rows)
    cw = min(cw, int(ch / 1.0))
    total_w = cw * cols + gap * (cols - 1)
    x0 = (W - total_w) // 2
    y0 = area_top + (area_bot - area_top - (ch * rows + gap * (rows - 1))) // 2
    for i, p in enumerate(ph):
        r, c = divmod(i, cols)
        tile = fill(load(p["photo"]), cw, ch, p.get("fx", 0.5), p.get("fy", 0.5), p.get("zoom", 1.0))
        x, y = x0 + c * (cw + gap), y0 + r * (ch + gap)
        img = rounded_paste(img, tile, x, y, radius=20)
        if p.get("label"):
            dd = ImageDraw.Draw(img)
            f = F("cond", 32)
            asc, desc = f.getmetrics()
            dd.rounded_rectangle([x, y + ch - asc - desc - 14, x + cw, y + ch], radius=20, fill=(20, 14, 17))
            dd.rectangle([x, y + ch - asc - desc - 14, x + cw, y + ch - 20], fill=(20, 14, 17))
            tw = dd.textlength(p["label"].upper(), font=f)
            dd.text((x + (cw - tw) / 2, y + ch - asc - desc - 12), p["label"].upper(), font=f, fill=(255, 255, 255))
    draw_band(img, s, n, total)
    img.save(out, quality=94)


def render_measure(s, n, total, out):
    """Foto inteira com linhas tracejadas de medida (busto, quadril)."""
    band, _ = band_metrics(s)
    src = load(s["photo"])
    img = blur_bg(src)
    side, bottom = 40, 40
    box_w, box_h = W - 2 * side, H - band - bottom
    r = min(box_w / src.width, box_h / src.height)
    ph = src.resize((int(src.width * r), int(src.height * r)), Image.LANCZOS)
    x, y = (W - ph.width) // 2, band + (box_h - ph.height) // 2
    img = rounded_paste(img, ph, x, y)
    d = ImageDraw.Draw(img)
    for ln in s.get("lines", []):
        ly = y + int(ph.height * ln["y"])
        x1 = x + int(ph.width * ln.get("x0", 0.18))
        x2 = x + int(ph.width * ln.get("x1", 0.82))
        dash = 22
        for xx in range(x1, x2, dash * 2):
            d.line([xx, ly, min(xx + dash, x2), ly], fill=(255, 255, 255), width=10)
            d.line([xx, ly, min(xx + dash, x2), ly], fill=PINK, width=6)
        pill(d, x2 + 14 if x2 + 200 < W else x2 - 10, ly - 26, ln["label"].upper(), size=38, anchor_right=x2 + 200 >= W)
    draw_band(img, s, n, total)
    img.save(out, quality=94)


def render_table(s, n, total, out):
    """Tabela comparativa desenhada (ex.: busto do P na meia taca x cortininha)."""
    img = Image.new("RGB", (W, H), (247, 240, 236))
    band, _ = band_metrics(s)
    dark = Image.new("RGB", (W, band), (24, 18, 21))
    img.paste(dark, (0, 0))
    t = s["table"]
    cols = t["cols"]
    rows = t["rows"]
    hl = t.get("highlight", [])
    x0, x1 = 60, W - 60
    cw = (x1 - x0) / len(cols)
    y = band + 50
    d = ImageDraw.Draw(img)
    fh = F("cond", 44)
    for i, c in enumerate(cols):
        tw = d.textlength(c.upper(), font=fh)
        d.text((x0 + cw * i + (cw - tw) / 2, y), c.upper(), font=fh, fill=PINK if i else (90, 70, 78))
    y += 80
    fr = F("bold", 46)
    rh = int(t.get("row_h", 104))
    for ri, row in enumerate(rows):
        if ri % 2 == 0:
            d.rectangle([x0, y, x1, y + rh], fill=(255, 255, 255))
        for ci, cell in enumerate(row):
            on = [ri, ci] in hl
            if on:
                d.rounded_rectangle([x0 + cw * ci + 14, y + 10, x0 + cw * (ci + 1) - 14, y + rh - 10], radius=14, fill=PINK)
            tw = d.textlength(cell, font=fr)
            d.text((x0 + cw * ci + (cw - tw) / 2, y + (rh - 54) / 2), cell, font=fr,
                   fill=(255, 255, 255) if on else (40, 30, 34))
        y += rh
    if t.get("note"):
        y += 40
        fn = F("bold", 42)
        for ln in wrap(d, t["note"], fn, W - 140):
            d.text((70, y), ln, font=fn, fill=(40, 30, 34))
            y += 56
    draw_band(img, s, n, total)
    img.save(out, quality=94)


KINDS = {"pair": render_pair, "grid": render_grid, "measure": render_measure, "table": render_table}


def render_slide(s, n, total, out):
    if s.get("kind") in KINDS:
        return KINDS[s["kind"]](s, n, total, out)
    if s.get("full"):
        return render_slide_full(s, n, total, out)
    pos = s.get("pos", "bottom")
    if s.get("contain"):
        # foto inteira (produto) sobre fundo escuro, texto embaixo
        img = Image.new("RGB", (W, H), (24, 18, 21))
        ph = load(s["photo"])
        box_h = H - 120 - 400
        r = min((W - 80) / ph.width, box_h / ph.height)
        ph = ph.resize((int(ph.width * r), int(ph.height * r)), Image.LANCZOS)
        img.paste(ph, ((W - ph.width) // 2, 120))
        pos = "bottom"
    else:
        img = fill(load(s["photo"]), W, H, s.get("fx", 0.5), s.get("fy", 0.3), s.get("zoom", 1.0))
        img = shade(img, top_frac=0.16 if pos == "bottom" else 0.45, bottom_frac=0.40 if pos == "bottom" else 0.0,
                    top_strength=150 if pos == "bottom" else 245)
    d = ImageDraw.Draw(img)
    handle(d)
    counter(d, n, total)
    fk, ft, fx = F("cond", 46), F("cond", 118), F("reg", 42)
    lines = wrap(d, s.get("text", ""), fx, W - 120) if s.get("text") else []
    asc, desc = ft.getmetrics()
    title_h = asc + desc - 10
    block = 70 + title_h + 10 + len(lines) * 54
    y = (H - 70 - block) if pos == "bottom" else 140
    if s.get("kicker"):
        tarja(d, 60, y, s["kicker"].upper(), fk)
    y += 70
    txt(d, (56, y - 14), s["title"].upper(), ft)
    y += title_h + 10
    for ln in lines:
        txt(d, (60, y), ln, fx, (245, 240, 242))
        y += 54
    img.save(out, quality=94)


def render_final(fz, n, total, out):
    img = fill(load(fz["photo"]), W, H, fz.get("fx", 0.5), fz.get("fy", 0.3), fz.get("zoom", 1.0))
    img = shade(img, top_frac=0.16, bottom_frac=0.55, strength=245)
    d = ImageDraw.Draw(img)
    handle(d)
    counter(d, n, total)
    y = H - 540
    ft = F("cond", 92)
    asc, desc = ft.getmetrics()
    for ln in wrap(d, fz["title"].upper(), ft, W - 120):
        txt(d, (56, y - 12), ln, ft)
        y += asc + desc - 4
    y += 10
    fx = F("reg", 40)
    for ln in wrap(d, fz.get("text", ""), fx, W - 120):
        txt(d, (60, y), ln, fx, (245, 240, 242))
        y += 52
    y += 22
    if fz.get("code"):
        fc = F("cond", 76)
        tw = d.textlength(fz["code"], font=fc)
        d.rounded_rectangle([60, y, 60 + tw + 60, y + 104], radius=16, outline=(255, 255, 255), width=4, fill=PINK)
        d.text((90, y + 4), fz["code"], font=fc, fill=(255, 255, 255))
        if fz.get("code_note"):
            txt(d, (60 + tw + 90, y + 30), fz["code_note"], F("bold", 40))
        y += 130
    if fz.get("cta"):
        txt(d, (60, y), fz["cta"], F("bold", 38))
    img.save(out, quality=94)


def main():
    data = json.load(open(sys.argv[1], encoding="utf-8"))
    outdir = sys.argv[2]
    DIRS.extend(sys.argv[3:])
    os.makedirs(outdir, exist_ok=True)
    total = 1 + len(data["slides"]) + (1 if data.get("final") else 0)
    render_cover(data["cover"], os.path.join(outdir, "slide_01.jpg"))
    for i, s in enumerate(data["slides"]):
        render_slide(s, i + 2, total, os.path.join(outdir, f"slide_{i + 2:02d}.jpg"))
    if data.get("final"):
        render_final(data["final"], total, total, os.path.join(outdir, f"slide_{total:02d}.jpg"))
    print(total, "slides em", outdir)


if __name__ == "__main__":
    main()
