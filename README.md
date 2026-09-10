# filmora

Site institucional da **filmora**, agência de produção audiovisual especializada em
fotografia e filmes de **casamentos** e **eventos**.

🌐 Produção: https://filmora-black.vercel.app

## Sobre

Experiência premium, clara e responsiva, com:

- Tema **claro/escuro** (padrão claro, com toggle memorizado)
- Índice de **serviços** escalável (6 ativos hoje; arquitetura pronta para as demais frentes)
- Galerias em **álbuns** → carrossel em tela cheia (contador, teclado e swipe no mobile)
- Seção **Casamentos** com o filme (YouTube) e álbum fotográfico
- Seções **Making Of da Noiva** e **Cerimônia do Jaleco**, cada uma com galeria completa
- Seção **Cobertura Fotográfica de Eventos** com álbuns por evento
- Seção **Gerenciamento de Perfil** com os reels verticais e página própria do serviço
- Contato via **WhatsApp** e Instagram
- Animações suaves, scroll nativo e blindagem de usabilidade

## Stack

Estático: HTML + CSS + JavaScript (GSAP/ScrollTrigger via CDN). Sem build.

```
site/
├── index.html
├── css/styles.css
├── js/main.js         # home
├── js/galeria.js      # páginas de galeria completa
├── js/conteudo.js     # página de produção de conteúdo
├── galeria/           # páginas geradas por tools/drive-sync.py
└── assets/            # logos, fotos, pôsteres de vídeo, retratos da equipe
```

## Sincronizar com o Google Drive

As galerias completas, os pôsteres de vídeo e as páginas de `galeria/` são
gerados a partir das pastas do Drive (que precisam estar como "qualquer pessoa
com o link"). O download é incremental.

```bash
python3 tools/drive-sync.py    # fotos, páginas e js/galerias-data.js
```

Do Drive vem só o pôster e o título dos vídeos. O player toca, nesta ordem:

1. **YouTube**: mapa `YOUTUBE` no `drive-sync.py` (id do Drive → id do YouTube).
2. **Arquivo do próprio site**: o que não está no YouTube o `tools/video-sync.py`
   baixa do Drive e converte para H.264 720p (~20–30 MB por minuto), em
   `assets/<cobertura|conteudo>/video/`.
3. **Drive** (`/preview`): só se nenhum dos dois existir.

```bash
python3 tools/video-sync.py    # baixa e converte os vídeos sem YouTube
python3 tools/drive-sync.py    # depois: marca no site os que ganharam arquivo
```

Quando um vídeo entra no mapa `YOUTUBE`, rodar o `video-sync.py` de novo apaga
o mp4 que ele deixou de usar.

## Rodar localmente

```bash
python -m http.server 8137
```

Depois abra http://localhost:8137

## Deploy

Publicado na Vercel (produção em `filmora-black.vercel.app`).

```bash
vercel deploy --prod
```
