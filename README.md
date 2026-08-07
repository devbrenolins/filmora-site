# filmora

Site institucional da **filmora**, agência de produção audiovisual especializada em
fotografia e filmes de **casamentos** e **eventos**.

🌐 Produção: https://filmora-black.vercel.app

## Sobre

Experiência premium, clara e responsiva, com:

- Tema **claro/escuro** (padrão claro, com toggle memorizado)
- Índice de **serviços** escalável (2 ativos hoje; arquitetura pronta para as demais frentes)
- Galerias em **álbuns** → carrossel em tela cheia (contador, teclado e swipe no mobile)
- Seção **Casamentos** com o filme (YouTube) e álbum fotográfico
- Seção **Cobertura Fotográfica de Eventos** com álbuns por evento
- Contato via **WhatsApp** e Instagram
- Animações suaves, scroll nativo e blindagem de usabilidade

## Stack

Estático: HTML + CSS + JavaScript (GSAP/ScrollTrigger via CDN). Sem build.

```
site/
├── index.html
├── css/styles.css
├── js/main.js
└── assets/            # logos, fotos (casamento, eventos), retratos da equipe
```

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
