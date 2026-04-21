/**
 * Ficha de producto (product_detail.html).
 */
import { initImageFallback } from "../components/img-fallback.js";
import { initProductImageZoom } from "../components/product-image-zoom.js";

function readPageData() {
  const el = document.getElementById("product-detail-page-data");
  if (!el) return null;
  try {
    return JSON.parse(el.textContent || "{}");
  } catch {
    return null;
  }
}

function isTypingTarget(el) {
  if (!el || !el.closest) return false;
  const t = el.closest("input, textarea, select, [contenteditable='true']");
  return Boolean(t);
}

function initProductGallery() {
  const main = document.getElementById("main-product-image");
  const thumbs = [...document.querySelectorAll(".product-thumbnail")];
  if (!main || thumbs.length === 0) return;

  const images = thumbs.map((t) => t.src);
  const activeIdx = thumbs.findIndex((t) => t.classList.contains("active"));
  let currentImageIndex = activeIdx >= 0 ? activeIdx : 0;

  function setActiveThumbnail(active) {
    thumbs.forEach((thumb) => {
      thumb.classList.toggle("active", thumb === active);
    });
  }

  function changeMainImage(imageUrl, thumbnail) {
    main.src = imageUrl;
    thumbs.forEach((t) => t.classList.remove("active"));
    if (thumbnail) {
      thumbnail.classList.add("active");
      const idx = thumbs.indexOf(thumbnail);
      if (idx >= 0) currentImageIndex = idx;
    } else {
      currentImageIndex = images.indexOf(imageUrl);
      if (currentImageIndex < 0) currentImageIndex = 0;
    }
  }

  function nextImage() {
    currentImageIndex = (currentImageIndex + 1) % images.length;
    changeMainImage(images[currentImageIndex], thumbs[currentImageIndex]);
  }

  function previousImage() {
    currentImageIndex = (currentImageIndex - 1 + images.length) % images.length;
    changeMainImage(images[currentImageIndex], thumbs[currentImageIndex]);
  }

  document.querySelector(".js-product-gallery-prev")?.addEventListener("click", () => {
    previousImage();
  });
  document.querySelector(".js-product-gallery-next")?.addEventListener("click", () => {
    nextImage();
  });

  document.querySelector(".thumbnails-container")?.addEventListener("click", (e) => {
    const thumb = e.target.closest(".product-thumbnail");
    if (!thumb || !thumbs.includes(thumb)) return;
    changeMainImage(thumb.src, thumb);
  });

  document.addEventListener("keydown", function (e) {
    if (images.length <= 1) return;
    if (isTypingTarget(e.target)) return;
    if (e.key === "ArrowLeft") {
      e.preventDefault();
      previousImage();
    } else if (e.key === "ArrowRight") {
      e.preventDefault();
      nextImage();
    }
  });
}

function initVariantQuantityCap() {
  const sel = document.getElementById("id_variant");
  const qty = document.getElementById("id_quantity");
  if (!sel || !qty) return;

  function apply() {
    const opt = sel.options[sel.selectedIndex];
    const capRaw =
      opt && opt.dataset && opt.dataset.stock != null && opt.dataset.stock !== ""
        ? parseInt(opt.dataset.stock, 10)
        : parseInt(qty.getAttribute("max"), 10);
    let cap = Number.isFinite(capRaw) ? capRaw : 1;
    if (cap < 1) cap = 1;
    qty.setAttribute("max", String(cap));
    const v = parseInt(qty.value, 10);
    if (Number.isFinite(v) && v > cap) qty.value = String(cap);
  }

  sel.addEventListener("change", apply);
  apply();
}

function onReady(fn) {
  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", fn);
  } else {
    fn();
  }
}

function initProductDetailPage() {
  const data = readPageData();
  if (!data || data.page !== "product_detail") return;

  initImageFallback();
  initProductImageZoom();
  initProductGallery();
  initVariantQuantityCap();
}

onReady(initProductDetailPage);
