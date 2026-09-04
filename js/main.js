/* ═══════════ filmora: premium ═══════════ */
gsap.registerPlugin(ScrollTrigger);
const reduced = matchMedia("(prefers-reduced-motion: reduce)").matches;
const $ = (s, c = document) => c.querySelector(s);
const $$ = (s, c = document) => [...c.querySelectorAll(s)];

/* guard de usabilidade: qualquer erro não pode deixar a página travada/invisível */
addEventListener("error", () => {
  document.getElementById("loader")?.remove();
  document.body.classList.add("ready");
  document.querySelectorAll(".rv").forEach(el => el.classList.add("is-in"));
});

/* ── scroll suave nativo (rápido e confiável em qualquer aparelho) ── */
const lenis = null; // Lenis removido: causava travamento do motor de animação
function smoothTo(target, offset = 68) {
  const el = target === "#top" ? document.body : $(target);
  if (!el) return;
  const y = target === "#top" ? 0 : el.getBoundingClientRect().top + scrollY - offset;
  scrollTo({ top: y, behavior: reduced ? "auto" : "smooth" });
}

/* ── CONFIG DAS SEÇÕES (escalável: ative novas mudando active:true) ── */
const SECTIONS = [
  { slug: "casamentos", name: "Casamentos", active: true, target: "#casamentos",
    cover: "assets/casamento/cas-353.jpg",
    desc: "Fotografia e cinema para o dia mais importante." },
  { slug: "making-of", name: "Making Of da Noiva", active: true, target: "#making-of",
    cover: "assets/galerias/making-of-noiva/thumb/030.webp",
    desc: "Os preparativos da noiva, do vestido no cabide ao altar." },
  { slug: "eventos", name: "Aniversários", active: true, target: "#eventos",
    cover: "assets/eventos/infantil-rosa/rosa-013.jpg",
    desc: "Aniversários, bodas e festas com olhar editorial." },
  { slug: "jaleco", name: "Cerimônia do Jaleco", active: true, target: "#jaleco",
    cover: "assets/galerias/cerimonia-jaleco/thumb/012.webp",
    desc: "Formatura e vida acadêmica registradas por inteiro." },
  { slug: "cobertura", name: "Cobertura de Eventos", active: true, target: "#cobertura",
    cover: "assets/cobertura/1gOngPusctonXmINtlhpUbA2qUFhXxxn4.webp",
    desc: "Stories e Aftermovies." },
  { slug: "social", name: "Gestão de Redes Sociais", active: true, target: "#conteudo",
    cover: "assets/conteudo/capa.webp",
    desc: "Reels verticais produzidos em lote para o seu perfil." },
  { slug: "marcas", name: "Conteúdo para Marcas", active: false,
    desc: "Vídeos e fotos avulsos para produtos e negócios." },
  { slug: "storymaker", name: "Cobertura em Tempo Real · Storymaker", active: false,
    desc: "Registro ao vivo do seu evento, em tempo real." },
  { slug: "design", name: "Design & Identidade Visual", active: false,
    desc: "Marcas, convites e peças gráficas com assinatura." },
  { slug: "politica", name: "Comunicação Política", active: false,
    desc: "Imagem, vídeo e estratégia para campanhas." },
  { slug: "aereas", name: "Imagens Aéreas", active: false,
    desc: "Tomadas de drone que ampliam a narrativa." },
];

/* ── dados das galerias ── */
const CASAMENTO = [
  353, 335, 306, 20, 313, 90, 331, 25, 322, 7, 344, 185,
  234, 326, 95, 347, 329, 14, 339, 92, 311, 356, 183, 327,
  6, 100, 232, 345, 354, 185,
].filter((v, i, a) => a.indexOf(v) === i)
 .map(n => `assets/casamento/cas-${String(n).padStart(3, "0")}.jpg`);

/* Páginas de galeria completa (geradas por tools/drive-sync.py).
   null = ainda não existe → o link some do álbum. */
const GALERIA = {
  casamento: "casamento-rs",
  menina:    "festa-menina",
  menino:    "festa-menino",
  cinquenta: "50-anos",
};

const EVENTOS = [
  {
    name: "50 Anos",
    tag: "festa country",
    dir: "assets/eventos/cinquenta",
    galeria: GALERIA.cinquenta,
    imgs: ["c50-000", "c50-008", "c50-002", "c50-007", "c50-009", "c50-012"],
  },
  {
    name: "Festa Menina",
    tag: "2 anos · fazendinha",
    dir: "assets/eventos/infantil-rosa",
    galeria: GALERIA.menina,
    imgs: ["rosa-013", "rosa-005", "rosa-000", "rosa-004", "rosa-015", "rosa-003"],
  },
  {
    name: "Festa Menino",
    tag: "festa temática · cowboy",
    dir: "assets/eventos/infantil-cowboy",
    galeria: GALERIA.menino,
    imgs: ["cow-002", "cow-000", "cow-009", "cow-012", "cow-005", "cow-001"],
  },
];
const LAYOUT = ["e-a", "e-b", "e-c", "e-d", "e-e", "e-f"];

/* Álbuns cujas fotos já vêm inteiras do drive-sync: a prévia da home é uma
   amostra espalhada pelo mesmo material da página completa, sem arquivo
   duplicado no repositório. `capa` é o índice da foto que abre o card. */
function albumDaGaleria(slug, capa = 0, n = 12) {
  const d = (window.GALERIAS || {})[slug];
  if (!d || !d.fotos.length) return null;
  const passo = Math.max(1, d.fotos.length / n);
  const escolhidas = [];
  while (escolhidas.length < Math.min(n, d.fotos.length)) {
    escolhidas.push(d.fotos[Math.floor(escolhidas.length * passo)][0]);
  }
  return {
    title: d.titulo, tag: d.tag, galeria: slug,
    cover: `${d.dir}/thumb/${d.fotos[Math.min(capa, d.fotos.length - 1)][0]}`,
    photos: escolhidas.map(f => `${d.dir}/full/${f}`),
  };
}
const NOVOS = {
  "making-of-noiva": albumDaGaleria("making-of-noiva", 22),
  "cerimonia-jaleco": albumDaGaleria("cerimonia-jaleco", 39),
};

/* ── THEME ── */
const root = document.documentElement;
$("#themeToggle").addEventListener("click", () => {
  const next = root.getAttribute("data-theme") === "dark" ? "light" : "dark";
  root.setAttribute("data-theme", next);
  try { localStorage.setItem("filmora-theme", next); } catch (e) {}
  document.querySelector('meta[name="theme-color"]')
    .setAttribute("content", next === "dark" ? "#110f0c" : "#f7f4ef");
});

/* ── ÁLBUNS (visitante escolhe → abre o carrossel) ── */
const ALBUMS = {
  // Casamentos
  "cas-rs": {
    title: "Casamento R&S", tag: "Fotografia e cinema",
    cover: "assets/casamento/cas-326.jpg", photos: CASAMENTO, galeria: GALERIA.casamento,
  },
  // Making of e cerimônia do jaleco (dados gerados pelo drive-sync)
  ...Object.fromEntries(Object.entries(NOVOS).filter(([, a]) => a)),
  // Eventos
  ...Object.fromEntries(EVENTOS.map((ev) => {
    const photos = ev.imgs.map(n => `${ev.dir}/${n}.jpg`);
    return [ev.dir, { title: ev.name, tag: ev.tag, cover: photos[0], photos, galeria: ev.galeria }];
  })),
};
/* link "galeria completa": só aparece se o álbum já tiver página */
function fullLink(a, cls) {
  if (!a.galeria) return "";
  const dados = (window.GALERIAS || {})[a.galeria];
  const total = dados ? ` <em>· ${dados.fotos.length} fotos</em>` : "";
  return `<a class="${cls}" href="/galeria/${a.galeria}.html"
    aria-label="Ver a galeria completa de ${a.title}">Ver galeria completa${total} <span>→</span></a>`;
}
function albumCard(id, feature, i = 0) {
  const a = ALBUMS[id];
  return `<article class="album rv${feature ? " album--feature" : ""}" data-open="${id}" style="transition-delay:${i * 0.08}s">
    <div class="album__cover">
      <img src="${a.cover}" alt="${a.title}, filmora" loading="lazy">
      <span class="album__count">${a.photos.length} fotos</span>
      <span class="album__view">Ver álbum <span>→</span></span>
    </div>
    <div class="album__meta">
      <h3 class="album__title">${a.title}</h3>
      <span class="album__tag">${a.tag}</span>
      ${fullLink(a, "album__full")}
    </div>
  </article>`;
}
$("#galCasamento").innerHTML = albumCard("cas-rs", true);
$("#eventsWrap").innerHTML = EVENTOS.map((ev, i) => albumCard(ev.dir, false, i)).join("");

/* seção sem dados sai da página inteira: melhor não existir do que existir vazia */
function montarSecao(slug, alvo, secao) {
  if (NOVOS[slug]) $(alvo).innerHTML = albumCard(slug, true);
  else $(secao)?.remove();
}
montarSecao("making-of-noiva", "#galMakingOf", "#making-of");
montarSecao("cerimonia-jaleco", "#galJaleco", "#jaleco");

/* ── CARDS DE VÍDEO (cobertura e produção de conteúdo, hospedados no Drive) ── */
function cardVideo(v, i, vertical = false) {
  return `
  <article class="vid rv" data-drive="${v.id}"${vertical ? " data-vert" : ""} style="transition-delay:${i * 0.06}s">
    <div class="vid__poster">
      <img src="${v.poster}" alt="${v.titulo}, filmora" loading="lazy">
      ${v.destaque ? '<span class="vid__badge">Destaque</span>' : ""}
      <span class="vid__play" aria-hidden="true">
        <svg width="20" height="20" viewBox="0 0 24 24" fill="currentColor"><path d="M8 5v14l11-7z"/></svg>
      </span>
    </div>
    <div class="vid__meta">
      <h3 class="vid__title">${v.titulo}</h3>
      <span class="vid__tag">${v.tag}</span>
    </div>
  </article>`;
}

/* ── COBERTURA DE EVENTOS (stories + aftermovies) ── */
const VIDEOS = window.COBERTURA || [];
$("#vidsWrap").innerHTML = VIDEOS.map((v, i) => cardVideo(v, i)).join("");

/* ── PRODUÇÃO DE CONTEÚDO (só vertical: o destino das peças é o Instagram) ── */
const CONTEUDO = window.CONTEUDO || [];
const PREVIA_CONTEUDO = 4;      // uma fileira limpa; o resto fica na página do serviço

/* Os dados vêm lote por lote, uma criadora depois da outra — ordem que a página
   do serviço mantém. Aqui só cabem as primeiras peças, e cortar em ordem traria
   quase todas do mesmo perfil, então a vitrine reveza entre eles. */
function previaEquilibrada(pecas, n) {
  const filas = new Map();
  pecas.forEach((p) => {
    const fila = filas.get(p.perfil) || [];
    fila.push(p);
    filas.set(p.perfil, fila);
  });
  const escolhidas = [];
  while (escolhidas.length < Math.min(n, pecas.length)) {
    for (const fila of filas.values()) {
      if (escolhidas.length >= n) break;
      if (fila.length) escolhidas.push(fila.shift());
    }
  }
  return escolhidas;
}

if (CONTEUDO.length) {
  $("#conteudoWrap").innerHTML =
    previaEquilibrada(CONTEUDO, PREVIA_CONTEUDO).map((v, i) => cardVideo(v, i, true)).join("");
  if (CONTEUDO.length > PREVIA_CONTEUDO) {
    $("#conteudoMais").textContent = `Ver todas as ${CONTEUDO.length} peças`;
  }
} else {
  $("#conteudo")?.remove();
}

/* ── índice de serviços ──
   Roda depois das seções porque uma seção sem material se remove da página, e
   um card que rola para lugar nenhum é pior do que card nenhum. */
$("#svcGrid").innerHTML = SECTIONS.filter(s => s.active && $(s.target)).map((s, i) => {
  const n = String(i + 1).padStart(2, "0");
  return `<article class="svc svc--on" data-go="${s.target}">
    <div class="svc__img"><img src="${s.cover}" alt="${s.name}, filmora" loading="lazy"></div>
    <div class="svc__body">
      <span class="svc__num">${n}</span>
      <h3 class="svc__name">${s.name}</h3>
      <p class="svc__desc">${s.desc}</p>
      <span class="svc__foot">Ver galeria <span class="svc__arrow">→</span></span>
    </div>
  </article>`;
}).join("");
$$('.svc--on').forEach(el => el.addEventListener("click", () => smoothTo(el.dataset.go)));

/* ── CARROSSEL / LIGHTBOX ── */
const lb = $("#lb"), lbImg = $("#lbImg"), lbCount = $("#lbCount"), lbFull = $("#lbFull");
let lbList = [], lbIndex = 0;
function openGallery(album, index = 0) {
  lbList = album.photos; lbIndex = index;
  lbFull.innerHTML = fullLink(album, "lb__full-link");
  showLb();
  lb.classList.add("is-open");
  lb.setAttribute("aria-hidden", "false");
  document.body.style.overflow = "hidden";
  if (lenis) lenis.stop();
}
function preload(src){ const i = new Image(); i.src = src; }
function showLb() {
  const src = lbList[lbIndex];
  lbCount.textContent = `${lbIndex + 1} / ${lbList.length}`;
  lbImg.style.opacity = 0;                                  // fade-out suave
  const swap = () => {
    const im = new Image();
    im.onload = () => { lbImg.src = im.src; requestAnimationFrame(() => (lbImg.style.opacity = 1)); };
    im.src = src;
  };
  // vizinhas já pré-carregadas → troca é instantânea; espera o fade-out
  setTimeout(swap, 200);
  preload(lbList[(lbIndex + 1) % lbList.length]);
  preload(lbList[(lbIndex - 1 + lbList.length) % lbList.length]);
}
function closeLb() {
  lb.classList.remove("is-open");
  lb.setAttribute("aria-hidden", "true");
  document.body.style.overflow = "";
  if (lenis) lenis.start();
}
function step(d) { lbIndex = (lbIndex + d + lbList.length) % lbList.length; showLb(); }
document.addEventListener("click", (e) => {
  if (e.target.closest("a")) return;            // link da galeria completa segue seu caminho
  const card = e.target.closest("[data-open]");
  if (card) openGallery(ALBUMS[card.dataset.open], 0);
});
$("#lbClose").addEventListener("click", closeLb);
$("#lbPrev").addEventListener("click", () => step(-1));
$("#lbNext").addEventListener("click", () => step(1));
lb.addEventListener("click", (e) => { if (e.target === lb || e.target === lbImg.parentElement) closeLb(); });
addEventListener("keydown", (e) => {
  if (!lb.classList.contains("is-open")) return;
  if (e.key === "Escape") closeLb();
  if (e.key === "ArrowRight") step(1);
  if (e.key === "ArrowLeft") step(-1);
});
/* swipe no mobile */
let tx = 0;
lb.addEventListener("touchstart", (e) => { tx = e.changedTouches[0].clientX; }, { passive: true });
lb.addEventListener("touchend", (e) => {
  const dx = e.changedTouches[0].clientX - tx;
  if (Math.abs(dx) > 45) step(dx < 0 ? 1 : -1);
}, { passive: true });
lbImg.style.transition = "opacity .4s ease";

/* ── PLAYER DE VÍDEO ──
   Todo vídeo é servido pelo Drive; o site guarda só o pôster. */
const vlb = $("#vlb"), vlbFrame = $("#vlbFrame");
function abrirPlayer({ id, rotulo, vertical }) {
  /* reel em moldura 16/9 fica minúsculo no meio de duas tarjas pretas */
  vlbFrame.classList.toggle("vlb__frame--vert", !!vertical);
  vlbFrame.innerHTML =
    `<iframe src="https://drive.google.com/file/d/${id}/preview" title="${rotulo}, filmora"
      allow="autoplay; encrypted-media; fullscreen; picture-in-picture"
      referrerpolicy="strict-origin-when-cross-origin" allowfullscreen></iframe>
     <a class="vlb__fallback" href="https://drive.google.com/file/d/${id}/view"
        target="_blank" rel="noopener">Não carregou? Abrir em nova aba →</a>`;
  vlb.classList.add("is-open");
  vlb.setAttribute("aria-hidden", "false");
  document.body.style.overflow = "hidden";
}
document.addEventListener("click", (e) => {
  const card = e.target.closest("[data-drive]");
  if (!card) return;
  abrirPlayer({
    id: card.dataset.drive,
    rotulo: card.querySelector(".vid__title")?.textContent || "Vídeo",
    vertical: card.hasAttribute("data-vert"),
  });
});
function closeVideo() {
  vlb.classList.remove("is-open");
  vlb.setAttribute("aria-hidden", "true");
  vlbFrame.innerHTML = "";
  document.body.style.overflow = "";
}
$("#vlbClose").addEventListener("click", closeVideo);
vlb.addEventListener("click", (e) => { if (e.target === vlb) closeVideo(); });
addEventListener("keydown", (e) => { if (e.key === "Escape" && vlb.classList.contains("is-open")) closeVideo(); });

/* ── NAV ── */
const nav = $("#nav");
addEventListener("scroll", () => nav.classList.toggle("is-scrolled", scrollY > 40), { passive: true });
$("#burger").addEventListener("click", () => {
  const open = nav.classList.toggle("is-open");
  document.body.style.overflow = open ? "hidden" : "";
});
$$('[data-link]').forEach(a => a.addEventListener("click", (e) => {
  const id = a.getAttribute("href");
  if (id && id.startsWith("#")) {
    e.preventDefault();
    nav.classList.remove("is-open");
    document.body.style.overflow = "";
    smoothTo(id);
  }
}));

/* ── REVEALS (rápido, sutil) ── */
function reveal() {
  const els = $$(".rv");
  const show = (el) => el.classList.add("is-in");
  if ("IntersectionObserver" in window) {
    const io = new IntersectionObserver((entries) => {
      entries.forEach(en => { if (en.isIntersecting) { show(en.target); io.unobserve(en.target); } });
    }, { threshold: 0.1, rootMargin: "0px 0px -6% 0px" });
    els.forEach(el => io.observe(el));
  }
  // failsafes de usabilidade: nada pode ficar invisível
  const sweep = () => els.forEach(el => {
    if (!el.classList.contains("is-in") && el.getBoundingClientRect().top < innerHeight * 0.94) show(el);
  });
  addEventListener("scroll", sweep, { passive: true });
  addEventListener("load", sweep);
  setTimeout(sweep, 350);
  setTimeout(() => els.forEach(show), 2600);   // último recurso: revela tudo
}

/* parallax suave do hero (opcional; só decorativo) */
function heroParallax() {
  if (reduced) return;
  gsap.to(".hero__media img", {
    yPercent: 8, ease: "none",
    scrollTrigger: { trigger: ".hero", start: "top top", end: "bottom top", scrub: true },
  });
}

/* ── LOADER à prova de falhas (independe do motor de animação) ── */
const loader = $("#loader");
function killLoader() {
  if (loader && loader.parentNode) loader.remove();
  document.body.classList.add("ready");
}
if (loader && !reduced) {
  loader.addEventListener("animationend", (e) => { if (e.target === loader) killLoader(); });
  setTimeout(killLoader, 2200);           // failsafe absoluto
} else {
  killLoader();
}

reveal();          // IntersectionObserver + CSS revelam tudo (não depende de gsap)
heroParallax();    // enfeite; se não rodar, sem problema
addEventListener("load", () => ScrollTrigger.refresh && ScrollTrigger.refresh());
