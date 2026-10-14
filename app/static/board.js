// CR-6 · uzdevumu sadales tāfele. Vilkšana ir uzlabojums: katrai kartītei ir arī forma
// „Nodot citam darbiniekam” (WCAG 2.2, 2.5.7), kas strādā arī bez JavaScript.

(() => {
  const board = document.querySelector("[data-board]");
  if (!board) return;
  const live = document.getElementById("live");

  const announce = (message) => {
    live.textContent = "";
    window.setTimeout(() => { live.textContent = message; }, 50);
  };

  const columnOf = (element) => element.closest(".board-column");
  const columnFor = (employeeId) =>
    board.querySelector(`.board-column[data-employee="${employeeId}"]`);

  // Kavētie augšā, tad pēc termiņa (CR-6 #16).
  const sortKey = (card) => `${card.dataset.late === "1" ? 0 : 1}-${card.dataset.due}-${card.dataset.task.padStart(8, "0")}`;

  function placeCard(card, column) {
    const list = column.querySelector(".column-cards");
    const key = sortKey(card);
    const before = [...list.children].find((other) => other !== card && sortKey(other) > key);
    list.insertBefore(card, before || null);
  }

  function refreshCounts() {
    const columns = [...board.querySelectorAll(".board-column")];
    const stats = columns.map((column) => {
      const cards = column.querySelectorAll(".task-card:not([hidden])");
      const late = column.querySelectorAll('.task-card[data-late="1"]:not([hidden])').length;
      return { column, open: cards.length, late };
    });
    const busiest = Math.max(1, ...stats.map((s) => s.open));
    stats.forEach(({ column, open, late }) => {
      column.querySelector("[data-open]").textContent = open;
      column.querySelector("[data-late]").textContent = late;
      column.querySelector("[data-late-wrap]").classList.toggle("late", late > 0);
      column.querySelector("[data-empty]").hidden = open > 0;
      const [lateBar, openBar] = column.querySelectorAll("[data-load] span");
      lateBar.style.width = `${(late / busiest) * 100}%`;
      openBar.style.width = `${((open - late) / busiest) * 100}%`;
    });
    document.querySelector("[data-total-open]").textContent = stats.reduce((n, s) => n + s.open, 0);
    document.querySelector("[data-total-late]").textContent = stats.reduce((n, s) => n + s.late, 0);
  }

  async function sendReassign(card, employeeId) {
    const form = card.querySelector("form.reassign");
    const body = new URLSearchParams({ assignee_id: employeeId });
    let response;
    try {
      response = await fetch(form.action, {
        method: "POST",
        headers: { Accept: "application/json" },
        credentials: "same-origin",
        body,
      });
    } catch {
      return { ok: false, message: "Neizdevās sazināties ar serveri" };
    }
    const isJson = (response.headers.get("content-type") || "").includes("application/json");
    // Ne-JSON atbilde (piem., pāradresācija uz sākumlapu) nozīmē, ka nekas netika saglabāts.
    if (response.ok && isJson && !response.redirected) {
      return { ok: true, data: await response.json() };
    }
    const reasons = { 403: "Nav tiesību mainīt izpildītāju", 404: "Uzdevums nav atrasts" };
    let message = reasons[response.status] || (response.ok ? "Sesija beigusies, atver sākumlapu" : "Servera kļūda");
    let code = "";
    if (isJson) {
      try {
        const payload = await response.json();
        if (payload.error?.message) message = payload.error.message;
        code = payload.error?.code || "";
      } catch { /* bojāts JSON */ }
    }
    return { ok: false, message, code };
  }

  // Kopīgā darbība vilkšanai un formai: optimistiski pārvieto, kļūdas gadījumā atgriež.
  async function reassign(card, employeeId, { focusAfter } = {}) {
    const fromColumn = columnOf(card);
    const title = card.querySelector("h3").textContent;
    if (fromColumn.dataset.employee === String(employeeId)) {
      // CR-6 #22: nomešana tajā pašā kolonnā ir klusa; formas lietotājam dod atbildi.
      if (focusAfter) announce(`Uzdevums „${title}” jau ir šim darbiniekam.`);
      return;
    }
    // Kamēr iepriekšējā pārvietošana nav beigusies, jaunu nesāk (citādi atgriešana
    // pēc vecas kļūdas var novietot kartīti kolonnā, kas neatbilst serverim).
    if (card.dataset.pending) {
      announce(`Uzdevums „${title}” vēl tiek nodots. Mēģini pēc brīža.`);
      return;
    }
    card.dataset.pending = "1";
    card.setAttribute("aria-busy", "true");
    try {
      await moveAndSave(card, fromColumn, employeeId, title, focusAfter);
    } finally {
      delete card.dataset.pending;
      card.removeAttribute("aria-busy");
    }
  }

  async function moveAndSave(card, fromColumn, employeeId, title, focusAfter) {
    const toColumn = columnFor(employeeId);
    const select = card.querySelector("select");
    // Iepriekšējais izpildītājs ir kolonnas darbinieks (forma jau var rādīt jauno izvēli).
    const previous = fromColumn.dataset.employee;

    if (toColumn) placeCard(card, toColumn);
    else card.hidden = true;
    refreshCounts();

    const result = await sendReassign(card, employeeId);
    if (!result.ok && result.code === "TASK_DONE") {
      // Uzdevums jau izpildīts citur: kartīte vairs nepieder tāfelei.
      card.remove();
      refreshCounts();
      announce(`Uzdevums „${title}” jau ir izpildīts, tāpēc tas noņemts no tāfeles.`);
      if (focusAfter) board.focus();
      return;
    }
    if (!result.ok) {
      card.hidden = false;
      placeCard(card, fromColumn);
      select.value = previous;
      refreshCounts();
      announce(`Uzdevumu „${title}” neizdevās nodot: ${result.message}. Kartīte atgriezta.`);
      if (focusAfter) select.focus();
      return;
    }
    select.value = String(employeeId);
    const name = result.data.assignee_name;
    if (toColumn) {
      card.classList.remove("just-moved");
      void card.offsetWidth;
      card.classList.add("just-moved");
      announce(`Uzdevums nodots: ${name} („${title}”).`);
      if (focusAfter) select.focus();
    } else {
      card.remove();
      refreshCounts();
      announce(`Uzdevums nodots: ${name} („${title}”). Šī darbinieka kolonna nav rādīta.`);
      if (focusAfter) board.focus();
    }
  }

  // Forma „Nodot citam darbiniekam”
  board.addEventListener("submit", (event) => {
    const form = event.target.closest("form.reassign");
    if (!form) return;
    event.preventDefault();
    const card = form.closest(".task-card");
    reassign(card, form.querySelector("select").value, { focusAfter: true });
  });

  // Vilkšana
  let dragged = null;
  board.addEventListener("dragstart", (event) => {
    const card = event.target.closest?.(".task-card");
    if (!card) return;
    dragged = card;
    card.classList.add("is-dragging");
    event.dataTransfer.effectAllowed = "move";
    event.dataTransfer.setData("text/plain", card.dataset.task);
  });
  board.addEventListener("dragend", () => {
    dragged?.classList.remove("is-dragging");
    board.querySelectorAll(".is-over").forEach((c) => c.classList.remove("is-over"));
    dragged = null;
  });
  board.addEventListener("dragover", (event) => {
    const column = columnOf(event.target);
    if (!dragged || !column) return;
    event.preventDefault();
    event.dataTransfer.dropEffect = "move";
    board.querySelectorAll(".is-over").forEach((c) => c !== column && c.classList.remove("is-over"));
    column.classList.add("is-over");
  });
  board.addEventListener("dragleave", (event) => {
    const column = columnOf(event.target);
    if (column && !column.contains(event.relatedTarget)) column.classList.remove("is-over");
  });
  board.addEventListener("drop", (event) => {
    const column = columnOf(event.target);
    if (!dragged || !column) return;
    event.preventDefault();
    column.classList.remove("is-over");
    reassign(dragged, column.dataset.employee);
  });
})();
