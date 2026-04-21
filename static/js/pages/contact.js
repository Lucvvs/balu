/**
 * Contacto (contact.html): logos de canales con fallback.
 */
import { initImageFallback } from "../components/img-fallback.js";

function readPageData() {
  const el = document.getElementById("contact-page-data");
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

function initContactPage() {
  const data = readPageData();
  if (!data || data.page !== "contact") return;
  initImageFallback();
}

onReady(initContactPage);
