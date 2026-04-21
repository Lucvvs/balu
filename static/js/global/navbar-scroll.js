export function initNavbarScroll() {
  const navbar = document.querySelector(".navbar-motomoto");
  const body = document.body;
  if (!navbar || !body) return;

  let compact = false;
  const ENTER = 72;
  const EXIT = 20;

  function syncNavbarScroll() {
    const y = window.scrollY || window.pageYOffset;
    if (!compact && y > ENTER) {
      compact = true;
      navbar.classList.add("scrolled");
      body.classList.add("navbar-scrolled");
    } else if (compact && y < EXIT) {
      compact = false;
      navbar.classList.remove("scrolled");
      body.classList.remove("navbar-scrolled");
    }
  }

  window.addEventListener("scroll", syncNavbarScroll, { passive: true });
  syncNavbarScroll();
}

