export function initUserDropdownHover() {
  const userDropdown = document.getElementById("userDropdown");
  if (!userDropdown) return;

  const dropdownMenu = userDropdown.nextElementSibling;
  if (!dropdownMenu || !dropdownMenu.classList.contains("dropdown-menu")) return;

  let openTimeout = null;
  let closeTimeout = null;
  const openDelay = 500;
  const closeDelay = 1000;

  function openDropdown() {
    const instance = bootstrap.Dropdown.getInstance(userDropdown);
    if (!instance) new bootstrap.Dropdown(userDropdown).show();
    else instance.show();
  }

  function closeDropdown() {
    const instance = bootstrap.Dropdown.getInstance(userDropdown);
    if (instance) instance.hide();
  }

  function clearTimeouts() {
    if (openTimeout) {
      clearTimeout(openTimeout);
      openTimeout = null;
    }
    if (closeTimeout) {
      clearTimeout(closeTimeout);
      closeTimeout = null;
    }
  }

  userDropdown.addEventListener("mouseenter", () => {
    clearTimeouts();
    if (!dropdownMenu.classList.contains("show")) {
      openTimeout = setTimeout(openDropdown, openDelay);
    }
  });

  userDropdown.addEventListener("mouseleave", () => {
    clearTimeouts();
    if (dropdownMenu.classList.contains("show")) {
      closeTimeout = setTimeout(closeDropdown, closeDelay);
    }
  });

  dropdownMenu.addEventListener("mouseenter", clearTimeouts);
  dropdownMenu.addEventListener("mouseleave", () => {
    clearTimeouts();
    closeTimeout = setTimeout(closeDropdown, closeDelay);
  });

  userDropdown.addEventListener("hidden.bs.dropdown", clearTimeouts);
  userDropdown.addEventListener("shown.bs.dropdown", () => {
    if (openTimeout) {
      clearTimeout(openTimeout);
      openTimeout = null;
    }
  });
}

