/**
 * Confirmación de pedido (order_confirmation.html): ilustración de progreso + formulario staff.
 */
import { initImageFallbackRevealNext } from "../components/img-fallback.js";

function readPageData() {
  const el = document.getElementById("order-confirmation-page-data");
  if (!el) return null;
  try {
    return JSON.parse(el.textContent || "{}");
  } catch {
    return null;
  }
}

function initStaffStatusForm(staff) {
  const form = document.getElementById("statusChangeForm");
  const select = document.getElementById("orderStatusSelect");
  if (!form || !select || !staff) return;

  const { orderId, currentStatusDisplay } = staff;

  form.addEventListener("submit", (e) => {
    const newStatus = select.options[select.selectedIndex].text;
    if (currentStatusDisplay === newStatus) {
      e.preventDefault();
      window.alert("El estado seleccionado es el mismo que el actual.");
      return;
    }
    if (
      !window.confirm(
        `¿Cambiar el pedido #${orderId} de "${currentStatusDisplay}" a "${newStatus}"?`
      )
    ) {
      e.preventDefault();
    }
  });
}

function onReady(fn) {
  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", fn);
  } else {
    fn();
  }
}

function initOrderConfirmationPage() {
  const data = readPageData();
  if (!data || data.page !== "order-confirmation") return;

  initImageFallbackRevealNext();
  initStaffStatusForm(data.staff);
}

onReady(initOrderConfirmationPage);
