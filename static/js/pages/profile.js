/**
 * Perfil (profile.html): teléfono solo dígitos; nombres sin números.
 */
function readPageData() {
  const el = document.getElementById("profile-page-data");
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

function stripDigitsFromName(el) {
  if (!el) return;
  el.addEventListener("input", function () {
    const s = this.value;
    const t = s.replace(/[0-9]/g, "");
    if (t !== s) this.value = t;
  });
}

function initProfilePage() {
  const data = readPageData();
  if (!data || data.page !== "profile") return;

  const form = document.getElementById("profile-form");
  if (!form) return;

  const phone = form.querySelector('input[name="phone"]');
  if (phone) {
    phone.addEventListener("input", function () {
      this.value = this.value.replace(/\D/g, "");
    });
  }

  stripDigitsFromName(form.querySelector('input[name="first_name"]'));
  stripDigitsFromName(form.querySelector('input[name="last_name"]'));
}

onReady(initProfilePage);
