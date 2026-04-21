import { initNavbarScroll } from "./navbar-scroll.js";
import { initUserDropdownHover } from "./dropdown-hover.js";
import { showDjangoMessagesAsToasts } from "./messages-to-toasts.js";
import { showToast } from "./toast.js";

function onReady(fn) {
  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", fn);
  } else {
    fn();
  }
}

onReady(() => {
  initNavbarScroll();
  initUserDropdownHover();
  showDjangoMessagesAsToasts();
});

// Back-compat: templates call showToast(...) directly
window.showToast = showToast;

