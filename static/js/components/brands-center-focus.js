/**
 * En viewport ≤768px, resalta la marca cuyo centro está más cerca del centro de pantalla.
 */
export function initBrandsCenterFocus() {
  const mq = window.matchMedia("(max-width: 768px)");
  const banner = document.querySelector(".brands-banner");
  const scrollEl = document.querySelector(".brands-scroll");
  if (!banner || !scrollEl) return;

  let rafId = null;

  function cleanup() {
    banner.classList.remove("brands-center-focus");
    scrollEl.querySelectorAll(".brand-logo-link.is-near-center").forEach((el) => {
      el.classList.remove("is-near-center");
    });
  }

  function tick() {
    if (!mq.matches) {
      rafId = null;
      cleanup();
      return;
    }

    banner.classList.add("brands-center-focus");
    const links = scrollEl.querySelectorAll(".brand-logo-link");
    const cx = window.innerWidth / 2;
    let best = null;
    let bestDist = Infinity;

    links.forEach((link) => {
      const r = link.getBoundingClientRect();
      const mid = r.left + r.width / 2;
      const d = Math.abs(mid - cx);
      if (d < bestDist) {
        bestDist = d;
        best = link;
      }
    });

    links.forEach((link) => {
      link.classList.toggle("is-near-center", link === best);
    });

    rafId = requestAnimationFrame(tick);
  }

  function start() {
    if (rafId !== null) {
      cancelAnimationFrame(rafId);
      rafId = null;
    }
    if (!mq.matches) {
      cleanup();
      return;
    }
    rafId = requestAnimationFrame(tick);
  }

  function onResize() {
    start();
  }

  mq.addEventListener("change", start);
  window.addEventListener("resize", onResize);
  window.addEventListener("orientationchange", onResize);
  start();
}
