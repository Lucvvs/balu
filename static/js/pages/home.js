/**
 * Página inicio (home.html).
 * Config: #home-page-data (application/json).
 */
import { initImageFallback } from "../components/img-fallback.js";
import { initSizeVariantModal } from "../components/size-variant-modal.js";
import { initOfferImageRotation } from "../components/offer-image-rotation.js";
import { initBestSellerCarousels } from "../components/best-seller-carousel.js";
import { initBrandsCenterFocus } from "../components/brands-center-focus.js";
import { initHomePromoModal } from "../components/home-promo-modal.js";

function readHomePageData() {
  const el = document.getElementById("home-page-data");
  if (!el) return null;
  try {
    return JSON.parse(el.textContent || "{}");
  } catch {
    return null;
  }
}

function onReady(fn) {
  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", fn);
  } else {
    fn();
  }
}

function initActionStopPropagation() {
  document.querySelectorAll(".js-stop-propagation").forEach((el) => {
    el.addEventListener("click", (e) => {
      e.stopPropagation();
    });
  });
}

function initHeroTitleMoto() {
  const hero = document.querySelector(".home-hero");
  const track = hero?.querySelector(".hero-title-track");
  const title = track?.querySelector(".masked-text");
  const moto = hero?.querySelector(".hero-title-moto");
  if (!hero || !track || !title || !moto) return;
  if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) return;

  const durationMs = 4000;
  let runId = 0;
  let currentAnim = null;
  let restartTimer = 0;

  function lineMids() {
    const heroRect = hero.getBoundingClientRect();
    const range = document.createRange();
    range.selectNodeContents(title);
    const raw = Array.from(range.getClientRects()).filter((r) => r.width > 1 && r.height > 1);

    const merged = [];
    raw.forEach((r) => {
      const last = merged[merged.length - 1];
      if (last && Math.abs(last.top - r.top) < 4) {
        last.bottom = Math.max(last.bottom, r.bottom);
      } else {
        merged.push({ top: r.top, bottom: r.bottom });
      }
    });

    if (merged.length < 2) {
      const cs = window.getComputedStyle(title);
      const fontSize = parseFloat(cs.fontSize) || 16;
      const lineHeight = Number.parseFloat(cs.lineHeight) || fontSize * 1.3;
      const padTop = parseFloat(cs.paddingTop) || 0;
      const padBottom = parseFloat(cs.paddingBottom) || 0;
      const contentH = title.clientHeight - padTop - padBottom;
      const estimated = Math.max(1, Math.round(contentH / lineHeight));
      if (estimated >= 2) {
        const titleRect = title.getBoundingClientRect();
        const top0 = titleRect.top + padTop;
        merged.length = 0;
        for (let i = 0; i < estimated; i += 1) {
          merged.push({
            top: top0 + i * lineHeight,
            bottom: top0 + (i + 1) * lineHeight,
          });
        }
      }
    }

    if (!merged.length) {
      const titleRect = title.getBoundingClientRect();
      merged.push({ top: titleRect.top, bottom: titleRect.bottom });
    }

    return merged.map((r) => (r.top + r.bottom) / 2 - heroRect.top);
  }

  function framesForLine(midY, rtl, width) {
    if (rtl) {
      return [
        { left: `${width}px`, top: `${midY}px`, transform: "translate(0, -50%) scaleX(-1)" },
        { left: "0px", top: `${midY}px`, transform: "translate(-100%, -50%) scaleX(-1)" },
      ];
    }
    return [
      { left: "0px", top: `${midY}px`, transform: "translate(-100%, -50%) scaleX(1)" },
      { left: `${width}px`, top: `${midY}px`, transform: "translate(0, -50%) scaleX(1)" },
    ];
  }

  async function play() {
    const id = ++runId;
    currentAnim?.cancel();
    moto.style.animation = "none";

    const mids = lineMids();
    const width = hero.clientWidth;
    if (!mids.length) return;

    while (id === runId) {
      for (let i = 0; i < mids.length; i += 1) {
        if (id !== runId) return;
        currentAnim = moto.animate(framesForLine(mids[i], i % 2 === 1, width), {
          duration: durationMs,
          easing: "ease-out",
          fill: "forwards",
        });
        try {
          await currentAnim.finished;
        } catch {
          return;
        }
      }
    }
  }

  function restart() {
    window.clearTimeout(restartTimer);
    restartTimer = window.setTimeout(() => {
      window.requestAnimationFrame(() => play());
    }, 80);
  }

  if (document.fonts?.ready) {
    document.fonts.ready.then(restart);
  } else {
    restart();
  }

  const observer = new ResizeObserver(restart);
  observer.observe(hero);
  observer.observe(title);
}

function initHomePage() {
  const data = readHomePageData();
  if (!data || data.page !== "home") return;

  initImageFallback();
  initSizeVariantModal(data);
  initActionStopPropagation();
  initOfferImageRotation();
  initBestSellerCarousels();
  initBrandsCenterFocus();
  initHomePromoModal(data);
  initHeroTitleMoto();
}

onReady(initHomePage);
