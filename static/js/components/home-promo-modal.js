/**
 * Modal promocional de inicio (Instagram + cupón).
 * Config en home-page-data.promoModal.
 */

const STORAGE_KEY = "motomoto_home_promo_dismissed_at";

function daysToMs(days) {
  return Math.max(0, Number(days) || 0) * 24 * 60 * 60 * 1000;
}

function wasDismissedRecently(dismissDays) {
  const raw = localStorage.getItem(STORAGE_KEY);
  if (!raw) return false;
  const dismissedAt = Number(raw);
  if (!Number.isFinite(dismissedAt)) return false;
  return Date.now() - dismissedAt < daysToMs(dismissDays);
}

function rememberDismissal(shouldRemember) {
  if (!shouldRemember) return;
  localStorage.setItem(STORAGE_KEY, String(Date.now()));
}

function shouldRememberDismissal() {
  const rememberCheckbox = document.getElementById("homePromoModalRemember");
  return rememberCheckbox ? rememberCheckbox.checked : true;
}

function bindDismissHandlers(modalEl, modal) {
  modalEl.addEventListener("hidden.bs.modal", () => {
    rememberDismissal(shouldRememberDismissal());
  });

  modalEl.querySelectorAll(".home-promo-modal__instagram-link").forEach((link) => {
    link.addEventListener("click", () => {
      rememberDismissal(shouldRememberDismissal());
      modal.hide();
    });
  });
}

export function initHomePromoModal(pageData) {
  const config = pageData?.promoModal;
  if (!config?.enabled) return;

  const modalEl = document.getElementById("homePromoModal");
  if (!modalEl || typeof bootstrap === "undefined" || !bootstrap.Modal) return;

  if (wasDismissedRecently(config.dismissDays)) return;

  const delay = Math.max(0, Number(config.showDelayMs) || 0);
  const modal = new bootstrap.Modal(modalEl, { backdrop: true, keyboard: true });

  bindDismissHandlers(modalEl, modal);

  window.setTimeout(() => {
    if (!document.hidden) {
      modal.show();
    }
  }, delay);
}
