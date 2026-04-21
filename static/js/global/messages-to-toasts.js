import { showToast } from "./toast.js";

export function showDjangoMessagesAsToasts() {
  const el = document.getElementById("django-messages-json");
  if (!el) return;
  let messages = [];
  try {
    messages = JSON.parse(el.textContent || "[]");
  } catch {
    messages = [];
  }
  if (!Array.isArray(messages)) return;
  messages.forEach((msg) => {
    if (!msg) return;
    showToast(msg.text, msg.type);
  });
}

