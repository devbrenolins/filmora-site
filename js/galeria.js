/* ═══════════ filmora: página de galeria completa ═══════════ */
const $ = (s, c = document) => c.querySelector(s);
const $$ = (s, c = document) => [...c.querySelectorAll(s)];
const reduced = matchMedia("(prefers-reduced-motion: reduce)").matches;

/* Fotos vêm do CDN do Google, redimensionadas no servidor deles.
   O CDN aplica cota por site que referencia e responde 429 quando estoura;
   por isso toda requisição de imagem vai sem Referer (referrerpolicy). */
const thumbURL = id => `https://lh3.googleusercontent.com/d/${id}=w800`;
const fullURL  = id => `https://lh3.googleusercontent.com/d/${id}=w1800`;
const semReferer = (img) => { img.referrerPolicy = "no-referrer"; return img; };

const LOTE = 60;                                   // fotos por rodada
const slug  = $("main.gal").dataset.album;
const album = (window.GALERIAS || {})[slug];

const grid = $("#galGrid"), more = $("#galMore"), count = $("#galCount");

if (!album || !album.fotos.length) {
  count.textContent = "Galeria em preparação.";
} else {
  const fotos = album.fotos;
  let mostradas = 0;

  count.textContent = `${fotos.length} fotos`;

  function render() {
    const ate = Math.min(mostradas + LOTE, fotos.length);
    const html = fotos.slice(mostradas, ate).map((id, i) => `
      <button class="gal__tile" data-i="${mostradas + i}" type="button"
        aria-label="Abrir foto ${mostradas + i + 1} de ${fotos.length}">
        <img src="${thumbURL(id)}" alt="${album.titulo}, foto ${mostradas + i + 1}"
          loading="lazy" decoding="async" referrerpolicy="no-referrer">
      </button>`).join("");
    grid.insertAdjacentHTML("beforeend", html);
    mostradas = ate;
    more.hidden = mostradas >= fotos.length;
    more.textContent = `Carregar mais ${Math.min(LOTE, fotos.length - mostradas)} fotos`;
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

  const preload = src => { semReferer(new Image()).src = src; };
  lbImg.referrerPolicy = "no-referrer";

  function show() {
    lbCount.textContent = `${idx + 1} / ${fotos.length}`;
    lbImg.style.opacity = 0;
    setTimeout(() => {
      const im = semReferer(new Image());
      im.onload = () => { lbImg.src = im.src; requestAnimationFrame(() => (lbImg.style.opacity = 1)); };
      im.src = fullURL(fotos[idx]);
    }, 200);
    preload(fullURL(fotos[(idx + 1) % fotos.length]));
    preload(fullURL(fotos[(idx - 1 + fotos.length) % fotos.length]));
  }
  function open(i) {
    idx = i; show();
    lb.classList.add("is-open");
    lb.setAttribute("aria-hidden", "false");
    document.body.style.overflow = "hidden";
  }
  function close() {
    lb.classList.remove("is-open");
    lb.setAttribute("aria-hidden", "true");
    document.body.style.overflow = "";
  }
  const step = d => { idx = (idx + d + fotos.length) % fotos.length; show(); };

  grid.addEventListener("click", (e) => {
    const tile = e.target.closest(".gal__tile");
    if (tile) open(Number(tile.dataset.i));
  });
  $("#lbClose").addEventListener("click", close);
  $("#lbPrev").addEventListener("click", () => step(-1));
  $("#lbNext").addEventListener("click", () => step(1));
  lb.addEventListener("click", (e) => {
    if (e.target === lb || e.target === lbImg.parentElement) close();
  });
  addEventListener("keydown", (e) => {
    if (!lb.classList.contains("is-open")) return;
    if (e.key === "Escape") close();
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

/* ── filme do álbum (YouTube, no lightbox de vídeo) ── */
const filme = $(".galfilme"), vlb = $("#vlb"), vlbFrame = $("#vlbFrame");
if (filme && vlb) {
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
const nav = $("#nav");
addEventListener("scroll", () => nav.classList.toggle("is-scrolled", scrollY > 40), { passive: true });
$("#burger").addEventListener("click", () => {
  const open = nav.classList.toggle("is-open");
  document.body.style.overflow = open ? "hidden" : "";
});
const root = document.documentElement;
$("#themeToggle").addEventListener("click", () => {
  const next = root.getAttribute("data-theme") === "dark" ? "light" : "dark";
  root.setAttribute("data-theme", next);
  try { localStorage.setItem("filmora-theme", next); } catch (e) {}
  document.querySelector('meta[name="theme-color"]')
    ?.setAttribute("content", next === "dark" ? "#110f0c" : "#f7f4ef");
});
