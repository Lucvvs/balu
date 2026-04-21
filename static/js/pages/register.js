/**
 * Registro (register.html): fortaleza de contraseña, coincidencia, mostrar/ocultar.
 */
function readPageData() {
  const el = document.getElementById("register-page-data");
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

function initRegisterPage() {
  const data = readPageData();
  if (!data || data.page !== "register") return;

  const password1Input = document.querySelector("#id_password1");
  const password2Input = document.querySelector("#id_password2");

  document.querySelectorAll(".password-toggle-btn").forEach((btn) => {
    btn.addEventListener("click", function (e) {
      e.preventDefault();
      e.stopPropagation();
      const wrapper = this.closest(".password-input-wrapper");
      if (!wrapper) return;
      const input = wrapper.querySelector('input[type="password"], input[type="text"]');
      const icon = this.querySelector("i");
      if (!input || !icon) return;
      if (input.type === "password") {
        input.type = "text";
        icon.classList.remove("fa-eye");
        icon.classList.add("fa-eye-slash");
      } else {
        input.type = "password";
        icon.classList.remove("fa-eye-slash");
        icon.classList.add("fa-eye");
      }
    });
  });

  function validatePassword(password) {
    const requirements = {
      length: password.length >= 8,
      uppercase: /[A-Z]/.test(password),
      lowercase: /[a-z]/.test(password),
      number: /[0-9]/.test(password),
    };

    Object.keys(requirements).forEach((key) => {
      const item = document.querySelector(`[data-requirement="${key}"]`);
      if (!item) return;
      if (requirements[key]) {
        item.classList.add("valid");
      } else {
        item.classList.remove("valid");
      }
    });

    const validCount = Object.values(requirements).filter((v) => v).length;
    const strengthFill = document.getElementById("strength-fill");

    if (strengthFill) {
      strengthFill.classList.remove("weak", "fair", "good", "strong");

      if (validCount === 0) {
        strengthFill.style.width = "0%";
      } else if (validCount <= 1) {
        strengthFill.style.width = "25%";
        strengthFill.classList.add("weak");
      } else if (validCount === 2) {
        strengthFill.style.width = "50%";
        strengthFill.classList.add("fair");
      } else if (validCount === 3) {
        strengthFill.style.width = "75%";
        strengthFill.classList.add("good");
      } else {
        strengthFill.style.width = "100%";
        strengthFill.classList.add("strong");
      }
    }

    if (password1Input) {
      if (password.length > 0) {
        if (validCount >= 3) {
          password1Input.classList.add("valid");
          password1Input.classList.remove("invalid");
        } else {
          password1Input.classList.add("invalid");
          password1Input.classList.remove("valid");
        }
      } else {
        password1Input.classList.remove("valid", "invalid");
      }
    }

    return requirements;
  }

  function validatePasswordMatch() {
    if (!password1Input || !password2Input) return;

    const password1 = password1Input.value;
    const password2 = password2Input.value;
    const matchStatus = document.getElementById("password-match-status");

    if (!matchStatus) return;

    if (password2.length === 0) {
      matchStatus.classList.remove("valid", "invalid");
      const matchText = matchStatus.querySelector(".match-text");
      if (matchText) matchText.textContent = "Deben coincidir";
      password2Input.classList.remove("valid", "invalid");
      return;
    }

    if (password1 === password2 && password1.length > 0) {
      matchStatus.classList.add("valid");
      matchStatus.classList.remove("invalid");
      const matchText = matchStatus.querySelector(".match-text");
      if (matchText) matchText.textContent = "Coinciden";
      password2Input.classList.add("valid");
      password2Input.classList.remove("invalid");
    } else {
      matchStatus.classList.add("invalid");
      matchStatus.classList.remove("valid");
      const matchText = matchStatus.querySelector(".match-text");
      if (matchText) matchText.textContent = "No coinciden";
      password2Input.classList.add("invalid");
      password2Input.classList.remove("valid");
    }
  }

  if (password1Input) {
    if (password1Input.value) {
      validatePassword(password1Input.value);
    }

    password1Input.addEventListener("input", function () {
      validatePassword(this.value);
      validatePasswordMatch();
    });

    password1Input.addEventListener("keyup", function () {
      validatePassword(this.value);
    });
  }

  if (password2Input) {
    password2Input.addEventListener("input", function () {
      validatePasswordMatch();
    });
  }
}

onReady(initRegisterPage);
