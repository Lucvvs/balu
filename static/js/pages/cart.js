/**
 * Página carrito + checkout (cart.html).
 * Config: lee #cart-page-data (application/json) emitido por Django.
 */
import { formatMoneyClp, parseClpString } from "../components/money-clp.js";
import { initImageFallback } from "../components/img-fallback.js";
import { initConfirmSubmits } from "../components/confirm-submit.js";

function readPageConfig() {
  const el = document.getElementById("cart-page-data");
  if (!el) return null;
  try {
    return JSON.parse(el.textContent || "{}");
  } catch {
    return null;
  }
}

function initQuantityControls() {
  document.querySelectorAll(".quantity-increase").forEach((button) => {
    button.addEventListener("click", function () {
      const itemId = this.getAttribute("data-item-id");
      const input = document.getElementById(`quantity-${itemId}`);
      const currentValue = parseInt(input.value, 10);
      const maxValue = parseInt(this.getAttribute("data-max-quantity"), 10);
      if (currentValue < maxValue) {
        input.value = String(currentValue + 1);
        updateCartItem(itemId, input.value);
      } else if (typeof window.showToast === "function") {
        window.showToast("No hay suficiente stock disponible.", "warning");
      }
    });
  });

  document.querySelectorAll(".quantity-decrease").forEach((button) => {
    button.addEventListener("click", function () {
      const itemId = this.getAttribute("data-item-id");
      const input = document.getElementById(`quantity-${itemId}`);
      const currentValue = parseInt(input.value, 10);
      if (currentValue > 1) {
        input.value = String(currentValue - 1);
        updateCartItem(itemId, input.value);
      }
    });
  });
}

function updateCartItem(itemId, quantity) {
  const form = document.getElementById(`quantity-form-${itemId}`);
  if (!form) return;
  const formData = new FormData(form);
  const itemTotalElement = document.getElementById(`item-total-${itemId}`);

  if (itemTotalElement) {
    itemTotalElement.innerHTML =
      '<span class="spinner-border spinner-border-sm cart-qty-spinner" role="status" aria-hidden="true"></span>';
  }

  const quantityButtons = form.querySelectorAll(".quantity-btn");
  quantityButtons.forEach((btn) => {
    btn.disabled = true;
  });

  fetch(form.action, {
    method: "POST",
    body: formData,
    headers: { "X-Requested-With": "XMLHttpRequest" },
  })
    .then((response) => {
      if (response.redirected) {
        window.location.href = response.url;
        return null;
      }
      const contentType = response.headers.get("content-type");
      if (contentType && contentType.includes("application/json")) {
        return response.json().then((data) => {
          if (data.error) {
            if (typeof window.showToast === "function") {
              window.showToast(data.error, "warning");
            }
            throw new Error(data.error);
          }
          return data;
        });
      }
      window.location.reload();
      return null;
    })
    .then((data) => {
      if (data) {
        if (data.deleted) {
          window.location.reload();
          return;
        }
        if (data.item_total && itemTotalElement) {
          itemTotalElement.textContent = data.item_total;
        }
        if (data.cart_subtotal) {
          const subtotalElement = document.querySelector(
            ".summary-row:first-of-type span:last-child"
          );
          const totalAmount = document.getElementById("total-amount");
          if (subtotalElement) subtotalElement.textContent = data.cart_subtotal;
          if (totalAmount) {
            const shippingRow = document.getElementById("shipping-row");
            let shippingCost = 0;
            if (shippingRow && !shippingRow.classList.contains("is-hidden")) {
              const shippingCostText = document.getElementById("shipping-cost").textContent;
              shippingCost = parseClpString(shippingCostText);
            }
            const subtotalValue = parseClpString(data.cart_subtotal);
            const discountRow = document.getElementById("discount-row");
            let discount = 0;
            if (discountRow && !discountRow.classList.contains("is-hidden")) {
              const discountText = document.getElementById("discount-amount").textContent;
              discount = parseClpString(discountText);
            }
            const newTotal = subtotalValue + shippingCost - discount;
            totalAmount.textContent = formatMoneyClp(newTotal);
          }
        }
      }
      quantityButtons.forEach((btn) => {
        btn.disabled = false;
      });
    })
    .catch((error) => {
      console.error("Error al actualizar item del carrito:", error);
      quantityButtons.forEach((btn) => {
        btn.disabled = false;
      });
      if (error.message && typeof window.showToast === "function") {
        window.showToast(error.message, "error");
      }
      window.location.reload();
    });
}

function getDomesticShippingCost(cfg) {
  if (!cfg || cfg.domesticId == null) return cfg ? cfg.priceOther : 5000;
  const regionEl = document.getElementById("shipping-region");
  const r = regionEl ? regionEl.value : "";
  if (!r) return cfg.priceOther;
  const rp = cfg.regionPrices || {};
  if (Object.prototype.hasOwnProperty.call(rp, r)) return rp[r];
  return cfg.priceOther;
}

function isDomesticShippingSelected(cfg) {
  if (!cfg || cfg.domesticId == null) return false;
  const sel = document.querySelector('input[name="shipping_method"]:checked');
  return !!(sel && String(sel.value) === String(cfg.domesticId));
}

function updateShippingCost(cfg, money, cost, opts) {
  opts = opts || {};
  const shippingRow = document.getElementById("shipping-row");
  const shippingCostEl = document.getElementById("shipping-cost");
  const totalAmount = document.getElementById("total-amount");
  if (!shippingRow || !shippingCostEl || !totalAmount) return;

  if (opts.skipFieldReset && isDomesticShippingSelected(cfg)) {
    const c = getDomesticShippingCost(cfg);
    shippingRow.classList.remove("is-hidden");
    shippingCostEl.textContent = formatMoneyClp(c);
    totalAmount.textContent = formatMoneyClp(money.subtotalClp + c - money.discountClp);
    return;
  }

  document.querySelectorAll('[id^="shipping-fields-"]').forEach((field) => {
    field.classList.add("is-hidden");
    const regionSelect = field.querySelector("#shipping-region");
    const comunaSelect = field.querySelector("#shipping-comuna");
    const addressTextarea = field.querySelector('textarea[name="shipping_address"]');
    const notesTextarea = field.querySelector('textarea[name="shipping_notes"]');

    if (regionSelect) {
      regionSelect.removeAttribute("required");
      regionSelect.value = "";
      const firstOption = regionSelect.querySelector('option[value=""]');
      if (firstOption) firstOption.disabled = false;
    }
    if (comunaSelect) {
      comunaSelect.removeAttribute("required");
      comunaSelect.innerHTML = '<option value="">Seleccione una comuna</option>';
    }
    if (addressTextarea) {
      addressTextarea.removeAttribute("required");
      addressTextarea.value = "";
    }
    if (notesTextarea) notesTextarea.value = "";
  });

  const selectedShipping = document.querySelector('input[name="shipping_method"]:checked');
  let resolved = cost;
  if (cfg && selectedShipping && String(selectedShipping.value) === String(cfg.domesticId)) {
    resolved = getDomesticShippingCost(cfg);
  }

  if (resolved > 0) {
    shippingRow.classList.remove("is-hidden");
    shippingCostEl.textContent = formatMoneyClp(resolved);

    if (selectedShipping) {
      const fieldsId = `shipping-fields-${selectedShipping.value}`;
      const fields = document.getElementById(fieldsId);
      if (fields) {
        fields.classList.remove("is-hidden");
        const regionSelect = fields.querySelector("#shipping-region");
        const comunaSelect = fields.querySelector("#shipping-comuna");
        const addressTextarea = fields.querySelector('textarea[name="shipping_address"]');
        if (regionSelect) {
          regionSelect.setAttribute("required", "required");
          const firstOption = regionSelect.querySelector('option[value=""]');
          if (firstOption) firstOption.disabled = true;
        }
        if (comunaSelect) {
          comunaSelect.setAttribute("required", "required");
          const firstComunaOption = comunaSelect.querySelector('option[value=""]');
          if (firstComunaOption) firstComunaOption.disabled = true;
        }
        if (addressTextarea) addressTextarea.setAttribute("required", "required");
      }
    }
  } else {
    shippingRow.classList.add("is-hidden");
  }

  totalAmount.textContent = formatMoneyClp(money.subtotalClp + resolved - money.discountClp);
}

function syncShippingFromMethodChange(cfg, money, radioInput) {
  const isDomestic = cfg && String(radioInput.value) === String(cfg.domesticId);
  if (isDomestic) {
    updateShippingCost(cfg, money, 0, {});
  } else {
    const shippingOption = radioInput.closest(".checkout-option");
    const costText = shippingOption ? shippingOption.textContent : "";
    const cost = costText.includes("Gratis")
      ? 0
      : parseClpString(costText.match(/\$[\d.]+/)?.[0] || "0");
    updateShippingCost(cfg, money, cost, {});
  }
  syncCashPaymentAvailability(cfg);
}

function isCashPaymentRadio(radio, cashPaymentId) {
  if (!radio) return false;
  if (cashPaymentId != null && String(radio.value) === String(cashPaymentId)) return true;
  const nameAttr = (radio.getAttribute("data-payment-name") || "").toLowerCase();
  if (nameAttr.includes("efectivo")) return true;
  const label = radio.closest(".checkout-option-payment");
  const nameEl = label ? label.querySelector(".payment-name") : null;
  const paymentName = nameEl ? nameEl.textContent.trim().toLowerCase() : "";
  return paymentName.includes("efectivo");
}

function syncCashPaymentAvailability(cfg) {
  const domestic = isDomesticShippingSelected(cfg);
  const cashId = cfg && cfg.cashPaymentId != null ? cfg.cashPaymentId : null;
  const alertEl = document.getElementById("domestic-payment-message");
  let selectedWasCash = false;

  document.querySelectorAll('input[name="payment_method"]').forEach((radio) => {
    const label = radio.closest(".checkout-option-payment");
    const isCash = isCashPaymentRadio(radio, cashId);
    if (!isCash) return;

    if (domestic) {
      if (radio.checked) selectedWasCash = true;
      radio.checked = false;
      radio.disabled = true;
      radio.removeAttribute("required");
      if (label) label.classList.add("is-disabled");
    } else {
      radio.disabled = false;
      if (label) label.classList.remove("is-disabled");
    }
  });

  if (alertEl) {
    alertEl.classList.toggle("is-hidden", !domestic);
  }

  if (domestic && selectedWasCash) {
    const firstAvailable = document.querySelector(
      'input[name="payment_method"]:not(:disabled)'
    );
    if (firstAvailable) {
      firstAvailable.checked = true;
      firstAvailable.dispatchEvent(new Event("change"));
    }
  }

  const enabled = document.querySelectorAll('input[name="payment_method"]:not(:disabled)');
  enabled.forEach((r, idx) => {
    if (idx === 0) r.setAttribute("required", "required");
    else r.removeAttribute("required");
  });
}

function initRegionComunas(comunasUrlBase, cfg, money) {
  const regionSelect = document.getElementById("shipping-region");
  const comunaSelect = document.getElementById("shipping-comuna");
  if (!regionSelect || !comunaSelect) return;

  regionSelect.addEventListener("change", function () {
    const region = this.value;
    if (isDomesticShippingSelected(cfg)) {
      updateShippingCost(cfg, money, 0, { skipFieldReset: true });
    }
    comunaSelect.innerHTML = '<option value="">Seleccione una comuna</option>';

    if (!region) return;
    const url = `${comunasUrlBase}?region=${encodeURIComponent(region)}`;
    fetch(url)
      .then((response) => response.json())
      .then((data) => {
        if (data.comunas && data.comunas.length > 0) {
          data.comunas.forEach((comuna) => {
            const option = document.createElement("option");
            option.value = comuna[0];
            option.textContent = comuna[1];
            comunaSelect.appendChild(option);
          });
        }
      })
      .catch((error) => {
        console.error("Error al cargar comunas:", error);
        if (typeof window.showToast === "function") {
          window.showToast(
            "Error al cargar las comunas. Por favor, intente nuevamente.",
            "error"
          );
        }
      });
  });
}

function initCheckoutValidation() {
  const checkoutForm = document.getElementById("checkout-form");
  if (!checkoutForm) return;

  checkoutForm.addEventListener("submit", function (e) {
    const selectedShipping = document.querySelector('input[name="shipping_method"]:checked');

    if (selectedShipping) {
      const shippingId = selectedShipping.value;
      const shippingFields = document.getElementById(`shipping-fields-${shippingId}`);

      if (shippingFields && !shippingFields.classList.contains("is-hidden")) {
        const regionSelect = shippingFields.querySelector("#shipping-region");
        const comunaSelect = shippingFields.querySelector("#shipping-comuna");
        const addressTextarea = shippingFields.querySelector('textarea[name="shipping_address"]');

        const errors = [];
        if (!regionSelect || !regionSelect.value || regionSelect.value === "") {
          errors.push("• Debe seleccionar una región");
        }
        if (!comunaSelect || !comunaSelect.value || comunaSelect.value === "") {
          errors.push("• Debe seleccionar una comuna");
        }
        if (!addressTextarea || !addressTextarea.value || addressTextarea.value.trim() === "") {
          errors.push("• Debe ingresar la dirección");
        }

        if (errors.length > 0) {
          e.preventDefault();
          if (typeof window.showToast === "function") {
            window.showToast(
              `Por favor complete los siguientes campos para envío a domicilio:\n\n${errors.join("\n")}`,
              "warning"
            );
          }
          return false;
        }
      }
    }

    const customerName = document.getElementById("customer_name");
    const customerEmail = document.getElementById("customer_email");

    if (customerName && (!customerName.value || customerName.value.trim() === "")) {
      e.preventDefault();
      if (typeof window.showToast === "function") {
        window.showToast("Debe ingresar su nombre completo", "warning");
      }
      return false;
    }

    if (customerEmail && (!customerEmail.value || customerEmail.value.trim() === "")) {
      e.preventDefault();
      if (typeof window.showToast === "function") {
        window.showToast("Debe ingresar su email", "warning");
      }
      return false;
    }

    if (customerEmail && customerEmail.value) {
      const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
      if (!emailRegex.test(customerEmail.value)) {
        e.preventDefault();
        if (typeof window.showToast === "function") {
          window.showToast("El email ingresado no es válido", "warning");
        }
        return false;
      }
    }
    return undefined;
  });
}

function initShippingCards(cfg, money) {
  function updateShippingMethodStyles() {
    document.querySelectorAll('.checkout-option-shipping input[type="radio"]').forEach((radio) => {
      const label = radio.closest(".checkout-option-shipping");
      if (!label) return;
      label.classList.toggle("selected", radio.checked);
    });
  }

  updateShippingMethodStyles();

  document.querySelectorAll('.checkout-option-shipping input[type="radio"]').forEach((radio) => {
    radio.addEventListener("change", function () {
      updateShippingMethodStyles();
      syncShippingFromMethodChange(cfg, money, this);
    });
  });

  document.querySelectorAll(".checkout-option-shipping").forEach((label) => {
    label.addEventListener("click", function (ev) {
      const input = label.querySelector('input[type="radio"]');
      if (!input) return;
      if (ev.target !== input) {
        input.checked = true;
        updateShippingMethodStyles();
        input.dispatchEvent(new Event("change"));
      }
    });
  });
}

function initPaymentCards(paymentNamesForMp, cfg) {
  const names = paymentNamesForMp || ["Tarjeta de Crédito", "Tarjeta de Débito"];

  function updatePaymentMethodStyles() {
    document.querySelectorAll('.checkout-option-payment input[type="radio"]').forEach((radio) => {
      const label = radio.closest(".checkout-option-payment");
      if (!label) return;
      label.classList.toggle("selected", radio.checked);
    });
  }

  function updateMercadoPagoMessage() {
    const mercadoPagoMessage = document.getElementById("mercado-pago-message");
    if (!mercadoPagoMessage) return;

    const selectedRadio = document.querySelector('input[name="payment_method"]:checked');
    if (selectedRadio) {
      const label = selectedRadio.closest(".checkout-option-payment");
      const nameEl = label ? label.querySelector(".payment-name") : null;
      const paymentName = nameEl ? nameEl.textContent.trim() : "";
      if (names.includes(paymentName)) {
        mercadoPagoMessage.classList.remove("is-hidden");
      } else {
        mercadoPagoMessage.classList.add("is-hidden");
      }
    } else {
      mercadoPagoMessage.classList.add("is-hidden");
    }
  }

  updatePaymentMethodStyles();

  document.querySelectorAll('.checkout-option-payment input[type="radio"]').forEach((radio) => {
    radio.addEventListener("change", () => {
      updatePaymentMethodStyles();
      updateMercadoPagoMessage();
    });
  });

  document.querySelectorAll(".checkout-option-payment").forEach((label) => {
    label.addEventListener("click", function (ev) {
      const radio = label.querySelector('input[type="radio"]');
      if (!radio || radio.disabled) {
        ev.preventDefault();
        return;
      }
      if (ev.target !== radio) {
        radio.checked = true;
        updatePaymentMethodStyles();
        updateMercadoPagoMessage();
      }
    });
  });

  syncCashPaymentAvailability(cfg);
  updateMercadoPagoMessage();
}

function initCartPage() {
  const data = readPageConfig();
  if (!data || !data.page || data.page !== "cart") return;

  const cfg = Object.assign({}, data.shipping || {}, {
    cashPaymentId: data.payment?.cashPaymentId ?? null,
  });
  const money = data.money || { subtotalClp: 0, discountClp: 0 };
  const comunasUrlBase = data.urls?.comunas || "";

  initQuantityControls();
  initImageFallback();
  initConfirmSubmits();

  const selectedShipping = document.querySelector('input[name="shipping_method"]:checked');
  if (selectedShipping) syncShippingFromMethodChange(cfg, money, selectedShipping);

  initRegionComunas(comunasUrlBase, cfg, money);
  initCheckoutValidation();
  initShippingCards(cfg, money);
  initPaymentCards(data.payment?.mercadoPagoNames, cfg);
}

if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", initCartPage);
} else {
  initCartPage();
}
