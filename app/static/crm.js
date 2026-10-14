// CR-6 · lietotnes ietvara uzlabojumi. Bez JS viss strādā: izvēlnes ir <details>,
// navigācija mobilajā skatā ir vienkārši redzama.

(() => {
  // Mobilā izvēlne
  const toggle = document.querySelector(".menu-toggle");
  const nav = document.getElementById("main-nav");
  if (toggle && nav) {
    toggle.addEventListener("click", () => {
      const open = nav.classList.toggle("is-open");
      toggle.setAttribute("aria-expanded", String(open));
    });
  }

  // <details> izvēlnes: Escape aizver un atgriež fokusu, bultiņas pārvietojas pa saitēm,
  // klikšķis ārpusē aizver.
  const menus = document.querySelectorAll("details.add-menu, details[data-menu]");
  menus.forEach((menu) => {
    const summary = menu.querySelector("summary");
    const links = () => [...menu.querySelectorAll(".menu-list a")];

    menu.addEventListener("toggle", () => {
      if (menu.open) links()[0]?.focus();
    });
    menu.addEventListener("keydown", (event) => {
      if (event.key === "Escape" && menu.open) {
        menu.open = false;
        summary.focus();
        event.preventDefault();
        return;
      }
      const items = links();
      const index = items.indexOf(document.activeElement);
      if (index === -1) return;
      if (event.key === "ArrowDown" || event.key === "ArrowUp") {
        const step = event.key === "ArrowDown" ? 1 : -1;
        items[(index + step + items.length) % items.length].focus();
        event.preventDefault();
      }
    });
  });
  document.addEventListener("click", (event) => {
    menus.forEach((menu) => {
      if (menu.open && !menu.contains(event.target)) menu.open = false;
    });
  });
})();
