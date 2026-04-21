/**
 * Dashboard administrativo (admin_dashboard.html).
 */
import { initConfirmSubmits } from "../components/confirm-submit.js";

function readPageData() {
  const el = document.getElementById("admin-dashboard-page-data");
  if (!el) return null;
  try {
    return JSON.parse(el.textContent || "{}");
  } catch {
    return null;
  }
}

function handleStatusChange(select) {
  const currentStatus = select.getAttribute("data-current-status");
  const selectedOption = select.options[select.selectedIndex];
  const newStatus = selectedOption.text;
  const orderId = select.getAttribute("data-order-id");
  const form = select.closest("form");

  if (!form || currentStatus === newStatus) {
    return;
  }

  if (
    window.confirm(
      `¿Estás seguro de cambiar el estado del pedido #${orderId} de "${currentStatus}" a "${newStatus}"?`
    )
  ) {
    form.submit();
  } else {
    const originalValue = Array.from(select.options).find((opt) => opt.text === currentStatus)?.value;
    if (originalValue) {
      select.value = originalValue;
    }
  }
}

function initOrderStatusSelects() {
  document.querySelectorAll(".js-order-status-select").forEach((sel) => {
    sel.addEventListener("change", () => handleStatusChange(sel));
  });
}

function onReady(fn) {
  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", fn);
  } else {
    fn();
  }
}

function initAdminDashboardPage() {
  const data = readPageData();
  if (!data || data.page !== "admin-dashboard") return;

  initOrderStatusSelects();
  initConfirmSubmits();
}

onReady(initAdminDashboardPage);
