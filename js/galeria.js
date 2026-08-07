/* ═══════════ filmora: página de galeria completa ═══════════ */
const $ = (s, c = document) => c.querySelector(s);
const $$ = (s, c = document) => [...c.querySelectorAll(s)];
const reduced = matchMedia("(prefers-reduced-motion: reduce)").matches;

/* Fotos servidas pelo próprio site (baixadas por tools/drive-sync.py).
   thumb 700px no mosaico, full 1600px no lightbox. */
const thumbURL = (dir, n) => `${dir}/thumb/${n}`;
const fullURL  = (dir, n) => `${dir}/full/${n}`;

const LOTE = 60;                                   // fotos por rodada
const slug  = $("main.gal").dataset.album;
const album = (window.GALERIAS || {})[slug];

const grid = $("#galGrid"), more = $("#galMore"), count = $("#galCount");

function montarGaleria() {
  const fotos = album.fotos;
  const dir = album.dir;
  let mostradas = 0;

  count.textContent = `${fotos.length} fotos`;

  /* O mosaico é montado com flexbox: uma <div> por coluna, as fotos distribuídas
     na coluna mais curta. Antes era CSS multi-column, que o WebKit até o Safari 16
     pinta errado quando há imagem dentro — era esse o defeito do iOS 16. Flexbox
     não tem fragmentação, então não há o que dar errado. */
  const colunasAgora = () => (innerWidth <= 560 ? 1 : innerWidth <= 1000 ? 2 : 3);
  let colunasMontadas = 0;

  const tile = ([arq, w, h], i) => `
    <button class="gal__tile" data-i="${i}" type="button"
      style="aspect-ratio:${w}/${h}"
      aria-label="Abrir foto ${i + 1} de ${fotos.length}">
      <img data-src="${thumbURL(dir, arq)}" width="${w}" height="${h}"
        alt="${album.titulo}, foto ${i + 1}" decoding="async">
    </button>`;

  function montar() {
    const n = colunasAgora();
    colunasMontadas = n;
    const colunas = Array.from({ length: n }, () => []);
    const altura = new Array(n).fill(0);
    fotos.slice(0, mostradas).forEach((foto, i) => {
      let menor = 0;
      for (let c = 1; c < n; c++) if (altura[c] < altura[menor]) menor = c;
      colunas[menor].push(tile(foto, i));
      altura[menor] += foto[2] / foto[1];      // altura relativa à largura da coluna
    });
    grid.innerHTML = colunas
      .map((c) => `<div class="gal__col">${c.join("")}</div>`)
      .join("");
    observar();
  }

  function render() {
    mostradas = Math.min(mostradas + LOTE, fotos.length);
    montar();
    more.hidden = mostradas >= fotos.length;
    more.textContent = `Carregar mais ${Math.min(LOTE, fotos.length - mostradas)} fotos`;
  }

  /* remonta só quando o número de colunas muda, para não recarregar imagem à toa */
  let tempoResize;
  addEventListener("resize", () => {
    clearTimeout(tempoResize);
    tempoResize = setTimeout(() => {
      if (colunasAgora() !== colunasMontadas) montar();
    }, 200);
  });

  /* Carregamento sob demanda por IntersectionObserver, em vez do loading="lazy"
     nativo, que o Safari 15.4 a 16 trata com heurística estrita demais. */
  const carregar = (img) => {
    if (!img.dataset.src) return;
    img.src = img.dataset.src;
    delete img.dataset.src;
  };
  const io = "IntersectionObserver" in window
    ? new IntersectionObserver((ents) => {
        ents.forEach((e) => {
          if (e.isIntersecting) { carregar(e.target); io.unobserve(e.target); }
        });
      }, { rootMargin: "600px 0px" })
    : null;
  function observar() {
    const pendentes = $$("#galGrid img[data-src]");
    if (!io) { pendentes.forEach(carregar); return; }
    pendentes.forEach((img) => io.observe(img));
    /* rede de segurança: se o observer não disparar, as fotos entram assim mesmo */
    clearTimeout(observar.rede);
    observar.rede = setTimeout(() => $$("#galGrid img[data-src]").forEach(carregar), 2500);
  }

  render();
  more.addEventListener("click", render);

  /* foto que não carrega não deixa buraco no mosaico */
  grid.addEventListener("error", (e) => {
    if (e.target.tagName === "IMG") e.target.closest(".gal__tile")?.remove();
  }, true);

  /* ── lightbox ── */
  const lb = $("#lb"), lbImg = $("#lbImg"), lbCount = $("#lbCount");
  let idx = 0;
  lbImg.style.transition = "opacity .4s ease";

  const preload = src => { new Image().src = src; };

  function show() {
    lbCount.textContent = `${idx + 1} / ${fotos.length}`;
    lbImg.style.opacity = 0;
    setTimeout(() => {
      const im = new Image();
      im.onload = () => { lbImg.src = im.src; requestAnimationFrame(() => (lbImg.style.opacity = 1)); };
      im.src = fullURL(dir, fotos[idx][0]);
    }, 200);
    preload(fullURL(dir, fotos[(idx + 1) % fotos.length][0]));
    preload(fullURL(dir, fotos[(idx - 1 + fotos.length) % fotos.length][0]));
  }
  function abrirFoto(i) {
    idx = i; show();
    lb.classList.add("is-open");
    lb.setAttribute("aria-hidden", "false");
    document.body.style.overflow = "hidden";
  }
  function fecharFoto() {
    lb.classList.remove("is-open");
    lb.setAttribute("aria-hidden", "true");
    document.body.style.overflow = "";
  }
  const step = d => { idx = (idx + d + fotos.length) % fotos.length; show(); };

  grid.addEventListener("click", (e) => {
    const tile = e.target.closest(".gal__tile");
    if (tile) abrirFoto(Number(tile.dataset.i));
  });
  $("#lbClose").addEventListener("click", fecharFoto);
  $("#lbPrev").addEventListener("click", () => step(-1));
  $("#lbNext").addEventListener("click", () => step(1));
  lb.addEventListener("click", (e) => {
    if (e.target === lb || e.target === lbImg.parentElement) fecharFoto();
  });
  addEventListener("keydown", (e) => {
    if (!lb.classList.contains("is-open")) return;
    if (e.key === "Escape") fecharFoto();
    if (e.key === "ArrowRight") step(1);
    if (e.key === "ArrowLeft") step(-1);
  });
  let tx = 0;
  lb.addEventListener("touchstart", (e) => { tx = e.changedTouches[0].clientX; }, { passive: true });
  lb.addEventListener("touchend", (e) => {
    const dx = e.changedTouches[0].clientX - tx;
    if (Math.abs(dx) > 45) step(dx < 0 ? 1 : -1);
  }, { passive: true });
}

/* Cada recurso da página roda isolado: uma falha no mosaico não pode levar junto
   o vídeo e o menu, que vêm depois no arquivo. Foi assim que um erro só apareceu
   como dois defeitos distintos. */
function protegido(nome, fn) {
  try { fn(); } catch (e) { console.error(`[filmora] ${nome}:`, e); }
}


/* ── filme do álbum (YouTube, no lightbox de vídeo) ── */
function montarFilme() {
  const filme = $(".galfilme"), vlb = $("#vlb"), vlbFrame = $("#vlbFrame");
  if (!filme || !vlb) return;
  const yt = filme.dataset.yt;
  const abrir = () => {
    const origin = location.protocol.startsWith("http")
      ? `&origin=${encodeURIComponent(location.origin)}` : "";
    vlbFrame.innerHTML =
      `<iframe src="https://www.youtube.com/embed/${yt}?autoplay=1&rel=0&modestbranding=1&playsinline=1${origin}"
        title="Filme, filmora" allow="autoplay; encrypted-media; fullscreen; picture-in-picture"
        referrerpolicy="strict-origin-when-cross-origin" allowfullscreen></iframe>
       <a class="vlb__fallback" href="https://youtu.be/${yt}" target="_blank" rel="noopener">Não carregou? Abrir no YouTube →</a>`;
    vlb.classList.add("is-open");
    vlb.setAttribute("aria-hidden", "false");
    document.body.style.overflow = "hidden";
  };
  const fechar = () => {
    vlb.classList.remove("is-open");
    vlb.setAttribute("aria-hidden", "true");
    vlbFrame.innerHTML = "";                 // corta o áudio ao fechar
    document.body.style.overflow = "";
  };
  filme.addEventListener("click", abrir);
  $("#vlbClose").addEventListener("click", (e) => { e.stopPropagation(); fechar(); });
  vlb.addEventListener("click", (e) => { if (e.target === vlb) fechar(); });
  addEventListener("keydown", (e) => {
    if (e.key === "Escape" && vlb.classList.contains("is-open")) fechar();
  });
}

/* ── nav (mesmo comportamento da home) ── */
function montarNav() {
  const nav = $("#nav");
  addEventListener("scroll", () => nav.classList.toggle("is-scrolled", scrollY > 40), { passive: true });
  $("#burger").addEventListener("click", () => {
    const aberto = nav.classList.toggle("is-open");
    document.body.style.overflow = aberto ? "hidden" : "";
  });
  const root = document.documentElement;
  $("#themeToggle").addEventListener("click", () => {
    const next = root.getAttribute("data-theme") === "dark" ? "light" : "dark";
    root.setAttribute("data-theme", next);
    try { localStorage.setItem("filmora-theme", next); } catch (e) {}
    document.querySelector('meta[name="theme-color"]')
      ?.setAttribute("content", next === "dark" ? "#110f0c" : "#f7f4ef");
  });
}

/* Ordem proposital: vídeo e menu entram antes do mosaico. Assim, mesmo que a
   galeria falhasse, os dois já estariam ligados. */
protegido("filme", montarFilme);
protegido("nav", montarNav);

if (!album || !album.fotos.length) {
  count.textContent = "Galeria em preparação.";
} else {
  protegido("galeria", montarGaleria);
}
