/**
 * Envío automático del formulario POST de django-allauth (Google OAuth interstitial).
 */
function readPageData() {
  const el = document.getElementById("socialaccount-oauth-page-data");
  if (!el) return null;
  try {
    return JSON.parse(el.textContent || "{}");
  } catch {
    return null;
  }
}

function onReady(fn) {
  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", fn);
  } else {
    fn();
  }
}

function initSocialaccountOauthRedirect() {
  const data = readPageData();
  if (!data || data.page !== "socialaccount-oauth-redirect") return;

  const form = document.querySelector("form[data-auto-submit-on-load]");
  if (form) {
    form.submit();
  }
}

onReady(initSocialaccountOauthRedirect);
