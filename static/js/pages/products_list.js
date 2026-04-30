/**
 * Listado de productos (products_list.html).
 */
import { initImageFallback } from "../components/img-fallback.js";
import { initSizeVariantModal } from "../components/size-variant-modal.js";
import { initCatalogProductCards } from "../components/catalog-product-cards.js";

function readPageData() {
  const el = document.getElementById("products-list-page-data");
  if (!el) return null;
  try {
    return JSON.parse(el.textContent || "{}");
  } catch {
    return null;
  }
}

function selectCategory(categorySlug, productsListUrl) {
  const urlParams = new URLSearchParams(window.location.search);
  const fromCategory = urlParams.get("category");
  const fromLegacy = urlParams.get("categories");
  const effective = (fromCategory || (fromLegacy ? fromLegacy.split(",")[0].trim() : "")) || "";

  if (effective === categorySlug) {
    urlParams.delete("category");
  } else {
    urlParams.set("category", categorySlug);
  }
  urlParams.delete("categories");
  urlParams.delete("page");

  const qs = urlParams.toString();
  const base = productsListUrl || "/";
  window.location.href = qs ? `${base}?${qs}` : base;
}

function updateSort(url) {
  if (url) {
    window.location.href = url;
  }
}

function resetAllFilters(productsListUrl) {
  window.location.href = productsListUrl || "/";
}

function initFilterCategories(productsListUrl) {
  document.querySelector(".filter-categories")?.addEventListener("click", (e) => {
    const link = e.target.closest("a[data-category-slug]");
    if (!link) return;
    e.preventDefault();
    selectCategory(link.getAttribute("data-category-slug") || "", productsListUrl);
  });
}

function initSortSelect() {
  const sel = document.querySelector(".js-sort-select");
  if (!sel) return;
  sel.addEventListener("change", () => updateSort(sel.value));
}

function initResetFilters(productsListUrl) {
  const icon = document.querySelector(".js-reset-filters");
  if (!icon) return;
  icon.addEventListener("click", () => {
    resetAllFilters(productsListUrl);
  });
  icon.addEventListener("keydown", (e) => {
    if (e.key === "Enter" || e.key === " ") {
      e.preventDefault();
      resetAllFilters(productsListUrl);
    }
  });
}

function initFilterButtonsReveal() {
  document.querySelectorAll(".filter-categories .filter-btn").forEach((btn, index) => {
    setTimeout(() => {
      btn.classList.add("is-filter-revealed");
    }, index * 50);
  });
}

function initActionStopPropagation() {
  document.querySelectorAll(".js-stop-propagation").forEach((el) => {
    el.addEventListener("click", (e) => {
      e.stopPropagation();
    });
  });
}

function applyVariantSeparators() {
  document.querySelectorAll(".variant-badges").forEach((wrap) => {
    // Limpieza para recalcular idempotente
    wrap.querySelectorAll(".variant-badge-sep").forEach((n) => n.remove());

    const badges = [...wrap.querySelectorAll(".variant-badge")];
    if (badges.length <= 1) return;

    const firstTop = badges[0].offsetTop;
    const inOneRow = badges.every((b) => b.offsetTop === firstTop);
    if (!inOneRow) return;

    // Insertar separadores entre todos los badges
    for (let i = 0; i < badges.length - 1; i += 1) {
      const sep = document.createElement("span");
      sep.className = "variant-badge-sep";
      sep.textContent = "-";
      sep.setAttribute("aria-hidden", "true");
      badges[i].insertAdjacentElement("afterend", sep);
    }
  });
}

function initVariantSeparators() {
  // Esperar a layout final (fuentes/imágenes) antes de medir wrap
  const schedule = () => {
    window.requestAnimationFrame(() => window.requestAnimationFrame(applyVariantSeparators));
  };

  schedule();

  let t = null;
  window.addEventListener("resize", () => {
    if (t) window.clearTimeout(t);
    t = window.setTimeout(schedule, 120);
  });
}

function onReady(fn) {
  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", fn);
  } else {
    fn();
  }
}

function initProductsListPage() {
  const data = readPageData();
  if (!data || data.page !== "products-list") return;

  const productsListUrl = data.productsListUrl || "";

  initFilterButtonsReveal();
  initFilterCategories(productsListUrl);
  initSortSelect();
  initResetFilters(productsListUrl);
  initImageFallback();
  initActionStopPropagation();
  initSizeVariantModal(data);
  initCatalogProductCards();
  initVariantSeparators();
}

onReady(initProductsListPage);
