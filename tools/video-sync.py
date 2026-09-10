#!/usr/bin/env python3
"""
Baixa os vídeos do Drive e os converte para arquivos que o site pode servir.

Só entram os vídeos sem YouTube (campo `youtube` do galerias-data.js): esses
tocam de lá. O resto o site serve daqui, para não depender do Drive.

Os originais são masters de edição (o maior tem quase 1 GB); o que vai para o
repositório é uma versão H.264 em 720p, ~20–30 MB por minuto. O master baixado
fica num cache fora do projeto.

Depois de rodar, o drive-sync.py preenche o campo `video` de cada peça que
ganhou arquivo aqui.

O trabalho é incremental: um _manifesto.json por pasta guarda qual id do Drive
gerou cada arquivo e com que ajuste, então rodar de novo só refaz o que mudou.

Uso:  python3 tools/video-sync.py [--cobertura] [--conteudo] [--manter-master]
Gera: assets/conteudo/video/**, assets/cobertura/video/**
"""

import argparse
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
CACHE = Path("/tmp/filmora-video-cache")

# O arquivo vai para o GitHub (limite de 100 MB por arquivo) e é baixado por
# visitante no celular. Medido num aftermovie: CRF 18 em 1080p dá ~15 Mbps
# (1 min passa de 100 MB); CRF 23 em 720p dá ~4 Mbps (1 min ≈ 30 MB).
# Preset slow gasta mais CPU e devolve o arquivo menor no mesmo CRF.
CRF = 23
PRESET = "slow"
AUDIO_KBPS = 128
# O x264 abre ~1,5 thread por núcleo e cada uma segura seus quadros; num host
# apertado de memória isso é o que faz o processo morrer no meio da conversão.
# Não mexe na qualidade: com CRF o alvo é a qualidade, não a taxa.
THREADS = 3
# 720p: o player do site ocupa no máximo 1100px de largura (ou 78vh de altura
# no vertical), e 1080p dobraria o peso para um ganho pequeno nesse tamanho.
LADO_MAIOR = 1280


def videos_gerados():
    """Lê js/galerias-data.js, que o drive-sync já deixou com as listas boas.
    Vídeo com YouTube fica de fora: o site toca de lá."""
    js = (RAIZ / "js" / "galerias-data.js").read_text(encoding="utf-8")
    def lista(nome, fim):
        m = re.search(rf"window\.{nome} = (\[.*?\]);\n{fim}", js, re.S)
        return [v for v in json.loads(m.group(1)) if not v.get("youtube")] if m else []
    return {
        "cobertura": lista("COBERTURA", r"window\.CONTEUDO"),
        "conteudo": lista("CONTEUDO", r"\Z"),
    }


def baixar(fid, destino):
    """Master do Drive. confirm=t pula o aviso de 'grande demais para varrer'."""
    url = f"https://drive.usercontent.google.com/download?id={fid}&export=download&confirm=t"
    parcial = destino.with_suffix(".parcial")
    r = subprocess.run(["curl", "-sL", "--fail", "--max-time", "1800",
                        "-o", str(parcial), url])
    if r.returncode != 0 or parcial.stat().st_size < 100_000:
        parcial.unlink(missing_ok=True)
        return False
    parcial.rename(destino)
    return True


def sondar(arq):
    r = subprocess.run(
        ["ffprobe", "-v", "error", "-print_format", "json", "-show_streams",
         "-show_format", str(arq)], capture_output=True, text=True)
    d = json.loads(r.stdout)
    v = next(s for s in d["streams"] if s["codec_type"] == "video")
    tem_audio = any(s["codec_type"] == "audio" for s in d["streams"])
    return {
        "w": int(v["width"]), "h": int(v["height"]),
        "codec": v["codec_name"], "audio": tem_audio,
        "dur": float(d["format"].get("duration", 0)),
    }


def converter(origem, destino, info):
    """Converte para um arquivo temporário e só então põe no lugar: enquanto o
    ffmpeg escreve, o mp4 ainda não tem o índice, e um arquivo pela metade
    dentro de assets/ faz o drive-sync anunciar como pronto um vídeo que o
    navegador não consegue abrir."""
    parcial = destino.with_suffix(".parcial")
    escala = []
    if max(info["w"], info["h"]) > LADO_MAIOR:
        # limita o lado maior; -2 mantém a proporção e fecha em número par,
        # que o H.264 exige
        alvo = f"scale=-2:{LADO_MAIOR}" if info["h"] >= info["w"] \
            else f"scale={LADO_MAIOR}:-2"
        escala = ["-vf", alvo]
    audio = ["-c:a", "aac", "-b:a", f"{AUDIO_KBPS}k"] if info["audio"] else ["-an"]
    cmd = (["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-i", str(origem)]
           + escala
           + ["-threads", str(THREADS),
              "-c:v", "libx264", "-preset", PRESET, "-crf", str(CRF),
              "-pix_fmt", "yuv420p", "-profile:v", "high", "-level", "4.1",
              # faststart põe o índice no começo: o vídeo abre sem baixar tudo
              "-movflags", "+faststart", "-f", "mp4"]
           + audio + [str(parcial)])
    if subprocess.run(cmd).returncode != 0:
        parcial.unlink(missing_ok=True)
        return False
    parcial.replace(destino)
    return True


def sincronizar(grupo, videos, manter_master):
    base = RAIZ / "assets" / grupo / "video"
    base.mkdir(parents=True, exist_ok=True)
    CACHE.mkdir(parents=True, exist_ok=True)
    arq_manifesto = base / "_manifesto.json"
    manifesto = json.loads(arq_manifesto.read_text(encoding="utf-8")) \
        if arq_manifesto.exists() else {}
    ajuste = {"crf": CRF, "preset": PRESET, "lado": LADO_MAIOR, "audio": AUDIO_KBPS}

    def gravar_manifesto():
        """Depois de cada vídeo, não só no fim: a conversão do lote leva horas e
        uma interrupção no meio não pode jogar fora o que já ficou pronto."""
        arq_manifesto.write_text(json.dumps(manifesto, indent=2), encoding="utf-8")

    for v in videos:
        fid, nome = v["id"], f"{v['id']}.mp4"
        destino = base / nome
        if destino.exists() and manifesto.get(nome, {}).get("ajuste") == ajuste:
            print(f"  · {v['titulo']}: já convertido", file=sys.stderr)
            continue

        master = CACHE / f"{fid}.master"
        if not master.exists():
            print(f"  ↓ {v['titulo']}: baixando…", file=sys.stderr)
            if not baixar(fid, master):
                print(f"  ! {v['titulo']}: download falhou", file=sys.stderr)
                continue
        info = sondar(master)
        print(f"  ⚙ {v['titulo']}: {info['w']}×{info['h']} {info['codec']} "
              f"{info['dur']:.0f}s · {master.stat().st_size/1e6:.0f} MB → convertendo…",
              file=sys.stderr)
        if not converter(master, destino, info):
            print(f"  ! {v['titulo']}: conversão falhou", file=sys.stderr)
            destino.unlink(missing_ok=True)
            continue
        manifesto[nome] = {"id": fid, "ajuste": ajuste,
                           "master_bytes": master.stat().st_size,
                           "bytes": destino.stat().st_size}
        gravar_manifesto()
        print(f"    → {destino.stat().st_size/1e6:.1f} MB "
              f"({destino.stat().st_size/master.stat().st_size*100:.0f}% do master)",
              file=sys.stderr)
        if not manter_master:
            master.unlink(missing_ok=True)

    # limpa sobras: vídeo que saiu do Drive ou ganhou YouTube, e conversão
    # interrompida
    validos = {f"{v['id']}.mp4" for v in videos}
    for arq in base.glob("*.mp4"):
        if arq.name not in validos:
            arq.unlink()
            manifesto.pop(arq.name, None)
    for arq in base.glob("*.parcial"):
        arq.unlink()
    gravar_manifesto()
    total = sum(m["bytes"] for m in manifesto.values())
    print(f"→ assets/{grupo}/video: {len(manifesto)} vídeos · {total/1e6:.0f} MB",
          file=sys.stderr)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--conteudo", action="store_true")
    ap.add_argument("--cobertura", action="store_true")
    ap.add_argument("--manter-master", action="store_true",
                    help="não apaga o download do cache depois de converter")
    a = ap.parse_args()
    grupos = [g for g in ("conteudo", "cobertura") if getattr(a, g)] \
        or ["conteudo", "cobertura"]
    dados = videos_gerados()
    for g in grupos:
        print(f"== {g}", file=sys.stderr)
        sincronizar(g, dados[g], a.manter_master)


if __name__ == "__main__":
    main()
