function escapeHtml(text) {
  const div = document.createElement("div");
  div.textContent = String(text ?? "");
  return div.innerHTML;
}

// eslint-disable-next-line no-unused-vars
export function showToast(message, type = "info") {
  const container = document.getElementById("toast-container");
  if (!container) return;

  const typeMap = {
    success: "success",
    error: "error",
    danger: "error",
    warning: "warning",
    info: "info",
    debug: "info",
  };
  const toastType = typeMap[type] || "info";

  const toast = document.createElement("div");
  toast.className = `toast-custom toast-${toastType}`;

  const icons = {
    success: '<i class="fas fa-check-circle"></i>',
    error: '<i class="fas fa-exclamation-circle"></i>',
    warning: '<i class="fas fa-exclamation-triangle"></i>',
    info: '<i class="fas fa-info-circle"></i>',
  };

  toast.innerHTML = `
    <div class="toast-icon">${icons[toastType]}</div>
    <div class="toast-content">
      <p class="toast-message">${escapeHtml(message)}</p>
    </div>
    <button class="toast-close" aria-label="Cerrar">
      <i class="fas fa-times"></i>
    </button>
    <div class="toast-progress"></div>
  `;

  container.appendChild(toast);

  const closeToast = () => {
    toast.classList.add("hiding");
    window.setTimeout(() => {
      toast.remove();
    }, 300);
  };

  const closeBtn = toast.querySelector(".toast-close");
  if (closeBtn) closeBtn.addEventListener("click", closeToast);

  let autoCloseTimeout = window.setTimeout(closeToast, 3000);
  toast.addEventListener("mouseenter", () => {
    window.clearTimeout(autoCloseTimeout);
    const progressBar = toast.querySelector(".toast-progress");
    if (progressBar) progressBar.style.animationPlayState = "paused";
  });
  toast.addEventListener("mouseleave", () => {
    const progressBar = toast.querySelector(".toast-progress");
    if (progressBar) progressBar.style.animationPlayState = "running";
    autoCloseTimeout = window.setTimeout(closeToast, 1000);
  });
}

