/** Formularios que piden confirmación nativa antes de enviar. */
export function initConfirmSubmits(root = document) {
  root.querySelectorAll("form.js-confirm-submit").forEach((form) => {
    form.addEventListener("submit", function (e) {
      const msg = form.getAttribute("data-confirm-message") || "¿Confirmar?";
      if (!window.confirm(msg)) {
        e.preventDefault();
      }
    });
  });
}
