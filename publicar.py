#!/usr/bin/env python3
"""Publica carrosseis do @loucasportutoriais pela API oficial do Instagram (Instagram API com login do Instagram).

Le todos os arquivos publicar/AAAA-MM-DD.json e publica os itens que:
  - estao com "aprovado": true,
  - ainda nao tem "publicado",
  - ja chegaram no "horario" (fuso America/Sao_Paulo).
Grava o resultado (id e link do post, ou o erro) de volta no proprio arquivo.

Formato de publicar/AAAA-MM-DD.json:
{
  "date": "AAAA-MM-DD",
  "posts": [
    {"id": "juliana", "tipo": "carrossel", "horario": "2026-10-10T12:00",
     "aprovado": true, "legenda": "texto com emojis e #hashtags",
     "midia": ["2026-10-10/juliana/01.jpg", "..."]}
  ]
}
As imagens ficam na branch "midia" deste repositorio (publico) e sao lidas pela API via raw.githubusercontent.com.

Variaveis de ambiente (secrets do GitHub):
  IG_ACCESS_TOKEN   token de longa duracao com instagram_business_basic e instagram_business_content_publish
  IG_USER_ID        ID da conta profissional do Instagram (o script descobre sozinho se faltar)
  GITHUB_REPOSITORY dono/repo (o GitHub Actions ja preenche)
  DRY_RUN=1         so confere arquivos e links, nao publica
  FORCAR=<arquivo>:<id>  publica esse item agora, ignorando o horario (ele ainda precisa estar aprovado)
"""
import glob, json, os, sys, time
from datetime import datetime, timedelta, timezone

import requests

API = "https://graph.instagram.com/" + os.environ.get("GRAPH_VERSION", "v23.0")
TOKEN = os.environ.get("IG_ACCESS_TOKEN", "").strip()
REPO = os.environ.get("GITHUB_REPOSITORY", "ferznandovvv/loucas-por-tutoriais")
RAW = f"https://raw.githubusercontent.com/{REPO}/midia/"
DRY = os.environ.get("DRY_RUN", "") == "1"
FORCAR = os.environ.get("FORCAR", "").strip()
BRT = timezone(timedelta(hours=-3))
MAX_SLIDES = 10


def api(method, path, **params):
    params["access_token"] = TOKEN
    r = requests.request(method, f"{API}/{path}", params=params, timeout=60)
    data = r.json() if r.headers.get("content-type", "").startswith("application/json") else {"raw": r.text}
    if r.status_code >= 400 or "error" in data:
        raise RuntimeError(f"{method} {path}: {data.get('error', data)}")
    return data


def user_id():
    uid = os.environ.get("IG_USER_ID", "").strip()
    if uid:
        return uid
    me = api("GET", "me", fields="user_id,username")
    print("conta:", me.get("username"), me.get("user_id"))
    return me["user_id"]


def wait_ready(container_id, tries=30):
    for _ in range(tries):
        st = api("GET", container_id, fields="status_code").get("status_code")
        if st == "FINISHED":
            return
        if st in ("ERROR", "EXPIRED"):
            raise RuntimeError(f"container {container_id} {st}")
        time.sleep(5)
    raise RuntimeError(f"container {container_id} nao ficou pronto")


def check_urls(urls):
    for u in urls:
        r = requests.head(u, timeout=30, allow_redirects=True)
        if r.status_code != 200:
            raise RuntimeError(f"imagem inacessivel ({r.status_code}): {u}")


def publish_carousel(uid, post):
    urls = [RAW + m for m in post["midia"]]
    if not 2 <= len(urls) <= MAX_SLIDES:
        raise RuntimeError(f"carrossel precisa ter de 2 a {MAX_SLIDES} imagens (tem {len(urls)})")
    check_urls(urls)
    if DRY:
        return {"dry_run": True, "imagens": len(urls)}
    children = []
    for u in urls:
        c = api("POST", f"{uid}/media", image_url=u, is_carousel_item="true")
        children.append(c["id"])
    for c in children:
        wait_ready(c)
    parent = api("POST", f"{uid}/media", media_type="CAROUSEL", children=",".join(children), caption=post.get("legenda", ""))
    wait_ready(parent["id"])
    pub = api("POST", f"{uid}/media_publish", creation_id=parent["id"])
    info = api("GET", pub["id"], fields="permalink,timestamp")
    return {"media_id": pub["id"], "link": info.get("permalink"), "em": info.get("timestamp")}


def main():
    if not TOKEN and not DRY:
        print("IG_ACCESS_TOKEN nao configurado ainda. Nada publicado.")
        return
    if os.path.exists("publicar/PAUSADO"):
        print("Publicacao pausada (existe publicar/PAUSADO). Nada publicado.")
        return
    now = datetime.now(BRT)
    uid = None
    changed = []
    for path in sorted(glob.glob("publicar/*.json")):
        fila = json.load(open(path, encoding="utf-8"))
        dirty = False
        for post in fila.get("posts", []):
            key = f"{os.path.basename(path)}:{post['id']}"
            if post.get("publicado") or not post.get("aprovado"):
                continue
            when = datetime.fromisoformat(post["horario"]).replace(tzinfo=BRT)
            if when > now and FORCAR != key:
                continue
            if post.get("tipo") != "carrossel":
                post["erro"] = f"tipo {post.get('tipo')} nao suportado (so carrossel por enquanto)"
                dirty = True
                continue
            print("publicando", key)
            try:
                if uid is None and not DRY:
                    uid = user_id()
                res = publish_carousel(uid, post)
                if DRY:
                    print("ok (simulacao)", res)
                    continue
                post["publicado"] = res
                post.pop("erro", None)
                print("publicado", res)
            except Exception as e:
                post["erro"] = f"{datetime.now(BRT):%Y-%m-%d %H:%M} {e}"
                print("ERRO", key, e)
            dirty = True
        if dirty and not DRY:
            json.dump(fila, open(path, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
            changed.append(path)
    print("arquivos alterados:", changed)


if __name__ == "__main__":
    main()
