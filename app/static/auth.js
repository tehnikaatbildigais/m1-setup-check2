// CR-4 · formas sūta JSON uz /auth/* un rāda servera kļūdas pie laukiem.

const FIELD_MESSAGES = {
  "email:ALREADY_EXISTS": "Šis e-pasts jau ir reģistrēts.",
  "username:ALREADY_EXISTS": "Šis lietotājvārds jau ir aizņemts.",
  "username:INVALID_FORMAT": "Lietotājvārds nedrīkst saturēt simbolu @.",
  "email:INVALID_FORMAT": "Ievadi derīgu e-pasta adresi, piemēram, vards@example.com.",
  "token:INVALID_OR_EXPIRED": "Saite ir nederīga, jau izmantota vai beigusies. Pieprasi jaunu saiti.",
};

const ISSUE_MESSAGES = {
  REQUIRED: "Šis lauks ir obligāts.",
  INVALID_FORMAT: "Nederīgs formāts.",
  TOO_SHORT: "Parolei jābūt vismaz 8 simbolus garai.",
  MISMATCH: "Paroles nesakrīt.",
  TOO_LONG: "Parole ir pārāk gara (ne vairāk kā 1024 simboli).",
};

const STATUS_MESSAGES = {
  401: "Nepareizs e-pasts, lietotājvārds vai parole. Pēc 3 kļūdām pēc kārtas pieteikšanās uz laiku tiek bloķēta.",
};

function clearErrors(form) {
  form.querySelectorAll(".field-error, .form-error").forEach((el) => (el.textContent = ""));
  form.querySelectorAll("[aria-invalid]").forEach((el) => el.removeAttribute("aria-invalid"));
}

function showFormError(form, message) {
  form.querySelector(".form-error").textContent = message;
}

function showFieldError(form, field, issue) {
  const message = FIELD_MESSAGES[`${field}:${issue}`] || ISSUE_MESSAGES[issue] || "Nederīga vērtība.";
  const target = form.querySelector(`[data-error-for="${CSS.escape(field)}"]`);
  if (!target) {
    showFormError(form, message);
    return;
  }
  target.textContent = message;
  form.querySelector(`[name="${CSS.escape(field)}"]`)?.setAttribute("aria-invalid", "true");
}

async function submitForm(event) {
  event.preventDefault();
  const form = event.currentTarget;
  const button = form.querySelector("button[type=submit]");
  clearErrors(form);
  document.querySelectorAll("[data-notice-param]").forEach((el) => (el.hidden = true));
  button.disabled = true;

  let response;
  try {
    response = await fetch(form.dataset.endpoint, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      credentials: "same-origin",
      body: JSON.stringify(Object.fromEntries(new FormData(form))),
    });
  } catch {
    showFormError(form, "Neizdevās sazināties ar serveri. Mēģini vēlreiz.");
    button.disabled = false;
    return;
  }

  if (response.ok) {
    if (form.dataset.redirect) {
      window.location.assign(form.dataset.redirect);
      return;
    }
    const notice = document.querySelector(form.dataset.successNotice);
    notice.hidden = false;
    form.reset();
    button.disabled = false;
    return;
  }

  let error = {};
  try {
    error = (await response.json()).error || {};
  } catch {
    // Atbilde nav JSON; parāda vispārīgu kļūdu.
  }
  if (STATUS_MESSAGES[response.status]) {
    showFormError(form, STATUS_MESSAGES[response.status]);
  } else if (error.details?.length) {
    error.details.forEach((d) => showFieldError(form, d.field, d.issue));
  } else {
    showFormError(form, "Radās kļūda. Mēģini vēlreiz vēlāk.");
  }
  button.disabled = false;
}

function showQueryNotices() {
  const params = new URLSearchParams(window.location.search);
  document.querySelectorAll("[data-notice-param]").forEach((el) => {
    if (params.has(el.dataset.noticeParam)) el.hidden = false;
  });
  const tokenInput = document.querySelector('input[name="token"]');
  if (tokenInput) {
    tokenInput.value = params.get("token") || "";
    // Marķieris nepaliek adreses joslā un pārlūka vēsturē.
    if (params.has("token")) window.history.replaceState(null, "", window.location.pathname);
  }
}

document.querySelectorAll("form[data-endpoint]").forEach((form) => {
  form.addEventListener("submit", submitForm);
});
showQueryNotices();
