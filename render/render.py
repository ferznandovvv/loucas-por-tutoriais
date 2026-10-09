#!/usr/bin/env python3
"""Renderizador Loucas por Tutoriais.
Uso: python3 render.py pauta.json pasta_saida [pasta_fotos]
Gera carrosseis (PNG 1080x1350), reels (MP4 1080x1920 com motion) e stories (PNG 1080x1920).
Marcacao de destaque no texto: **palavra** vira italico serifado em rosa.
"""
import json, math, os, re, subprocess, sys
from PIL import Image, ImageDraw, ImageFilter, ImageFont

# ---------------- identidade ----------------
OFF = (247, 241, 236)
BLUSH = (242, 217, 213)
INK = (30, 26, 29)
ROSE = (194, 105, 122)
ROSE_DARK = (150, 70, 88)
WHITE = (255, 255, 255)
HANDLE = "@loucasportutoriais"

FONT_DIRS = ["/usr/share/fonts/opentype/inter", "/usr/share/fonts/truetype/google-fonts",
             os.path.join(os.path.dirname(os.path.abspath(__file__)), "fonts")]
FONT_FILES = {
    "black": ["InterDisplay-Black.otf", "Inter-Black.otf", "Poppins-Bold.ttf"],
    "bold": ["InterDisplay-Bold.otf", "Inter-Bold.otf", "Poppins-Bold.ttf"],
    "semi": ["Inter-SemiBold.otf", "Poppins-Medium.ttf"],
    "body": ["Inter-Medium.otf", "Poppins-Regular.ttf"],
    "reg": ["Inter-Regular.otf", "Poppins-Regular.ttf"],
    "serif": ["Lora-Italic-Variable.ttf", "Poppins-Italic.ttf"],
}
_font_cache = {}


def font(kind, size):
    key = (kind, size)
    if key in _font_cache:
        return _font_cache[key]
    for name in FONT_FILES[kind]:
      for d in FONT_DIRS:
        p = os.path.join(d, name)
        if os.path.exists(p):
            f = ImageFont.truetype(p, size)
            if kind == "serif":
                try:
                    f.set_variation_by_name("SemiBold")
                except Exception:
                    pass
            _font_cache[key] = f
            return f
    sys.stderr.write(f"AVISO: fonte {kind} nao encontrada, usando padrao\n")
    f = ImageFont.load_default(size)
    _font_cache[key] = f
    return f


# ---------------- texto com destaque ----------------
def tokens(text):
    """Quebra em palavras: (palavra, destaque, colada_na_anterior)."""
    out = []
    parts = re.split(r"(\*\*[^*]+\*\*)", text)
    for p in parts:
        if not p:
            continue
        acc = p.startswith("**") and p.endswith("**")
        body = p[2:-2] if acc else p
        glue_first = bool(out) and not p[0].isspace() and not acc
        for i, w in enumerate(body.split()):
            out.append((w, acc, glue_first and i == 0))
    return out


def line_width(l, sp):
    return sum(t[2] for t in l) + sum(sp for j, t in enumerate(l) if j > 0 and not t[3])


def layout(text, size, maxw, kind="black", line_gap=1.08, upper=False):
    """Retorna linhas: lista de listas de (palavra, destaque, largura, colada)."""
    f_main, f_acc = font(kind, size), font("serif", int(size * 1.02))
    space = f_main.getlength(" ")
    lines, cur = [], []
    for w, acc, glue in tokens(text):
        fw = f_acc.getlength(w) if acc else f_main.getlength(w.upper() if upper else w)
        item = (w, acc, fw, glue)
        if cur and not glue and line_width(cur + [item], space) > maxw:
            lines.append(cur)
            cur = [(w, acc, fw, False)]
        else:
            cur.append(item)
    if cur:
        lines.append(cur)
    lh = int(size * line_gap)
    return lines, lh, space


def fit(text, maxw, maxh, start, minimum, kind="black", line_gap=1.08, upper=False):
    s = start
    while s > minimum:
        lines, lh, sp = layout(text, s, maxw, kind, line_gap, upper)
        if len(lines) * lh <= maxh and all(line_width(l, sp) <= maxw for l in lines):
            return s, lines, lh, sp
        s -= 2
    lines, lh, sp = layout(text, minimum, maxw, kind, line_gap, upper)
    return minimum, lines, lh, sp


def draw_lines(d, lines, lh, sp, size, x, y, color, acc_color, kind="black", align="left", boxw=None, upper=False):
    f_main, f_acc = font(kind, size), font("serif", int(size * 1.02))
    for i, l in enumerate(lines):
        lw = line_width(l, sp)
        cx = x + ((boxw - lw) / 2 if align == "center" and boxw else 0)
        cy = y + i * lh
        for j, (w, acc, fw, glue) in enumerate(l):
            if j > 0 and not glue:
                cx += sp
            if acc:
                d.text((cx, cy - size * 0.06), w, font=f_acc, fill=acc_color)
            else:
                d.text((cx, cy), w.upper() if upper else w, font=f_main, fill=color)
            cx += fw
    return y + len(lines) * lh


# ---------------- fotos ----------------
def load_photo(name, photos_dir):
    if not name or not photos_dir:
        return None
    p = os.path.join(photos_dir, name)
    if not os.path.exists(p):
        return None
    try:
        return Image.open(p).convert("RGB")
    except Exception:
        return None


def cover_crop(img, w, h, scale=1.0, fx=0.5, fy=0.4):
    r = max(w / img.width, h / img.height) * scale
    im = img.resize((max(w, int(img.width * r)), max(h, int(img.height * r))), Image.LANCZOS)
    x = int((im.width - w) * fx)
    y = int((im.height - h) * fy)
    return im.crop((x, y, x + w, y + h))


def gradient_bottom(w, h, start=0.35, strength=235):
    g = Image.new("L", (1, h))
    for yy in range(h):
        t = max(0, (yy / h - start) / (1 - start))
        g.putpixel((0, yy), int(strength * (t ** 1.4)))
    g = g.resize((w, h))
    black = Image.new("RGBA", (w, h), (15, 10, 14, 255))
    black.putalpha(g)
    return black


def gradient_top(w, h, frac=0.2, strength=150):
    g = Image.new("L", (1, h), 0)
    lim = int(h * frac)
    for yy in range(lim):
        g.putpixel((0, yy), int(strength * (1 - yy / lim) ** 1.6))
    g = g.resize((w, h))
    black = Image.new("RGBA", (w, h), (15, 10, 14, 255))
    black.putalpha(g)
    return black


SHOW_CREDITS = False  # o Fernando pediu para nao mostrar a origem da foto na arte


def credit(d, text, w, h, y=None):
    if not text or not SHOW_CREDITS:
        return
    f = font("reg", 22)
    tw = f.getlength(text)
    d.text((w - tw - 40, (y if y is not None else h - 52)), text, font=f, fill=(255, 255, 255, 200))


# ---------------- carrossel ----------------
CW, CH = 1080, 1350
M = 90


def header(d, n, total, dark=False):
    col = WHITE if dark else INK
    d.text((M, 64), HANDLE, font=font("semi", 26), fill=col)
    if n and total:
        s = f"{n:02d}/{total:02d}"
        f = font("semi", 26)
        d.text((CW - M - f.getlength(s), 64), s, font=f, fill=col)


def swipe_hint(d, dark):
    col = WHITE if dark else ROSE_DARK
    f = font("semi", 26)
    t = "arrasta pro lado"
    tw = f.getlength(t)
    x = CW - M - tw - 60
    y = CH - 92
    d.text((x, y), t, font=f, fill=col)
    ax = CW - M - 40
    d.line([(ax, y + 17), (ax + 40, y + 17)], fill=col, width=4)
    d.line([(ax + 26, y + 5), (ax + 40, y + 17), (ax + 26, y + 29)], fill=col, width=4)


def render_cover(post, photos_dir, total):
    cv = post["cover"]
    photo = load_photo(cv.get("photo"), photos_dir)
    if photo:
        img = cover_crop(photo, CW, CH, 1.0, cv.get("focus", 0.5), 0.3).convert("RGBA")
        img.alpha_composite(gradient_bottom(CW, CH, 0.30, 240))
        img.alpha_composite(gradient_top(CW, CH))
        d = ImageDraw.Draw(img)
        header(d, None, None, dark=True)
        tag = post.get("tag", "").upper()
        size, lines, lh, sp = fit(cv["headline"], CW - 2 * M, 470, 112, 60, upper=True)
        sub_f = font("body", 36)
        sub_h = 60 if cv.get("sub") else 0
        y = CH - 150 - sub_h - len(lines) * lh
        if tag:
            tf = font("bold", 24)
            tw = tf.getlength(tag)
            d.rounded_rectangle([M, y - 70, M + tw + 36, y - 26], radius=22, fill=ROSE)
            d.text((M + 18, y - 64), tag, font=tf, fill=WHITE)
        y = draw_lines(d, lines, lh, sp, size, M, y, WHITE, (244, 178, 190), upper=True)
        if cv.get("sub"):
            d.text((M, y + 14), cv["sub"], font=sub_f, fill=(240, 232, 230))
        credit(d, cv.get("credit"), CW, CH, y=40 + 64)
        swipe_hint(d, True)
        return img.convert("RGB")
    # capa tipografica
    img = Image.new("RGB", (CW, CH), BLUSH)
    d = ImageDraw.Draw(img)
    d.ellipse([CW - 420, -260, CW + 260, 420], fill=(236, 200, 196))
    d.ellipse([-300, CH - 380, 300, CH + 220], fill=(238, 206, 202))
    header(d, None, None)
    tag = post.get("tag", "").upper()
    size, lines, lh, sp = fit(cv["headline"], CW - 2 * M, 640, 124, 64, upper=True)
    block = len(lines) * lh + (90 if cv.get("sub") else 0)
    y = (CH - block) // 2 + 20
    if tag:
        tf = font("bold", 24)
        tw = tf.getlength(tag)
        d.rounded_rectangle([M, y - 80, M + tw + 36, y - 36], radius=22, fill=INK)
        d.text((M + 18, y - 74), tag, font=tf, fill=WHITE)
    y = draw_lines(d, lines, lh, sp, size, M, y, INK, ROSE_DARK, upper=True)
    if cv.get("sub"):
        d.text((M, y + 20), cv["sub"], font=font("body", 38), fill=(80, 64, 70))
    swipe_hint(d, False)
    return img


def render_slide(slide, n, total, photos_dir):
    img = Image.new("RGB", (CW, CH), OFF)
    d = ImageDraw.Draw(img)
    header(d, n, total)
    photo = load_photo(slide.get("photo"), photos_dir)
    top = 150
    if photo:
        ph = cover_crop(photo, CW - 2 * M, 640, 1.0, slide.get("focus", 0.5), 0.3)
        mask = Image.new("L", ph.size, 0)
        ImageDraw.Draw(mask).rounded_rectangle([0, 0, ph.width, ph.height], radius=28, fill=255)
        img.paste(ph, (M, top), mask)
        if slide.get("credit") and SHOW_CREDITS:
            f = font("reg", 20)
            d.text((M, top + 648), slide["credit"], font=f, fill=(120, 108, 112))
        top += 710
    avail = CH - top - 150
    maxw = CW - 2 * M
    t = slide.get("title")
    tb = slide.get("text")
    tsize = tlines = None
    th = 0
    if t:
        tsize, tlines, tlh, tsp = fit(t, maxw, min(340, int(avail * 0.45)), 84, 46)
        th = len(tlines) * tlh + (48 if not photo else 0) + 34
    bh = 0
    if tb:
        bsize, blines, blh, bsp = fit(tb, maxw, avail - th, 56, 32, kind="body", line_gap=1.36)
        bh = len(blines) * blh
    block = th + bh
    y = top + (max(40, int((avail - block) * 0.42)) if not photo else 24)
    if t:
        if not photo:
            d.rectangle([M, y, M + 70, y + 8], fill=ROSE)
            y += 48
        y = draw_lines(d, tlines, tlh, tsp, tsize, M, y, INK, ROSE) + 34
    if tb:
        draw_lines(d, blines, blh, bsp, bsize, M, y, (62, 52, 58), ROSE_DARK, kind="body")
    if n < total:
        f = font("semi", 24)
        d.text((CW - M - f.getlength("continua"), CH - 84), "continua", font=f, fill=(150, 130, 136))
    return img


def bookmark(d, x, y, s, col, width=5):
    d.line([(x, y), (x + s, y), (x + s, y + s * 1.35), (x + s / 2, y + s * 0.95), (x, y + s * 1.35), (x, y)], fill=col, width=width, joint="curve")


def plane(d, x, y, s, col, width=5):
    pts = [(x, y + s * 0.45), (x + s, y), (x + s * 0.62, y + s), (x + s * 0.45, y + s * 0.58), (x, y + s * 0.45)]
    d.line(pts, fill=col, width=width, joint="curve")
    d.line([(x + s * 0.45, y + s * 0.58), (x + s, y)], fill=col, width=width)


def render_final(post, total):
    fin = post["final"]
    img = Image.new("RGB", (CW, CH), INK)
    d = ImageDraw.Draw(img)
    header(d, total, total, dark=True)
    size, lines, lh, sp = fit(fin["text"], CW - 2 * M, 520, 84, 48)
    y = 330
    y = draw_lines(d, lines, lh, sp, size, M, y, WHITE, (244, 178, 190))
    y += 80
    d.rectangle([M, y, CW - M, y + 2], fill=(90, 78, 84))
    y += 60
    cta = fin.get("cta", "Salva pra consultar depois e manda pra uma amiga")
    csize, clines, clh, csp = fit(cta, CW - 2 * M - 140, 260, 44, 30, kind="semi", line_gap=1.3)
    bookmark(d, M + 6, y + 6, 44, (244, 178, 190))
    plane(d, M + 70, y + 8, 50, (244, 178, 190))
    draw_lines(d, clines, clh, csp, csize, M + 150, y, (235, 225, 228), (244, 178, 190), kind="semi")
    return img


def render_carousel(post, outdir, photos_dir):
    total = len(post["slides"]) + 2
    files = []
    imgs = [render_cover(post, photos_dir, total)]
    for i, s in enumerate(post["slides"]):
        imgs.append(render_slide(s, i + 2, total, photos_dir))
    imgs.append(render_final(post, total))
    for i, im in enumerate(imgs):
        p = os.path.join(outdir, f"slide_{i + 1:02d}.png")
        im.save(p, optimize=True)
        files.append(p)
    return files


# ---------------- reels (motion) ----------------
RW, RH, FPS = 1080, 1920, 30
SAFE_L, SAFE_R, SAFE_T, SAFE_B = 90, 190, 300, 420


def ease_out(t):
    t = max(0.0, min(1.0, t))
    return 1 - (1 - t) ** 3


def ease_in(t):
    t = max(0.0, min(1.0, t))
    return t ** 3


def blob_sprite(r, color, alpha=170):
    pad = 160
    size = r * 2 + pad * 2
    m = Image.new("L", (size, size), 0)
    ImageDraw.Draw(m).ellipse([pad, pad, pad + 2 * r, pad + 2 * r], fill=alpha)
    m = m.filter(ImageFilter.GaussianBlur(60))
    s = Image.new("RGBA", (size, size), color + (0,))
    s.putalpha(m)
    return s


class Backdrop:
    def __init__(self, palette):
        self.base = palette
        self.blobs = [
            (blob_sprite(380, (236, 190, 190)), 0.2, 0.25, 0.11, 0.3),
            (blob_sprite(300, (250, 228, 214)), 0.8, 0.6, 0.08, 1.7),
            (blob_sprite(260, (226, 170, 180), 140), 0.35, 0.85, 0.13, 3.1),
        ]

    def frame(self, t):
        img = Image.new("RGBA", (RW, RH), self.base + (255,))
        for spr, bx, by, sp, ph in self.blobs:
            x = int(bx * RW + math.sin(t * sp * 2 * math.pi + ph) * 140 - spr.width / 2)
            y = int(by * RH + math.cos(t * sp * 2 * math.pi * 0.8 + ph) * 160 - spr.height / 2)
            sx, sy = max(0, -x), max(0, -y)
            ex, ey = min(spr.width, RW - x), min(spr.height, RH - y)
            if ex > sx and ey > sy:
                img.alpha_composite(spr, (x + sx, y + sy), (sx, sy, ex, ey))
        return img


def word_sprites(text, size, maxw, color, acc_color, kind="black", upper=True):
    lines, lh, sp = layout(text, size, maxw, kind, 1.05, upper)
    f_main, f_acc = font(kind, size), font("serif", int(size * 1.02))
    out = []
    for li, l in enumerate(lines):
        x = 0
        for j, (w, acc, fw, glue) in enumerate(l):
            if j > 0 and not glue:
                x += sp
            word = w if acc else (w.upper() if upper else w)
            f = f_acc if acc else f_main
            spr = Image.new("RGBA", (int(fw) + 20, int(size * 1.35)), (0, 0, 0, 0))
            ImageDraw.Draw(spr).text((4, (-size * 0.06 if acc else 0) + 6), word, font=f, fill=acc_color if acc else color)
            out.append({"img": spr, "line": li, "x": x, "acc": acc})
            x += fw
    return out, len(lines), int(size * 1.05)


def render_reel(reel, outpath, photos_dir):
    scenes = reel["scenes"]
    total = sum(s.get("dur", 2.5) for s in scenes)
    nframes = int(total * FPS)
    back = Backdrop(BLUSH)
    prepared = []
    for s in scenes:
        photo = load_photo(s.get("photo"), photos_dir)
        dark = photo is not None or s.get("style") == "dark"
        color = WHITE if dark else INK
        acc = (244, 178, 190) if dark else ROSE_DARK
        size_start = s.get("size", 118)
        maxw = RW - SAFE_L - SAFE_R
        maxh = RH - SAFE_T - SAFE_B - 200
        size = size_start
        while size > 56:
            lines, lh, spc = layout(s["text"], size, maxw, "black", 1.05, True)
            if len(lines) * lh <= maxh and len(lines) <= 6 and all(line_width(l, spc) <= maxw for l in lines):
                break
            size -= 4
        words, nl, lh = word_sprites(s["text"], size, maxw, color, acc)
        big = None
        if photo:
            big = cover_crop(photo, RW, RH, 1.0, s.get("focus", 0.5), 0.35)
        prepared.append({"s": s, "photo": big, "dark": dark, "words": words, "nl": nl, "lh": lh, "size": size})

    proc = subprocess.Popen([
        "ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{RW}x{RH}", "-r", str(FPS),
        "-i", "-", "-f", "lavfi", "-i", "anullsrc=r=44100:cl=stereo", "-shortest",
        "-c:v", "libx264", "-preset", "medium", "-crf", "19", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "128k",
        "-movflags", "+faststart", outpath], stdin=subprocess.PIPE)
    grad = gradient_bottom(RW, RH, 0.0, 170)
    gtop = gradient_top(RW, RH, 0.18, 150)
    t0 = 0.0
    starts = []
    for s in scenes:
        starts.append(t0)
        t0 += s.get("dur", 2.5)
    for fi in range(nframes):
        t = fi / FPS
        si = max(i for i, st in enumerate(starts) if st <= t + 1e-6)
        P = prepared[si]
        dur = P["s"].get("dur", 2.5)
        lt = t - starts[si]
        # fundo
        if P["photo"] is not None:
            k = lt / dur
            sc = 1.0 + 0.10 * ease_out(k)
            ph = P["photo"]
            bw, bh = ph.width / sc, ph.height / sc
            ox = (ph.width - bw) / 2 + 25 * math.sin(k * math.pi)
            oy = (ph.height - bh) / 2
            frame = ph.crop((int(ox), int(oy), int(ox + bw), int(oy + bh))).resize((RW, RH), Image.BILINEAR).convert("RGBA")
            frame.alpha_composite(grad)
            frame.alpha_composite(gtop)
            ov = Image.new("RGBA", (RW, RH), (20, 12, 16, 70))
            frame.alpha_composite(ov)
            if P["s"].get("credit"):
                credit(ImageDraw.Draw(frame), P["s"]["credit"], RW, RH, y=230)
        elif P["dark"]:
            frame = Image.new("RGBA", (RW, RH), INK + (255,))
        else:
            frame = back.frame(t)
        d = ImageDraw.Draw(frame)
        # barra de progresso e handle
        d.rectangle([0, 0, RW, 10], fill=(255, 255, 255, 60) if P["dark"] else (30, 26, 29, 30))
        d.rectangle([0, 0, int(RW * t / total), 10], fill=ROSE + (255,))
        hc = WHITE if P["dark"] else INK
        d.text((SAFE_L, 150), HANDLE, font=font("semi", 30), fill=hc)
        # palavras
        block_h = P["nl"] * P["lh"]
        y0 = SAFE_T + (RH - SAFE_T - SAFE_B - block_h) // 2
        if P["s"].get("align") == "bottom":
            y0 = RH - SAFE_B - block_h - 40
        out_t = ease_in((lt - (dur - 0.28)) / 0.28) if lt > dur - 0.28 and si < len(scenes) - 1 else 0
        for wi, w in enumerate(P["words"]):
            delay = 0.04 + wi * 0.075
            k = ease_out((lt - delay) / 0.38)
            if k <= 0:
                continue
            spr = w["img"]
            if w["acc"] and k < 1:
                s2 = 0.6 + 0.4 * k + 0.12 * math.sin(k * math.pi)
                spr = spr.resize((max(1, int(spr.width * s2)), max(1, int(spr.height * s2))), Image.BILINEAR)
            a = int(255 * k * (1 - out_t))
            if a <= 0:
                continue
            if a < 255:
                spr = spr.copy()
                alpha = spr.getchannel("A").point(lambda v, a=a: v * a // 255)
                spr.putalpha(alpha)
            x = SAFE_L + int(w["x"]) + (w["img"].width - spr.width) // 2
            y = y0 + w["line"] * P["lh"] + int((1 - k) * 70) - int(out_t * 120) + (w["img"].height - spr.height) // 2
            frame.alpha_composite(spr, (max(0, x), max(0, y)))
        # sublinha animado em cenas de gancho
        if P["s"].get("underline"):
            k = ease_out((lt - 0.5) / 0.5)
            yl = y0 + block_h + 30
            d.rectangle([SAFE_L, yl, SAFE_L + int(260 * k), yl + 12], fill=ROSE + (255,))
        proc.stdin.write(frame.convert("RGB").tobytes())
    proc.stdin.close()
    proc.wait()
    return outpath


# ---------------- stories ----------------
def render_story(st, outpath, photos_dir):
    W, H = 1080, 1920
    photo = load_photo(st.get("photo"), photos_dir)
    if photo:
        img = cover_crop(photo, W, H, 1.0, st.get("focus", 0.5), 0.25).convert("RGBA")
        img.alpha_composite(gradient_bottom(W, H, 0.42, 245))
        img.alpha_composite(gradient_top(W, H, 0.16, 140))
        color, acc = WHITE, (244, 178, 190)
    else:
        img = Image.new("RGBA", (W, H), (BLUSH if st.get("style") != "dark" else INK) + (255,))
        if st.get("style") != "dark":
            d0 = ImageDraw.Draw(img)
            d0.ellipse([W - 500, -300, W + 300, 500], fill=(236, 200, 196))
            d0.ellipse([-350, H - 500, 350, H + 250], fill=(238, 206, 202))
        color = INK if st.get("style") != "dark" else WHITE
        acc = ROSE_DARK if st.get("style") != "dark" else (244, 178, 190)
    d = ImageDraw.Draw(img)
    d.text((90, 170), HANDLE, font=font("semi", 30), fill=color)
    size, lines, lh, sp = fit(st["text"], W - 180, 620, 96, 52, upper=True)
    hint_h = 70 if st.get("hint") else 0
    if photo:
        # foto: texto embaixo, para nao cobrir o rosto; o adesivo vai no meio da tela
        y = H - 360 - hint_h - len(lines) * lh
        ky = y - 100
    else:
        y = 400
        ky = 300
    if st.get("kicker"):
        kf = font("bold", 28)
        kw = kf.getlength(st["kicker"].upper())
        d.rounded_rectangle([90, ky, 90 + kw + 40, ky + 52], radius=26, fill=ROSE)
        d.text((110, ky + 9), st["kicker"].upper(), font=kf, fill=WHITE)
    y = draw_lines(d, lines, lh, sp, size, 90, y, color, acc, upper=True)
    if st.get("hint"):
        d.text((90, y + 30), st["hint"], font=font("body", 36), fill=color)
    return img.convert("RGB").save(outpath, optimize=True)


# ---------------- main ----------------
def main():
    data = json.load(open(sys.argv[1], encoding="utf-8"))
    out = sys.argv[2]
    photos = sys.argv[3] if len(sys.argv) > 3 else None
    os.makedirs(out, exist_ok=True)
    made = []
    for post in data.get("posts", []):
        pdir = os.path.join(out, f"post_{post['id']:02d}")
        os.makedirs(pdir, exist_ok=True)
        made += render_carousel(post, pdir, photos)
    for i, reel in enumerate(data.get("reels", [])):
        p = os.path.join(out, f"reel_{i + 1:02d}.mp4")
        render_reel(reel, p, photos)
        made.append(p)
    sdir = os.path.join(out, "stories")
    if data.get("stories"):
        os.makedirs(sdir, exist_ok=True)
        for i, st in enumerate(data["stories"]):
            p = os.path.join(sdir, f"story_{i + 1:02d}.png")
            render_story(st, p, photos)
            made.append(p)
    print("\n".join(made))


if __name__ == "__main__":
    main()
