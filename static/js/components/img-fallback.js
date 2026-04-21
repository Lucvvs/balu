/**
 * Imágenes con respaldo: data-fallback-src apunta al reemplazo (p. ej. placeholder).
 * Si no hay fallback o ya se usó, oculta la imagen.
 */
export function initImageFallback(root = document) {
  root.querySelectorAll("img.js-img-fallback").forEach((img) => {
    img.addEventListener("error", function onErr() {
      const fallback = this.getAttribute("data-fallback-src");
      if (fallback && this.src !== fallback) {
        this.src = fallback;
      } else {
        this.style.display = "none";
      }
    });
  });
}

/** Tras error: oculta la imagen y muestra el siguiente hermano (p. ej. icono de respaldo). */
export function initImageFallbackRevealNext(root = document) {
  root.querySelectorAll("img.js-img-fallback-reveal-next").forEach((img) => {
    img.addEventListener("error", () => {
      img.classList.add("d-none");
      const next = img.nextElementSibling;
      if (!next) return;
      next.classList.remove("d-none");
      if (next.tagName === "DIV") {
        next.classList.add("d-flex");
      }
    });
  });
}
