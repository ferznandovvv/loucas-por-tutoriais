#!/usr/bin/env python3
"""Baixa as fotos do dia para o @loucasportutoriais.

Le pedidos/AAAA-MM-DD.json e grava em fotos/AAAA-MM-DD/:
  type "article": abre a materia, pega a foto principal (og:image) e ate 3 alternativas do corpo
  type "image":   baixa a URL direta de imagem
  type "ai":      gera a imagem pela API do Gemini (precisa do secret GEMINI_API_KEY)
Ao final grava status.json com o resultado de cada item.
"""
import base64, io, json, os, re, sys, time
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup
from PIL import Image

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/129.0 Safari/537.36")
S = requests.Session()
S.headers.update({"User-Agent": UA, "Accept-Language": "pt-BR,pt;q=0.9,en;q=0.8"})
MIN_SIDE = 480


SEEN = set()


def fingerprint(im):
    small = im.convert("L").resize((12, 12))
    px = list(small.getdata())
    avg = sum(px) / len(px)
    return "".join("1" if p > avg else "0" for p in px)


def save_image(data, path):
    im = Image.open(io.BytesIO(data))
    im = im.convert("RGB")
    if min(im.size) < MIN_SIDE:
        raise ValueError(f"imagem pequena demais {im.size}")
    fp = fingerprint(im)
    if fp in SEEN:
        raise ValueError("imagem repetida")
    SEEN.add(fp)
    if max(im.size) > 2400:
        im.thumbnail((2400, 2400))
    im.save(path, "JPEG", quality=90)
    return im.size


def fetch(url, referer=None):
    h = {"Referer": referer} if referer else {}
    r = S.get(url, timeout=25, headers=h)
    r.raise_for_status()
    return r


def article_images(url):
    html = fetch(url).text
    soup = BeautifulSoup(html, "html.parser")
    cands = []
    for prop in ["og:image", "og:image:secure_url", "twitter:image", "twitter:image:src"]:
        for tag in soup.find_all("meta", attrs={"property": prop}) + soup.find_all("meta", attrs={"name": prop}):
            c = tag.get("content")
            if c:
                cands.append(urljoin(url, c))
    for img in (soup.select("article img") or soup.select("main img, figure img")):
        src = img.get("data-src") or img.get("data-lazy-src") or img.get("src")
        srcset = img.get("srcset") or img.get("data-srcset")
        if srcset:
            best = sorted(
                [(int(re.sub(r"\D", "", p.split()[-1]) or 0), p.split()[0]) for p in srcset.split(",") if p.strip() and len(p.split()) > 1],
                reverse=True)
            if best:
                src = best[0][1]
        if src and not src.startswith("data:"):
            cands.append(urljoin(url, src))
    seen, out = set(), []
    for c in cands:
        key = c.split("?")[0]
        if key not in seen and not re.search(r"(logo|icon|avatar|sprite|placeholder)", c, re.I):
            seen.add(key)
            out.append(c)
    return out


def gemini_model(key):
    forced = os.environ.get("GEMINI_IMAGE_MODEL", "").strip()
    if forced:
        return forced
    r = S.get("https://generativelanguage.googleapis.com/v1beta/models", params={"key": key, "pageSize": 200}, timeout=25)
    r.raise_for_status()
    names = [m["name"].split("/")[-1] for m in r.json().get("models", [])
             if "generateContent" in m.get("supportedGenerationMethods", []) and "image" in m["name"]
             and "imagen" not in m["name"]]
    if not names:
        raise RuntimeError("nenhum modelo de imagem do Gemini disponivel nessa chave")
    stable = sorted([n for n in names if "preview" not in n], reverse=True)
    return (stable or sorted(names, reverse=True))[0]


def gemini_image(prompt, aspect, key, model):
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
    body = {"contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {"responseModalities": ["IMAGE"], "imageConfig": {"aspectRatio": aspect}}}
    r = S.post(url, params={"key": key}, json=body, timeout=120)
    if r.status_code == 400 and "imageConfig" in r.text:
        body["generationConfig"].pop("imageConfig")
        body["contents"][0]["parts"][0]["text"] = prompt + f" Vertical composition, aspect ratio {aspect}."
        r = S.post(url, params={"key": key}, json=body, timeout=120)
    r.raise_for_status()
    for cand in r.json().get("candidates", []):
        for part in cand.get("content", {}).get("parts", []):
            inline = part.get("inlineData") or part.get("inline_data")
            if inline and inline.get("data"):
                return base64.b64decode(inline["data"])
    raise RuntimeError("Gemini nao devolveu imagem: " + r.text[:300])


def free_image(prompt, aspect):
    """Gerador gratuito sem chave (Pollinations). Tenta algumas vezes porque a fila gratuita oscila."""
    from urllib.parse import quote
    w, h = {"4:5": (1080, 1350), "9:16": (1080, 1920), "1:1": (1080, 1080)}.get(aspect, (1080, 1350))
    last = None
    for attempt in range(4):
        url = (f"https://image.pollinations.ai/prompt/{quote(prompt)}"
               f"?width={w}&height={h}&nologo=true&private=true&seed={int(time.time()) % 100000 + attempt}")
        try:
            r = S.get(url, timeout=180)
            if r.status_code == 200 and r.headers.get("content-type", "").startswith("image"):
                im = Image.open(io.BytesIO(r.content)).convert("RGB")
                im = im.crop((0, 0, im.width, int(im.height * 0.93)))  # remove a marca d'agua do rodape
                buf = io.BytesIO()
                im.save(buf, "JPEG", quality=92)
                return buf.getvalue()
            last = f"HTTP {r.status_code}: {r.text[:150]}"
        except Exception as e:
            last = str(e)
        time.sleep(15)
    raise RuntimeError("gerador gratuito falhou: " + str(last))


def main():
    pedido_path = sys.argv[1]
    pedido = json.load(open(pedido_path, encoding="utf-8"))
    date = pedido["date"]
    outdir = os.path.join("fotos", date)
    os.makedirs(outdir, exist_ok=True)
    key = os.environ.get("GEMINI_API_KEY", "").strip()
    model = None
    status = {"date": date, "finished_at": None, "items": []}
    for it in pedido["items"]:
        name = it["file"]
        base = os.path.splitext(name)[0]
        res = {"file": name, "type": it["type"], "ok": False, "alts": []}
        try:
            if it["type"] == "article":
                imgs = article_images(it["url"])
                saved = 0
                for img_url in imgs:
                    if saved >= 4:
                        break
                    try:
                        data = fetch(img_url, referer=it["url"]).content
                        target = name if saved == 0 else f"{base}_alt{saved}.jpg"
                        size = save_image(data, os.path.join(outdir, target))
                        if saved == 0:
                            res.update(ok=True, source=img_url, size=size)
                        else:
                            res["alts"].append({"file": target, "source": img_url, "size": size})
                        saved += 1
                    except Exception:
                        continue
                if not saved:
                    res["error"] = f"nenhuma imagem utilizavel ({len(imgs)} candidatas)"
            elif it["type"] == "image":
                size = save_image(fetch(it["url"], referer=it.get("referer")).content, os.path.join(outdir, name))
                res.update(ok=True, source=it["url"], size=size)
            elif it["type"] == "ai":
                aspect = it.get("aspect", "4:5")
                use_gemini = key and os.environ.get("USE_GEMINI", "") == "1"
                if use_gemini:
                    model = model or gemini_model(key)
                    data = gemini_image(it["prompt"], aspect, key, model)
                    res["model"] = model
                else:
                    data = free_image(it["prompt"], aspect)
                    res["model"] = "pollinations-gratuito"
                size = save_image(data, os.path.join(outdir, name))
                res.update(ok=True, size=size)
        except Exception as e:
            res["error"] = str(e)[:300]
        status["items"].append(res)
        print(json.dumps(res, ensure_ascii=False))
        time.sleep(0.5)
    status["finished_at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    json.dump(status, open(os.path.join(outdir, "status.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=2)


if __name__ == "__main__":
    main()
