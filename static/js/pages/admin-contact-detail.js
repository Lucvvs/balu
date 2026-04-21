/**
 * Detalle mensaje contacto (admin_contact_detail.html).
 */
import { initConfirmSubmits } from "../components/confirm-submit.js";

function readPageData() {
  const el = document.getElementById("admin-contact-detail-page-data");
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

function initAdminContactDetailPage() {
  const data = readPageData();
  if (!data || data.page !== "admin-contact-detail") return;
  initConfirmSubmits();
}

onReady(initAdminContactDetailPage);
