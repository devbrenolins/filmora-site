#!/usr/bin/env python3
"""
Sincroniza as galerias completas com as pastas do Google Drive.

As fotos são BAIXADAS para assets/galerias/<slug>/ em duas versões WebP:
full (1600px, lightbox) e thumb (700px, mosaico). O site não depende do CDN
do Google em tempo de visita. Os vídeos tocam do YouTube (mapa YOUTUBE); os
que não estão lá o site serve convertidos pelo tools/video-sync.py, e só na
falta dos dois o player do Drive entra. As pastas precisam seguir
compartilhadas como "qualquer pessoa com o link" para o sync funcionar.

O download é incremental: um _manifesto.json por álbum guarda qual id do
Drive gerou cada arquivo, então rodar de novo só busca o que mudou.

Uso:  python3 tools/drive-sync.py
Gera: assets/galerias/**, assets/cobertura/**, assets/conteudo/**,
      js/galerias-data.js, galeria/<slug>.html, galeria/producao-conteudo.html
      e sitemap.xml
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
        "destaque": "assets/casamento/cas-347.jpg",   # abre a galeria em largura cheia
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
    {
        "slug": "making-of-noiva",
        "titulo": "Making Of da Noiva",
        "tag": "as horas antes do sim",
        "descricao": "A galeria completa do making of da noiva: dos preparativos ao altar.",
        "secao": "making-of",
        "pasta": "18cjMX4fwuu6FfAGGeu_19PSSrrxK4f64",
        "limite": 70,    # a pasta tem 220; a galeria mostra 70 espalhadas pelo dia
    },
    {
        "slug": "cerimonia-jaleco",
        "titulo": "Cerimônia do Jaleco",
        "tag": "formatura · vida acadêmica",
        "descricao": "A galeria completa da cerimônia do jaleco, do retrato de estúdio ao abraço da família.",
        "secao": "jaleco",
        "pasta": "1VKJrDpY6ryuiIP5FM4ROiNii3S1bd-H9",
        "limite": 60,    # a pasta tem 91
    },
]

# ── vídeos da seção "Cobertura de Eventos" ──────────────────────────────────
VIDEOS = [
    {"tag": "Stories",    "pasta": "1WrocipEpdMx_c1x_gIMaGAhdiY13-Ewh", "recursivo": False},
    {"tag": "Aftermovie", "pasta": "1UtTI_vtJ_KgUN9xUUesikYKFQc0p1CjI", "recursivo": True},
]

# ── produção de conteúdo para gerenciamento de perfil ───────────────────────
# O entregável desse serviço é o feed do cliente, então aqui entra só o que é
# vertical: as pastas têm as mesmas peças em corte horizontal (YouTube), que
# ficariam deslocadas numa seção sobre Instagram.
# Cada pasta é o lote de um perfil. `perfil` não muda a ordem daqui — a página
# do serviço mostra lote por lote —, mas a home usa o campo para equilibrar as
# poucas peças que cabem na vitrine entre as duas criadoras.
VERTICAIS = [
    {"tag": "Reels", "perfil": "perfil-1", "pasta": "1dEFngtdFq9p15WuUDsV2hIaMmqNnZD49"},   # .../Vídeos/Verticais (rede social)
    {"tag": "Reels", "perfil": "perfil-2", "pasta": "1Ibac3A-iUQUwvzKvYt5xtCYmUxnR-yCt"},   # .../Vídeos Verticais (Instagram)
]

# peças que abrem a seção, na ordem
DESTAQUES = [
    "1yXNzjfwH9d5rTkdtCz-gBuxxSgvjNfCE",   # Quanto o Senhor tem de nós
    "1zI72lTOpJvnCZVoRfCG9g3mD2Iw2iohg",   # Se você fosse viajar
]

# retrato da cliente que ilustra o serviço no índice e na abertura da seção
CAPA_CONTEUDO = "1A0f5C58WOqGzMswuTpmGOTygLxlmauJj"

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
    # verticais da produção de conteúdo: o nome do arquivo vira Caixa Alta Em
    # Toda Palavra no titulo_video(), e estes títulos são frases.
    "1yXNzjfwH9d5rTkdtCz-gBuxxSgvjNfCE": "Quanto o Senhor tem de nós",
    "1zI72lTOpJvnCZVoRfCG9g3mD2Iw2iohg": "Se você fosse viajar",
    "1R1GhuzJSN8VuIxyDY2aLJUHKDeh8ciW2": "Espírito de sabedoria e revelação",
    "1rJLW3Gcp2BTI4wpvQfg2XyTOI0GQawLg": "Pois ele é a nossa paz",
    "1iFGRlffppviNpA4rqCNDJSwG8AupC6az": "Se a gente faz tudo da mesma forma",
    "1UMzp7J--x0jTUsnKQHXPSTAYWsVczPE4": "Se você ganhasse hoje na mega-sena",
    "1TjgyUSaejkWH9mFAwGBbFwq3hD6qxsyq": "A presença ou a promessa",
    "104GDVCQdzovM7D534AfUHxEFa4T4mI6s": "Casa na rocha ou na areia",
    "1heRVdlmtIJ7VCf9ag4ajM2ZE3R0zhTzJ": "Milagres",
    "1BPKEpXdbLSq2j6vA2bRi9i1kfou9tqoX": "Salmos",
    "1kRt86EVuJQasTUflWEGGBY68gqWIojNX": "Confiança no Senhor",
}

# Os vídeos tocam do YouTube. O Drive segue como origem do pôster e do título;
# quem não está aqui o site serve do próprio arquivo (tools/video-sync.py).
# id do arquivo no Drive → id do vídeo no YouTube
YOUTUBE = {
    "1lT6iByyyU4I3swXOqr_C4xEn2Ovq4FI9": "ZOY_VQRFgBE",   # 01 Cobertura em tempo real
    "1nf8DllgkyzA77R0Ht-_icTHIEXnQXw2A": "WJq5e_phYuw",   # 02 Nosso Sertão · Dia 2
    "1_HQnBTbqvG7Uqa9OHzwZDA1fcj9YNFQH": "5HRBbv9nU9c",   # 03 Arraiá do Vaqueiro
    "1yXNzjfwH9d5rTkdtCz-gBuxxSgvjNfCE": "8eFlNir1_yE",   # 09 Quanto o Senhor tem de nós
    "1zI72lTOpJvnCZVoRfCG9g3mD2Iw2iohg": "IpBZ7J7rvvA",   # 10 Se você fosse viajar
    "1R1GhuzJSN8VuIxyDY2aLJUHKDeh8ciW2": "vJtkq10s4Mg",   # 11 Espírito de sabedoria e revelação
    "1rJLW3Gcp2BTI4wpvQfg2XyTOI0GQawLg": "AauWakzIHPE",   # 12 Pois ele é a nossa paz
    "1UMzp7J--x0jTUsnKQHXPSTAYWsVczPE4": "MV9LSdG66NU",   # 14 Se você ganhasse hoje na mega-sena
    "1TjgyUSaejkWH9mFAwGBbFwq3hD6qxsyq": "KC5ZLjCD3_E",   # 15 A presença ou a promessa
    "104GDVCQdzovM7D534AfUHxEFa4T4mI6s": "iav54jgJCF8",   # 16 Casa na rocha ou na areia
    "1heRVdlmtIJ7VCf9ag4ajM2ZE3R0zhTzJ": "cz2yMEZPVNc",   # 17 Milagres
    "1BPKEpXdbLSq2j6vA2bRi9i1kfou9tqoX": "JzGF5ON0pTE",   # 18 Salmos
    "1kRt86EVuJQasTUflWEGGBY68gqWIojNX": "qjNuQplWKds",   # 19 Confiança no Senhor
    # Servidos pelo site: 05 São João (1zxt2Ed_…) e 13 Se a gente faz tudo da
    # mesma forma (1iFGRlff…), sem link no YouTube, e os 4 abaixo, que estão
    # no YouTube mas o player embutido responde "Este vídeo não está
    # disponível". Descomente quando voltarem a tocar (e rode o video-sync.py
    # de novo: ele apaga o mp4 que deixou de ser usado).
    # "1gOngPusctonXmINtlhpUbA2qUFhXxxn4": "MUk52JTRafM",   # 04 Katlin · 100K
    # "1kdFbnry1sywdeepLtlIwjCuojzvNckHg": "JXIy0cSNSfQ",   # 06 Decoração São João 2026
    # "1cu5ZGkXLSZ_-1LRwo_UQavNrPqtx2pmR": "JYo2bwPTcac",   # 07 Nosso Sertão · Manim
    # "1uX62sZTJ__h_7PBMqFFRE3eRQd-yMCKK": "7z0X1sX7WdA",   # 08 Nalvinho
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


def versao_assets():
    """Hash curto de CSS+JS. Vira ?v=<hash> nos links das páginas geradas, para
    o navegador não servir versão velha de cache depois de um deploy."""
    import hashlib
    h = hashlib.sha1()
    for rel in ("css/styles.css", "js/galeria.js", "js/conteudo.js", "js/galerias-data.js"):
        arq = RAIZ / rel
        if arq.exists():
            h.update(arq.read_bytes())
    return h.hexdigest()[:8]


def escapar(t):
    return (t.replace("&", "&amp;").replace("<", "&lt;")
             .replace(">", "&gt;").replace('"', "&quot;"))


# ── chrome compartilhado pelas páginas geradas ──────────────────────────────
NAV = """<header class="nav" id="nav">
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
</header>"""

RODAPE = """<footer class="footer">
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
</footer>"""


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
    """Grava a versão grande e gera a miniatura, ambas em WebP.
    Devolve (largura, altura) da miniatura: o site precisa disso para
    reservar o espaço de cada foto antes dela carregar."""
    from PIL import Image
    import io

    im = Image.open(io.BytesIO(dados)).convert("RGB")
    if im.width > LARGURA_GRANDE:
        im = im.resize((LARGURA_GRANDE, round(im.height * LARGURA_GRANDE / im.width)),
                       Image.LANCZOS)
    im.save(dir_full / nome, "WEBP", quality=QUALIDADE, method=6)

    prop = LARGURA_THUMB / im.width
    if prop < 1:
        im = im.resize((LARGURA_THUMB, round(im.height * prop)), Image.LANCZOS)
    im.save(dir_thumb / nome, "WEBP", quality=QUALIDADE, method=6)
    return im.width, im.height


def medir(caminho):
    from PIL import Image
    with Image.open(caminho) as im:
        return im.width, im.height


def sincronizar_fotos(slug, ids, destaque=None):
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

    # 000 é a foto de destaque: arquivo local, não vem do Drive
    if destaque:
        origem = RAIZ / destaque
        nome = "000.webp"
        if origem.exists():
            if not ((dir_full / nome).exists() and (dir_thumb / nome).exists()
                    and manifesto.get(nome) == destaque):
                w, h = gravar_par(origem.read_bytes(), dir_full, dir_thumb, nome)
                manifesto[nome] = destaque
                novos += 1
            else:
                w, h = medir(dir_thumb / nome)
            nomes.append([nome, w, h])
        else:
            print(f"  ! destaque não encontrado: {destaque}", file=sys.stderr)

    for i, fid in enumerate(ids, 1):
        nome = f"{i:03d}.webp"
        ja_tem = (manifesto.get(nome) == fid
                  and (dir_full / nome).exists() and (dir_thumb / nome).exists())
        if ja_tem:
            nomes.append([nome, *medir(dir_thumb / nome)])
            continue
        dados = baixar_imagem(fid, LARGURA_GRANDE)
        if not dados:
            falhas.append(fid)
            continue
        w, h = gravar_par(dados, dir_full, dir_thumb, nome)
        nomes.append([nome, w, h])
        manifesto[nome] = fid
        novos += 1

    # limpa sobras de quando o álbum tinha mais fotos
    validos = {n[0] for n in nomes}
    for arq in list(dir_full.iterdir()) + list(dir_thumb.iterdir()):
        if arq.name not in validos:
            arq.unlink()
            manifesto.pop(arq.name, None)
    manifesto_arq.write_text(json.dumps(manifesto, indent=2), encoding="utf-8")
    return nomes, novos, falhas


def sincronizar_posters(videos, pasta="cobertura"):
    """Pôster de cada vídeo em assets/<pasta>/. O vídeo em si vem de outro
    lugar (YouTube, video-sync.py ou Drive); aqui só a imagem de capa."""
    base = RAIZ / "assets" / pasta
    base.mkdir(parents=True, exist_ok=True)
    novos, falhas = 0, []
    for v in videos:
        destino = base / f"{v['id']}.webp"
        v["poster"] = f"/assets/{pasta}/{v['id']}.webp"
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


def arquivos_locais(videos, pasta):
    """Vídeo sem YouTube que o tools/video-sync.py já converteu é servido pelo
    próprio site: o campo `video` aponta para o mp4. Quem não tem nenhum dos
    dois ainda toca do Drive."""
    base = RAIZ / "assets" / pasta / "video"
    for v in videos:
        if not v.get("youtube") and (base / f"{v['id']}.mp4").exists():
            v["video"] = f"/assets/{pasta}/video/{v['id']}.mp4"


def sincronizar_capa(fid, destino_rel, largura=1200):
    """Baixa uma foto avulsa do Drive para servir de capa de seção."""
    destino = RAIZ / destino_rel
    destino.parent.mkdir(parents=True, exist_ok=True)
    if destino.exists():
        return False
    dados = baixar_imagem(fid, largura)
    if not dados:
        print(f"  ! capa {destino_rel}: download falhou", file=sys.stderr)
        return False
    from PIL import Image
    import io
    Image.open(io.BytesIO(dados)).convert("RGB").save(
        destino, "WEBP", quality=QUALIDADE, method=6)
    return True


def pagina(alb, VERSAO):
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
<link rel="stylesheet" href="/css/styles.css?v={VERSAO}">
<script>
  (function(){{
    var t = 'light';
    try{{ t = localStorage.getItem('filmora-theme') || 'light'; }}catch(e){{}}
    document.documentElement.setAttribute('data-theme', t);
  }})();
</script>
</head>
<body class="page-galeria">

{NAV}

<main class="gal" data-album="{alb['slug']}">
  <div class="gal__head">
    <a class="gal__back" href="/#{alb['secao']}"><span>←</span> Voltar ao portfólio</a>
    <span class="cat__kicker">{escapar(alb['tag'])}</span>
    <h1 class="gal__title">{titulo}</h1>
    <p class="gal__desc">{desc}</p>
    <span class="gal__count" id="galCount"></span>
  </div>
  <div class="gal__grid" id="galGrid"></div>

  <div class="gal__more">
    <button class="btn btn--ghost" id="galMore" hidden>Carregar mais fotos</button>
  </div>

  <div class="gal__cta">
    <p>Gostou do que viu?</p>
    <a class="btn btn--solid" href="https://wa.me/5575997083386?text=Ol%C3%A1%20filmora!%20Gostaria%20de%20um%20or%C3%A7amento." target="_blank" rel="noopener">Solicitar orçamento</a>
  </div>
</main>

{RODAPE}

<div class="lb" id="lb" aria-hidden="true">
  <button class="lb__close" id="lbClose" aria-label="fechar">×</button>
  <button class="lb__nav lb__prev" id="lbPrev" aria-label="anterior">‹</button>
  <button class="lb__nav lb__next" id="lbNext" aria-label="próximo">›</button>
  <span class="lb__count" id="lbCount"></span>
  <figure class="lb__stage"><img id="lbImg" src="" alt=""></figure>
</div>
<script src="/js/galerias-data.js?v={VERSAO}"></script>
<script src="/js/galeria.js?v={VERSAO}"></script>
</body>
</html>
"""


def pagina_conteudo(VERSAO):
    """Página do serviço de produção de conteúdo (gerenciamento de perfil).
    Não usa o mosaico de fotos: o entregável aqui é vídeo vertical, então a
    página monta os cards a partir de window.CONTEUDO e toca no player do YouTube."""
    desc = ("Produção de conteúdo vertical para gerenciamento de perfil no Instagram: "
            "roteiro, captação, edição e entrega mensal de reels.")
    return f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Produção de Conteúdo para Instagram | filmora</title>
<meta name="description" content="{desc}">
<meta name="theme-color" content="#f7f4ef">
<link rel="icon" href="/assets/logo.jpg">
<meta property="og:title" content="Produção de Conteúdo para Instagram | filmora">
<meta property="og:description" content="{desc}">
<meta property="og:type" content="article">
<meta property="og:locale" content="pt_BR">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Bodoni+Moda:ital,opsz,wght@0,6..96,400;0,6..96,500;0,6..96,600;1,6..96,400;1,6..96,500&family=Prata&family=Jost:wght@300;400;500&display=swap" rel="stylesheet">
<link rel="stylesheet" href="/css/styles.css?v={VERSAO}">
<script>
  (function(){{
    var t = 'light';
    try{{ t = localStorage.getItem('filmora-theme') || 'light'; }}catch(e){{}}
    document.documentElement.setAttribute('data-theme', t);
  }})();
</script>
</head>
<body class="page-galeria">

{NAV}

<main class="gal">
  <div class="gal__head">
    <a class="gal__back" href="/#conteudo"><span>←</span> Voltar ao portfólio</a>
    <span class="cat__kicker">Gerenciamento de perfil</span>
    <h1 class="gal__title">Produção de Conteúdo</h1>
    <p class="gal__desc">Um perfil vivo não se sustenta em post avulso. Cuidamos do ciclo inteiro:
    roteiro, captação, edição, legenda e entrega. Tudo em formato vertical, pensado para
    o feed e os reels do Instagram.</p>
    <span class="gal__count" id="conteudoCount"></span>
  </div>

  <section class="conteudo__bloco">
    <h2 class="conteudo__rotulo">Em destaque</h2>
    <div class="vids vids--vert vids--destaque" id="conteudoDestaques"></div>
  </section>

  <section class="conteudo__bloco">
    <h2 class="conteudo__rotulo">Outras peças</h2>
    <div class="vids vids--vert" id="conteudoGrid"></div>
  </section>

  <section class="fluxo">
    <article><span class="fluxo__num">01</span><h3>Roteiro</h3>
      <p>Pauta e roteiro alinhados à voz do perfil, com o gancho já pensado para os primeiros segundos.</p></article>
    <article><span class="fluxo__num">02</span><h3>Captação</h3>
      <p>Luz, áudio e direção de cena. A gravação é conduzida para o material não parecer improviso.</p></article>
    <article><span class="fluxo__num">03</span><h3>Edição &amp; entrega</h3>
      <p>Corte vertical, legenda queimada e trilha. Sai pronto para publicar, no calendário combinado.</p></article>
  </section>

  <div class="gal__cta">
    <p>Quer esse ritmo no seu perfil?</p>
    <a class="btn btn--solid" href="https://wa.me/5575997083386?text=Ol%C3%A1%20filmora!%20Quero%20produ%C3%A7%C3%A3o%20de%20conte%C3%BAdo%20para%20o%20meu%20perfil." target="_blank" rel="noopener">Solicitar orçamento</a>
  </div>
</main>

{RODAPE}

<div class="vlb" id="vlb" aria-hidden="true">
  <button class="vlb__close" id="vlbClose" aria-label="fechar vídeo">×</button>
  <div class="vlb__frame vlb__frame--vert" id="vlbFrame"></div>
</div>
<script src="/js/galerias-data.js?v={VERSAO}"></script>
<script src="/js/conteudo.js?v={VERSAO}"></script>
</body>
</html>
"""


def main():
    dados = {}
    paginas_pendentes = []
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
        nomes, novos, falhas = sincronizar_fotos(
            alb["slug"], [fid for fid, _ in itens], alb.get("destaque"))
        dados[alb["slug"]] = {
            "titulo": alb["titulo"],
            "tag": alb["tag"],
            "pasta": alb["pasta"],
            "dir": f"/assets/galerias/{alb['slug']}",
            "destaque": bool(alb.get("destaque")),
            "fotos": nomes,
        }
        corte = f" (de {len(todas)})" if len(itens) < len(todas) else ""
        extra = f" · {novos} baixadas" if novos else " · nada novo"
        if falhas:
            extra += f" · {len(falhas)} FALHARAM"
        print(f"  · {alb['slug']}: {len(nomes)} fotos{corte}{extra}", file=sys.stderr)

        destino = RAIZ / "galeria" / f"{alb['slug']}.html"
        destino.parent.mkdir(exist_ok=True)
        paginas_pendentes.append((destino, alb))

    urls = "".join(
        f"\n  <url><loc>/galeria/{s}</loc><changefreq>monthly</changefreq><priority>0.7</priority></url>"
        for s in list(dados) + ["producao-conteudo"]
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
                           "tag": grupo["tag"],
                           "youtube": YOUTUBE.get(fid)})
        print(f"  · vídeos {grupo['tag']}: {len(itens)}", file=sys.stderr)

    pn, pf = sincronizar_posters(videos)
    print(f"  · pôsteres de vídeo: {pn} baixados" +
          (f" · {len(pf)} FALHARAM" if pf else ""), file=sys.stderr)
    # a cobertura mistura aftermovie deitado com stories em pé: o pôster diz
    # qual é qual, e o player abre na moldura certa
    for v2 in videos:
        poster = RAIZ / v2["poster"].lstrip("/")
        if poster.exists():
            w, h = medir(poster)
            v2["vertical"] = h > w
    arquivos_locais(videos, "cobertura")

    # produção de conteúdo: só as peças verticais, com os destaques na frente
    conteudo = []
    for grupo in VERTICAIS:
        itens = listar_pasta(grupo["pasta"], exts=r"mp4|mov|m4v|webm")
        for fid, nome in itens:
            conteudo.append({"id": fid,
                             "titulo": TITULOS.get(fid) or titulo_video(nome),
                             "tag": grupo["tag"],
                             "youtube": YOUTUBE.get(fid),
                             "perfil": grupo["perfil"],
                             "destaque": fid in DESTAQUES})
        print(f"  · verticais {grupo['perfil']}: {len(itens)}", file=sys.stderr)
    # destaques na frente; o resto segue a ordem das pastas, um lote por perfil
    ordem = {fid: i for i, fid in enumerate(DESTAQUES)}
    conteudo.sort(key=lambda v2: ordem.get(v2["id"], len(DESTAQUES)))
    faltando = [d for d in DESTAQUES if d not in {v2["id"] for v2 in conteudo}]
    if faltando:
        print(f"  ! destaque(s) fora das pastas verticais: {faltando}", file=sys.stderr)

    cn, cf = sincronizar_posters(conteudo, pasta="conteudo")
    print(f"  · pôsteres de conteúdo: {cn} baixados" +
          (f" · {len(cf)} FALHARAM" if cf else ""), file=sys.stderr)
    arquivos_locais(conteudo, "conteudo")
    if sincronizar_capa(CAPA_CONTEUDO, "assets/conteudo/capa.webp"):
        print("  · capa da seção de conteúdo baixada", file=sys.stderr)

    saida = RAIZ / "js" / "galerias-data.js"
    saida.write_text(
        "/* GERADO por tools/drive-sync.py: não edite à mão. */\n"
        "window.GALERIAS = " + json.dumps(dados, ensure_ascii=False, indent=2) + ";\n"
        "window.COBERTURA = " + json.dumps(videos, ensure_ascii=False, indent=2) + ";\n"
        "window.CONTEUDO = " + json.dumps(conteudo, ensure_ascii=False, indent=2) + ";\n",
        encoding="utf-8",
    )
    v = versao_assets()
    for destino, alb in paginas_pendentes:
        destino.parent.mkdir(exist_ok=True)
        destino.write_text(pagina(alb, v), encoding="utf-8")
    (RAIZ / "galeria" / "producao-conteudo.html").write_text(
        pagina_conteudo(v), encoding="utf-8")

    total = sum(len(v2["fotos"]) for v2 in dados.values())
    print(f"→ {saida.relative_to(RAIZ)} · {len(dados)} álbuns · {total} fotos", file=sys.stderr)


if __name__ == "__main__":
    main()
