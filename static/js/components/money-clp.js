/**
 * Formato y parseo de montos CLP (reutilizable en carrito, checkout, etc.).
 */
export function formatMoneyClp(n) {
  const num = Number(n);
  if (Number.isNaN(num)) return "$0";
  return new Intl.NumberFormat("es-CL", {
    style: "currency",
    currency: "CLP",
    minimumFractionDigits: 0,
  })
    .format(num)
    .replace("CLP", "$");
}

/** Extrae entero CLP desde strings tipo "$12.345" o "12.345" */
export function parseClpString(s) {
  if (s == null || s === "") return 0;
  const digits = String(s).replace(/[^\d]/g, "");
  return parseInt(digits, 10) || 0;
}
