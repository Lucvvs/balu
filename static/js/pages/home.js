/**
 * Página inicio (home.html).
 * Config: #home-page-data (application/json).
 */
import { initImageFallback } from "../components/img-fallback.js";
import { initSizeVariantModal } from "../components/size-variant-modal.js";
import { initOfferImageRotation } from "../components/offer-image-rotation.js";
import { initBestSellerCarousels } from "../components/best-seller-carousel.js";
import { initBrandsCenterFocus } from "../components/brands-center-focus.js";

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

function initHomePage() {
  const data = readHomePageData();
  if (!data || data.page !== "home") return;

  initImageFallback();
  initSizeVariantModal(data);
  initActionStopPropagation();
  initOfferImageRotation();
  initBestSellerCarousels();
  initBrandsCenterFocus();
}

onReady(initHomePage);
