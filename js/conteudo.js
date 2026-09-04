/* ═══════════ filmora: página de produção de conteúdo ═══════════ */
const $ = (s, c = document) => c.querySelector(s);
const $$ = (s, c = document) => [...c.querySelectorAll(s)];

/* Cada recurso roda isolado: uma falha na grade não pode levar junto o menu
   e o player, que vêm depois. */
function protegido(nome, fn) {
  try { fn(); } catch (e) { console.error(`[filmora] ${nome}:`, e); }
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
protegido("nav", montarNav);

/* ── grade de peças verticais ── */
const PECAS = window.CONTEUDO || [];

function cardVideo(v, i) {
  return `
  <article class="vid" data-drive="${v.id}" style="transition-delay:${i * 0.06}s">
    <div class="vid__poster">
      <img src="${v.poster}" alt="${v.titulo}, produção de conteúdo filmora" loading="lazy">
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

function montarGrade() {
  const destaques = PECAS.filter(v => v.destaque);
  const demais = PECAS.filter(v => !v.destaque);
  $("#conteudoCount").textContent = `${PECAS.length} peças verticais`;
  $("#conteudoDestaques").innerHTML = destaques.map(cardVideo).join("");
  $("#conteudoGrid").innerHTML = demais.map(cardVideo).join("");
  /* sem destaque marcado, o rótulo do bloco ficaria sozinho na página */
  destaques.length || $("#conteudoDestaques").closest(".conteudo__bloco").remove();
  demais.length || $("#conteudoGrid").closest(".conteudo__bloco").remove();
}

/* ── player em moldura vertical ──
   Todo vídeo é servido pelo Drive; o site guarda só o pôster. */
function montarPlayer() {
  const vlb = $("#vlb"), frame = $("#vlbFrame");
  function abrir(card, rotulo) {
    const id = card.dataset.drive;
    frame.innerHTML =
      `<iframe src="https://drive.google.com/file/d/${id}/preview" title="${rotulo}, filmora"
        allow="autoplay; encrypted-media; fullscreen; picture-in-picture"
        referrerpolicy="strict-origin-when-cross-origin" allowfullscreen></iframe>
       <a class="vlb__fallback" href="https://drive.google.com/file/d/${id}/view"
          target="_blank" rel="noopener">Não carregou? Abrir em nova aba →</a>`;
    vlb.classList.add("is-open");
    vlb.setAttribute("aria-hidden", "false");
    document.body.style.overflow = "hidden";
  }
  function fechar() {
    vlb.classList.remove("is-open");
    vlb.setAttribute("aria-hidden", "true");
    frame.innerHTML = "";
    document.body.style.overflow = "";
  }
  document.addEventListener("click", (e) => {
    const card = e.target.closest("[data-drive]");
    if (card) abrir(card, card.querySelector(".vid__title")?.textContent || "Vídeo");
  });
  $("#vlbClose").addEventListener("click", fechar);
  vlb.addEventListener("click", (e) => { if (e.target === vlb) fechar(); });
  addEventListener("keydown", (e) => {
    if (e.key === "Escape" && vlb.classList.contains("is-open")) fechar();
  });
}

if (!PECAS.length) {
  $("#conteudoCount").textContent = "Peças em preparação.";
} else {
  protegido("grade", montarGrade);
  protegido("player", montarPlayer);
}
