/**
 * Zoom al mover el mouse sobre la imagen principal (solo ancho > umbral).
 * Los handlers comprueban el ancho en cada interacción para adaptarse al resize sin duplicar listeners.
 */
export function initProductImageZoom(options = {}) {
  const desktopMinWidth = options.desktopMinWidth ?? 768;
  const zoomWrapper = document.querySelector(".product-image-zoom-wrapper");
  const mainImage = document.getElementById("main-product-image");
  if (!zoomWrapper || !mainImage) return;

  let isZooming = false;

  zoomWrapper.addEventListener("mouseenter", function () {
    if (window.innerWidth <= desktopMinWidth) return;
    isZooming = true;
    zoomWrapper.classList.add("zoom-active");
  });

  zoomWrapper.addEventListener("mouseleave", function () {
    isZooming = false;
    zoomWrapper.classList.remove("zoom-active");
    mainImage.style.transform = "scale(1)";
    mainImage.style.transformOrigin = "center center";
  });

  zoomWrapper.addEventListener("mousemove", function (e) {
    if (!isZooming || window.innerWidth <= desktopMinWidth) return;

    const rect = zoomWrapper.getBoundingClientRect();
    const x = e.clientX - rect.left;
    const y = e.clientY - rect.top;
    const xPercent = (x / rect.width) * 100;
    const yPercent = (y / rect.height) * 100;

    mainImage.style.transformOrigin = `${xPercent}% ${yPercent}%`;
    mainImage.style.transform = "scale(2)";
  });
}
