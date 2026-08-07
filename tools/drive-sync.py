#!/usr/bin/env python3
"""
Sincroniza as galerias completas com as pastas do Google Drive.

As fotos são BAIXADAS para assets/galerias/<slug>/ em duas versões WebP:
full (1600px, lightbox) e thumb (700px, mosaico). O site não depende do CDN
do Google em tempo de visita. Só os vídeos continuam no Drive, embutidos
pelo player deles, então as pastas precisam seguir compartilhadas como
"qualquer pessoa com o link" para o sync funcionar e os vídeos tocarem.

O download é incremental: um _manifesto.json por álbum guarda qual id do
Drive gerou cada arquivo, então rodar de novo só busca o que mudou.

Uso:  python3 tools/drive-sync.py
Gera: assets/galerias/**, assets/cobertura/**, js/galerias-data.js,
      galeria/<slug>.html e sitemap.xml
"""

import html
import json
import re
import subprocess
import sys
import unicodedata
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent

# ── álbuns: slug → metadados + pasta do Drive ────────────────────────────────
ALBUNS = [
    {
        "slug": "casamento-rs",
        "titulo": "Casamento R&S",
        "tag": "Fotografia e cinema",
        "descricao": "A galeria completa do casamento R&S em fotografia e cinema.",
        "secao": "casamentos",
        "pasta": "1hdrdsNgBVLONDXd5ekdoEs9zQAky0O98",
        "limite": 50,    # a pasta tem 441; a galeria mostra 50 espalhadas pelo dia
        "video": {
            "youtube": "HGXlJedpLJ0",
            "poster": "/assets/casamento/cas-347.jpg",
            "kicker": "O filme",
            "titulo": "Cada casamento vira um curta-metragem.",
            "desc": "A emoção do dia inteiro editada em um filme. Aperte o play.",
        },
    },
    {
        "slug": "festa-menina",
        "titulo": "Festa Menina",
        "tag": "2 anos · fazendinha",
        "descricao": "A galeria completa da festa de 2 anos com tema fazendinha.",
        "secao": "eventos",
        "pasta": "1GzvdDRYi5_FK8spfgpNOBOYYhbNE3r5-",     # Aniversários/Menina
    },
    {
        "slug": "festa-menino",
        "titulo": "Festa Menino",
        "tag": "festa temática · cowboy",
        "descricao": "A galeria completa do aniversário com tema cowboy.",
        "secao": "eventos",
        "pasta": "1xltY1b3J0gYyMnE2WjpIU84T1Nli7spp",     # Aniversários/MENINO
    },
    {
        "slug": "50-anos",
        "titulo": "50 Anos",
        "tag": "festa country",
        "descricao": "A galeria completa da festa de 50 anos.",
        "secao": "eventos",
        "pasta": "15ZxHoRF5Zco8euPhFA0UJcsebwClJzn2",     # Aniversários/50
    },
]

# ── vídeos da seção "Cobertura de Eventos" ──────────────────────────────────
VIDEOS = [
    {"tag": "Stories",    "pasta": "1WrocipEpdMx_c1x_gIMaGAhdiY13-Ewh", "recursivo": False},
    {"tag": "Aftermovie", "pasta": "1UtTI_vtJ_KgUN9xUUesikYKFQc0p1CjI", "recursivo": True},
]

# Nome de arquivo do Drive vira título no site. Quando o nome interno não serve
# para o público, coloque o título aqui (id do arquivo → título).
TITULOS = {
    "1lT6iByyyU4I3swXOqr_C4xEn2Ovq4FI9": "Cobertura em tempo real",
    "1nf8DllgkyzA77R0Ht-_icTHIEXnQXw2A": "Nosso Sertão · Dia 2",
    "1_HQnBTbqvG7Uqa9OHzwZDA1fcj9YNFQH": "Arraiá do Vaqueiro",
    "1gOngPusctonXmINtlhpUbA2qUFhXxxn4": "Katlin · 100K",
    "1zxt2Ed_n5c7LIglm0AxMZ0OG9sX_3U9n": "São João",
    "1kdFbnry1sywdeepLtlIwjCuojzvNckHg": "Decoração São João 2026",
    "1cu5ZGkXLSZ_-1LRwo_UQavNrPqtx2pmR": "Nosso Sertão · Manim",
    "1uX62sZTJ__h_7PBMqFFRE3eRQd-yMCKK": "Nalvinho",
}


def _baixar(pasta_id):
    url = f"https://drive.google.com/embeddedfolderview?id={pasta_id}#list"
    return subprocess.run(["curl", "-sL", "--max-time", "90", url],
                          capture_output=True, text=True).stdout


def _subpastas(page):
    return re.findall(
        r'href="https://drive\.google\.com/drive/folders/([\w-]+)"'
        r'(?:(?!flip-entry-title).)*?flip-entry-title">([^<]+)</div>', page, re.S)


def listar_pasta(pasta_id, exts=r"jpe?g|png|webp", recursivo=False):
    """(id, nome) de cada arquivo de uma pasta pública, ordenado por nome."""
    page = _baixar(pasta_id)
    itens, vistos = [], set()
    for m in re.finditer(
        r'href="https://drive\.google\.com/file/d/([\w-]+)/view[^"]*"'
        r'(?:(?!flip-entry-title).)*?flip-entry-title">([^<]+)</div>', page, re.S
    ):
        fid, nome = m.group(1), html.unescape(m.group(2)).strip()
        if fid in vistos or not re.search(rf"\.({exts})$", nome, re.I):
            continue
        vistos.add(fid)
        itens.append((fid, nome))
    if recursivo:
        for sub, _ in _subpastas(page):
            itens += listar_pasta(sub, exts, recursivo=False)
    itens.sort(key=lambda x: x[1].lower())
    return itens


def amostrar(itens, limite):
    """Recorta a lista mantendo a ordem e espalhando pelo evento inteiro,
    em vez de pegar só as primeiras fotos (que são todas da preparação)."""
    if not limite or len(itens) <= limite:
        return itens
    passo = len(itens) / limite
    return [itens[int(i * passo)] for i in range(limite)]


def titulo_video(nome):
    """'AFTERMOVIE SJ V2.mov' → 'Aftermovie SJ V2'"""
    base = re.sub(r"\.[A-Za-z0-9]+$", "", nome).replace("_", " ").strip()
    base = re.sub(r"\s*-\s*", " · ", base)
    return " ".join(p if p.isupper() and len(p) <= 3 else p.capitalize()
                    for p in base.split())


def escapar(t):
    return (t.replace("&", "&amp;").replace("<", "&lt;")
             .replace(">", "&gt;").replace('"', "&quot;"))


# ── download e otimização ───────────────────────────────────────────────────
LARGURA_GRANDE = 1600     # usada no lightbox
LARGURA_THUMB = 700       # usada no mosaico
QUALIDADE = 82            # WebP: ~43% do peso do JPEG equivalente, sem perda visível


def baixar_imagem(fid, largura):
    """Baixa do CDN do Google já redimensionado. Sem Referer: o CDN aplica
    cota por site que referencia e devolve 429 quando estoura."""
    url = f"https://lh3.googleusercontent.com/d/{fid}=w{largura}"
    r = subprocess.run(["curl", "-sL", "--max-time", "120", url],
                       capture_output=True)
    dados = r.stdout
    if len(dados) < 2000 or not dados.startswith(b"\xff\xd8"):   # não é JPEG
        return None
    return dados


def gravar_par(dados, dir_full, dir_thumb, nome):
    """Grava a versão grande e gera a miniatura, ambas em WebP."""
    from PIL import Image
    import io

    im = Image.open(io.BytesIO(dados)).convert("RGB")
    im.save(dir_full / nome, "WEBP", quality=QUALIDADE, method=6)

    prop = LARGURA_THUMB / im.width
    if prop < 1:
        im = im.resize((LARGURA_THUMB, round(im.height * prop)), Image.LANCZOS)
    im.save(dir_thumb / nome, "WEBP", quality=QUALIDADE, method=6)


def sincronizar_fotos(slug, ids):
    """Baixa o que falta em assets/galerias/<slug>/. Idempotente: um manifesto
    guarda qual id do Drive gerou cada arquivo, então rodar de novo só busca o
    que mudou."""
    base = RAIZ / "assets" / "galerias" / slug
    dir_full, dir_thumb = base / "full", base / "thumb"
    dir_full.mkdir(parents=True, exist_ok=True)
    dir_thumb.mkdir(parents=True, exist_ok=True)
    manifesto_arq = base / "_manifesto.json"
    manifesto = {}
    if manifesto_arq.exists():
        manifesto = json.loads(manifesto_arq.read_text(encoding="utf-8"))

    nomes, novos, falhas = [], 0, []
    for i, fid in enumerate(ids, 1):
        nome = f"{i:03d}.webp"
        nomes.append(nome)
        ja_tem = (manifesto.get(nome) == fid
                  and (dir_full / nome).exists() and (dir_thumb / nome).exists())
        if ja_tem:
            continue
        dados = baixar_imagem(fid, LARGURA_GRANDE)
        if not dados:
            falhas.append(fid)
            continue
        gravar_par(dados, dir_full, dir_thumb, nome)
        manifesto[nome] = fid
        novos += 1

    # limpa sobras de quando o álbum tinha mais fotos
    for arq in list(dir_full.iterdir()) + list(dir_thumb.iterdir()):
        if arq.name not in nomes:
            arq.unlink()
            manifesto.pop(arq.name, None)
    manifesto_arq.write_text(json.dumps(manifesto, indent=2), encoding="utf-8")
    return nomes, novos, falhas


def sincronizar_posters(videos):
    """Pôster de cada vídeo em assets/cobertura/. O vídeo em si continua no
    Drive; só a imagem de capa vem para cá."""
    base = RAIZ / "assets" / "cobertura"
    base.mkdir(parents=True, exist_ok=True)
    novos, falhas = 0, []
    for v in videos:
        destino = base / f"{v['id']}.webp"
        v["poster"] = f"/assets/cobertura/{v['id']}.webp"
        if destino.exists():
            continue
        dados = baixar_imagem(v["id"], 900)
        if not dados:
            falhas.append(v["id"])
            continue
        from PIL import Image
        import io
        Image.open(io.BytesIO(dados)).convert("RGB").save(
            destino, "WEBP", quality=QUALIDADE, method=6)
        novos += 1
    return novos, falhas


def bloco_filme(alb):
    """Banda do filme, quando o álbum tem vídeo. Abre no lightbox de vídeo."""
    v = alb.get("video")
    if not v:
        return ""
    return f"""
  <div class="galfilme" data-yt="{v['youtube']}">
    <div class="galfilme__poster">
      <img src="{v['poster']}" alt="{escapar(v['titulo'])}, filmora" loading="lazy">
      <span class="galfilme__play" aria-hidden="true">
        <svg width="24" height="24" viewBox="0 0 24 24" fill="currentColor"><path d="M8 5v14l11-7z"/></svg>
      </span>
    </div>
    <div class="galfilme__body">
      <span class="cat__kicker">{escapar(v['kicker'])}</span>
      <h2 class="galfilme__title">{escapar(v['titulo'])}</h2>
      <p class="galfilme__desc">{escapar(v['desc'])}</p>
      <button class="btn btn--solid" type="button">Assistir ao filme</button>
    </div>
  </div>
"""


def bloco_vlb(alb):
    return "" if not alb.get("video") else """
<div class="vlb" id="vlb" aria-hidden="true">
  <button class="vlb__close" id="vlbClose" aria-label="fechar vídeo">×</button>
  <div class="vlb__frame" id="vlbFrame"></div>
</div>
"""


def pagina(alb):
    """HTML estático de uma página de galeria."""
    titulo = escapar(alb["titulo"])
    desc = escapar(alb["descricao"])
    return f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{titulo}: Galeria completa | filmora</title>
<meta name="description" content="{desc}">
<meta name="theme-color" content="#f7f4ef">
<link rel="icon" href="/assets/logo.jpg">
<meta property="og:title" content="{titulo}: Galeria completa | filmora">
<meta property="og:description" content="{desc}">
<meta property="og:type" content="article">
<meta property="og:locale" content="pt_BR">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Bodoni+Moda:ital,opsz,wght@0,6..96,400;0,6..96,500;0,6..96,600;1,6..96,400;1,6..96,500&family=Prata&family=Jost:wght@300;400;500&display=swap" rel="stylesheet">
<link rel="stylesheet" href="/css/styles.css">
<script>
  (function(){{
    var t = 'light';
    try{{ t = localStorage.getItem('filmora-theme') || 'light'; }}catch(e){{}}
    document.documentElement.setAttribute('data-theme', t);
  }})();
</script>
</head>
<body class="page-galeria">

<header class="nav" id="nav">
  <a href="/" class="nav__brand" aria-label="filmora, início">
    <img class="nav__logo" src="/assets/logo-ink.png" alt="filmora">
  </a>
  <nav class="nav__links">
    <a href="/#servicos">Serviços</a>
    <a href="/#sobre">Sobre</a>
    <a href="/#contato">Contato</a>
  </nav>
  <div class="nav__actions">
    <button class="theme" id="themeToggle" aria-label="alternar tema claro e escuro">
      <svg class="theme__sun" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><circle cx="12" cy="12" r="4.5"/><path d="M12 2v2.5M12 19.5V22M4.2 4.2l1.8 1.8M18 18l1.8 1.8M2 12h2.5M19.5 12H22M4.2 19.8L6 18M18 6l1.8-1.8"/></svg>
      <svg class="theme__moon" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><path d="M21 12.8A8.5 8.5 0 1 1 11.2 3a6.5 6.5 0 0 0 9.8 9.8Z"/></svg>
    </button>
    <a href="/#contato" class="nav__cta">Orçamento</a>
  </div>
  <button class="nav__burger" id="burger" aria-label="menu"><span></span><span></span></button>
</header>

<main class="gal" data-album="{alb['slug']}">
  <div class="gal__head">
    <a class="gal__back" href="/#{alb['secao']}"><span>←</span> Voltar ao portfólio</a>
    <span class="cat__kicker">{escapar(alb['tag'])}</span>
    <h1 class="gal__title">{titulo}</h1>
    <p class="gal__desc">{desc}</p>
    <span class="gal__count" id="galCount"></span>
  </div>
{bloco_filme(alb)}
  <div class="gal__grid" id="galGrid"></div>

  <div class="gal__more">
    <button class="btn btn--ghost" id="galMore" hidden>Carregar mais fotos</button>
  </div>

  <div class="gal__cta">
    <p>Gostou do que viu?</p>
    <a class="btn btn--solid" href="https://wa.me/5575997083386?text=Ol%C3%A1%20filmora!%20Gostaria%20de%20um%20or%C3%A7amento." target="_blank" rel="noopener">Solicitar orçamento</a>
  </div>
</main>

<footer class="footer">
  <img class="footer__logo" src="/assets/logo-ink.png" alt="filmora">
  <p class="footer__tag">Fotografia &amp; Filmes para as histórias que merecem ficar.</p>
  <p class="footer__copy">© 2026 filmora · Agência de Produção Audiovisual</p>
  <a class="byline" href="https://infusesoftware.com/" target="_blank" rel="noopener">
    Desenvolvido por
    <span class="byline__logo">
      <img class="byline__symbol" src="/assets/infuse/infuse-symbol-white.webp" alt="" aria-hidden="true">
      <img class="byline__word" src="/assets/infuse/infuse-word-white.webp" alt="Infuse Software">
    </span>
  </a>
</footer>

<div class="lb" id="lb" aria-hidden="true">
  <button class="lb__close" id="lbClose" aria-label="fechar">×</button>
  <button class="lb__nav lb__prev" id="lbPrev" aria-label="anterior">‹</button>
  <button class="lb__nav lb__next" id="lbNext" aria-label="próximo">›</button>
  <span class="lb__count" id="lbCount"></span>
  <figure class="lb__stage"><img id="lbImg" src="" alt=""></figure>
</div>
{bloco_vlb(alb)}
<script src="/js/galerias-data.js"></script>
<script src="/js/galeria.js"></script>
</body>
</html>
"""


def main():
    dados = {}
    for alb in ALBUNS:
        if not alb["pasta"]:
            print(f"  · {alb['slug']}: sem pasta do Drive, pulando", file=sys.stderr)
            continue
        todas = listar_pasta(alb["pasta"])
        if not todas:
            print(f"  ! {alb['slug']}: nenhuma foto encontrada; a pasta está pública?",
                  file=sys.stderr)
            continue
        itens = amostrar(todas, alb.get("limite"))
        nomes, novos, falhas = sincronizar_fotos(alb["slug"], [fid for fid, _ in itens])
        dados[alb["slug"]] = {
            "titulo": alb["titulo"],
            "tag": alb["tag"],
            "pasta": alb["pasta"],
            "dir": f"/assets/galerias/{alb['slug']}",
            "fotos": nomes,
        }
        corte = f" (de {len(todas)})" if len(itens) < len(todas) else ""
        extra = f" · {novos} baixadas" if novos else " · nada novo"
        if falhas:
            extra += f" · {len(falhas)} FALHARAM"
        print(f"  · {alb['slug']}: {len(nomes)} fotos{corte}{extra}", file=sys.stderr)

        destino = RAIZ / "galeria" / f"{alb['slug']}.html"
        destino.parent.mkdir(exist_ok=True)
        destino.write_text(pagina(alb), encoding="utf-8")

    urls = "".join(
        f"\n  <url><loc>/galeria/{s}</loc><changefreq>monthly</changefreq><priority>0.7</priority></url>"
        for s in dados
    )
    (RAIZ / "sitemap.xml").write_text(
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        '  <url><loc>/</loc><changefreq>monthly</changefreq><priority>1.0</priority></url>'
        f"{urls}\n</urlset>\n",
        encoding="utf-8",
    )

    videos = []
    for grupo in VIDEOS:
        itens = listar_pasta(grupo["pasta"], exts=r"mp4|mov|m4v|webm",
                             recursivo=grupo["recursivo"])
        for fid, nome in itens:
            videos.append({"id": fid,
                           "titulo": TITULOS.get(fid) or titulo_video(nome),
                           "tag": grupo["tag"]})
        print(f"  · vídeos {grupo['tag']}: {len(itens)}", file=sys.stderr)

    pn, pf = sincronizar_posters(videos)
    print(f"  · pôsteres de vídeo: {pn} baixados" +
          (f" · {len(pf)} FALHARAM" if pf else ""), file=sys.stderr)

    saida = RAIZ / "js" / "galerias-data.js"
    saida.write_text(
        "/* GERADO por tools/drive-sync.py: não edite à mão. */\n"
        "window.GALERIAS = " + json.dumps(dados, ensure_ascii=False, indent=2) + ";\n"
        "window.COBERTURA = " + json.dumps(videos, ensure_ascii=False, indent=2) + ";\n",
        encoding="utf-8",
    )
    total = sum(len(v["fotos"]) for v in dados.values())
    print(f"→ {saida.relative_to(RAIZ)} · {len(dados)} álbuns · {total} fotos", file=sys.stderr)


if __name__ == "__main__":
    main()
