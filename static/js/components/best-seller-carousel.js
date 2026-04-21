/**
 * Carrusel principal + miniaturas en "Los más vendidos" (home).
 */
const carouselIndices = {};

function setCarouselImage(productId, index, imageUrl) {
  const mainImage = document.getElementById(`main-image-${productId}`);
  const thumbnails = document.querySelectorAll(`.carousel-thumb[data-product="${productId}"]`);

  if (!mainImage || !thumbnails.length) return;

  mainImage.style.opacity = "0";
  setTimeout(() => {
    mainImage.src = imageUrl;
    mainImage.style.opacity = "1";
  }, 150);

  thumbnails.forEach((thumb, idx) => {
    thumb.classList.toggle("active", idx === index);
  });

  carouselIndices[productId] = index;
}

function changeCarouselImage(productId, direction) {
  const thumbnails = document.querySelectorAll(`.carousel-thumb[data-product="${productId}"]`);
  if (!thumbnails.length) return;

  const currentIndex = carouselIndices[productId] || 0;
  let newIndex;
  if (direction > 0) {
    newIndex = (currentIndex + 1) % thumbnails.length;
  } else {
    newIndex = (currentIndex - 1 + thumbnails.length) % thumbnails.length;
  }

  setCarouselImage(productId, newIndex, thumbnails[newIndex].src);
}

export function initBestSellerCarousels() {
  const section = document.querySelector(".best-sellers-section");
  if (!section) return;

  section.querySelectorAll(".carousel-thumb").forEach((thumb) => {
    const productId = thumb.getAttribute("data-product");
    if (productId && carouselIndices[productId] === undefined) {
      carouselIndices[productId] = 0;
    }
  });

  section.addEventListener("click", (e) => {
    const arrow = e.target.closest(".carousel-arrow");
    if (arrow) {
      e.preventDefault();
      const productId = arrow.getAttribute("data-product");
      const dir = parseInt(arrow.getAttribute("data-direction") || "0", 10);
      if (productId && dir) {
        changeCarouselImage(productId, dir);
      }
      return;
    }

    const thumb = e.target.closest(".carousel-thumb");
    if (thumb) {
      const productId = thumb.getAttribute("data-product");
      const index = parseInt(thumb.getAttribute("data-index") || "0", 10);
      if (productId) {
        setCarouselImage(productId, index, thumb.src);
      }
    }
  });
}
