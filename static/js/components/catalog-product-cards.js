/**
 * Tarjetas de catálogo: rotación de imágenes al hover y clic en la tarjeta → detalle.
 */
export function initCatalogProductCards() {
  const productCards = document.querySelectorAll(".product-card");
  const imageIntervals = new Map();

  productCards.forEach((card) => {
    const imageContainer = card.querySelector(".product-card-image-container");
    let intervalId = null;
    let timeoutId = null;
    let animCycle = 0;
    let resetCardImagesToFirst = null;

    if (imageContainer) {
      const images = imageContainer.querySelectorAll(".product-card-img");
      let currentIndex = 0;

      resetCardImagesToFirst = function () {
        currentIndex = 0;
        images.forEach((img, index) => {
          img.classList.remove("active", "flip-in", "flip-out");
          if (index === 0) {
            img.classList.add("active");
          }
        });
      };

      if (images.length > 1) {
        function nextImage() {
          const cycleAtStart = animCycle;
          const currentImg = images[currentIndex];
          currentImg.classList.remove("active", "flip-in");
          currentImg.classList.add("flip-out");

          currentIndex = (currentIndex + 1) % images.length;

          setTimeout(() => {
            if (cycleAtStart !== animCycle) return;
            currentImg.classList.remove("flip-out");
            const nextImg = images[currentIndex];
            nextImg.classList.remove("flip-out");
            nextImg.classList.add("flip-in", "active");

            setTimeout(() => {
              if (cycleAtStart !== animCycle) return;
              images.forEach((img) => {
                img.classList.remove("flip-in", "flip-out");
                if (img !== nextImg) {
                  img.classList.remove("active");
                }
              });
            }, 500);
          }, 50);
        }

        card.addEventListener("mouseenter", function () {
          const enterCycle = animCycle;
          timeoutId = setTimeout(() => {
            if (enterCycle !== animCycle) return;
            nextImage();
            intervalId = setInterval(nextImage, 2000);
            imageIntervals.set(card, intervalId);
          }, 300);
        });

        card.addEventListener("mouseleave", function () {
          animCycle += 1;
          if (timeoutId) {
            clearTimeout(timeoutId);
            timeoutId = null;
          }
          if (intervalId) {
            clearInterval(intervalId);
            intervalId = null;
            imageIntervals.delete(card);
          }
          resetCardImagesToFirst();
        });
      }
    }

    card.addEventListener(
      "click",
      function (e) {
        animCycle += 1;
        if (timeoutId) {
          clearTimeout(timeoutId);
          timeoutId = null;
        }
        const currentCard = e.currentTarget;
        if (imageIntervals.has(currentCard)) {
          clearInterval(imageIntervals.get(currentCard));
          imageIntervals.delete(currentCard);
        }
        if (intervalId) {
          clearInterval(intervalId);
          intervalId = null;
        }
        if (typeof resetCardImagesToFirst === "function") {
          resetCardImagesToFirst();
        }

        const clickedElement = e.target;
        const isInteractive = clickedElement.closest(
          "a, button, form, .btn, .offer-badge, .stock-alert-badge, input"
        );

        if (isInteractive) {
          if (clickedElement.closest("a, button")) {
            return true;
          }
          if (clickedElement.closest("form")) {
            return true;
          }
          return true;
        }

        const productUrl = currentCard.getAttribute("data-product-url");
        if (productUrl) {
          e.preventDefault();
          e.stopPropagation();
          window.location.href = productUrl;
          return false;
        }
      },
      true
    );
  });
}
