/* PharmaCare — shared front-end behaviour. */
document.addEventListener("DOMContentLoaded", function () {
  // ---- Mobile off-canvas sidebar -----------------------------------------
  const sidebar = document.querySelector(".sidebar");
  const backdrop = document.getElementById("sidebarBackdrop");
  const toggleBtn = document.getElementById("sidebarToggle");

  function openSidebar() {
    sidebar && sidebar.classList.add("show");
    backdrop && backdrop.classList.add("show");
    document.body.style.overflow = "hidden";
  }
  function closeSidebar() {
    sidebar && sidebar.classList.remove("show");
    backdrop && backdrop.classList.remove("show");
    document.body.style.overflow = "";
  }
  if (toggleBtn) {
    toggleBtn.addEventListener("click", () => {
      sidebar.classList.contains("show") ? closeSidebar() : openSidebar();
    });
  }
  if (backdrop) backdrop.addEventListener("click", closeSidebar);
  // Close the drawer after tapping a nav link (mobile UX)
  document.querySelectorAll(".sidebar-nav .nav-link").forEach((link) => {
    link.addEventListener("click", () => { if (window.innerWidth < 992) closeSidebar(); });
  });
  window.addEventListener("resize", () => { if (window.innerWidth >= 992) closeSidebar(); });

  // ---- Dark mode -------------------------------------------------------
  // data-theme is already applied server-side (see base.html) to avoid a
  // flash of the wrong theme; this just keeps the toggle and cookie in sync.
  const themeToggle = document.getElementById("themeToggle");
  const root = document.documentElement;
  if (themeToggle) {
    themeToggle.checked = root.getAttribute("data-theme") === "dark";
    themeToggle.addEventListener("change", function () {
      const next = this.checked ? "dark" : "light";
      root.setAttribute("data-theme", next);
      document.cookie = `pharmacare_theme=${next}; path=/; max-age=31536000`;
    });
  }

  // ---- Searchable dropdowns --------------------------------------------
  // Any <select> with more than 8 options becomes type-to-search, so long
  // lists (medicines, categories, suppliers, customers) stay usable.
  // Opt out per-field with class="no-search"; opt in on a short list with
  // class="searchable". Pages that build their own Tom Select instances
  // (e.g. the purchase form's dynamic rows) are skipped automatically
  // because Tom Select sets el.tomselect once initialised.
  if (typeof TomSelect !== "undefined") {
    document.querySelectorAll("select").forEach(function (el) {
      if (el.tomselect || el.multiple) return;
      if (el.classList.contains("no-search")) return;
      const optionCount = el.querySelectorAll("option").length;
      if (optionCount <= 8 && !el.classList.contains("searchable")) return;
      new TomSelect(el, {
        create: false,
        maxOptions: null,
        allowEmptyOption: true,
        placeholder: el.dataset.placeholder || null,
      });
    });
  }

  // ---- Auto-dismiss alerts after 5s -----------------------------------
  document.querySelectorAll(".alert[data-auto-dismiss]").forEach((el) => {
    setTimeout(() => {
      el.classList.remove("show");
      el.classList.add("fade");
    }, 5000);
  });
});
