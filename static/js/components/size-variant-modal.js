/**
 * Modal talla/color + envío del formulario a add_to_cart.
 * Requiere Bootstrap 5 (bootstrap.Modal).
 * addToCartUrlTemplate: URL generada con product_id placeholder fijo (ver home-page-data).
 */
const ADD_TO_CART_PRODUCT_ID_PLACEHOLDER = "999999999";

function buildAddToCartUrl(template, productId) {
  return template.replace(ADD_TO_CART_PRODUCT_ID_PLACEHOLDER, String(productId));
}

function openSizeModal(button, urlTemplate) {
  const productId = button.getAttribute("data-product-id");
  const productName = button.getAttribute("data-product-name") || "";
  const raw = button.getAttribute("data-product-variants") || "[]";
  let items = [];
  try {
    items = JSON.parse(raw);
  } catch {
    items = [];
  }
  const modalEl = document.getElementById("sizeModal");
  if (!modalEl || typeof bootstrap === "undefined" || !bootstrap.Modal) return;

  const modal = new bootstrap.Modal(modalEl);
  const idInput = document.getElementById("modalProductId");
  const nameEl = document.getElementById("modalProductName");
  const sel = document.getElementById("modalVariantSelect");
  const form = document.getElementById("sizeModalForm");
  if (!idInput || !nameEl || !sel || !form) return;

  idInput.value = productId || "";
  nameEl.textContent = productName;
  sel.innerHTML = '<option value="">-- Seleccione una opción --</option>';
  items.forEach((row) => {
    const opt = document.createElement("option");
    opt.value = String(row.id);
    opt.textContent = row.name;
    opt.setAttribute("data-stock", String(row.stock));
    sel.appendChild(opt);
  });
  form.reset();
  idInput.value = productId || "";
  const qty = form.querySelector('input[name="quantity"]');
  if (qty) qty.value = "1";
  modal.show();
}

function submitSizeForm(urlTemplate) {
  const form = document.getElementById("sizeModalForm");
  const sel = document.getElementById("modalVariantSelect");
  const productId = document.getElementById("modalProductId")?.value;
  if (!form || !sel || !productId) return;
  if (!sel.value) {
    window.alert("Por favor, selecciona una talla/color antes de agregar al carrito.");
    sel.focus();
    return;
  }
  form.action = buildAddToCartUrl(urlTemplate || "", productId);
  form.submit();
}

export function initSizeVariantModal(pageData) {
  const modalEl = document.getElementById("sizeModal");
  if (!modalEl) return;

  const urlTemplate = pageData?.addToCartUrlTemplate || "";

  document.querySelectorAll(".js-open-size-modal").forEach((btn) => {
    btn.addEventListener("click", (e) => {
      e.stopPropagation();
      openSizeModal(btn, urlTemplate);
    });
  });

  document.getElementById("js-size-modal-submit")?.addEventListener("click", () => {
    submitSizeForm(urlTemplate);
  });
}
