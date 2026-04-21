/**
 * Buscar pedido (search_order.html).
 */
import { initImageFallbackRevealNext } from "../components/img-fallback.js";

function readPageData() {
  const el = document.getElementById("search-order-page-data");
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

function initSearchOrderPage() {
  const data = readPageData();
  if (!data || data.page !== "search-order") return;
  initImageFallbackRevealNext();
}

onReady(initSearchOrderPage);
