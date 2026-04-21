/**
 * Carrusel automático de imágenes dentro de cada tarjeta de oferta (flip).
 */
export function initOfferImageRotation() {
  const offerCards = document.querySelectorAll(".offer-card");

  offerCards.forEach((card, index) => {
    const imageContainer = card.querySelector(".offer-image-container");
    if (!imageContainer) return;

    const images = imageContainer.querySelectorAll(".offer-product-img");
    if (images.length <= 1) return;

    let currentImageIndex = 0;
    const delay = (index + 1) * 2000;

    function changeToNextImage() {
      const currentImg = images[currentImageIndex];
      currentImg.classList.remove("active", "flip-in");
      currentImg.classList.add("flip-out");

      currentImageIndex = (currentImageIndex + 1) % images.length;

      setTimeout(() => {
        currentImg.classList.remove("flip-out");
        const nextImg = images[currentImageIndex];
        nextImg.classList.remove("flip-out");
        nextImg.classList.add("flip-in", "active");

        setTimeout(() => {
          images.forEach((img) => {
            img.classList.remove("flip-in", "flip-out");
            if (img !== nextImg) {
              img.classList.remove("active");
            }
          });
        }, 600);
      }, 50);
    }

    setTimeout(() => {
      changeToNextImage();
      setInterval(changeToNextImage, 6000);
    }, delay);
  });
}
