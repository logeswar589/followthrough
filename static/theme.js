(() => {
  const system = matchMedia("(prefers-color-scheme: dark)");
  const saved = () => {
    try {
      return localStorage.getItem("followthrough-theme");
    } catch {
      return null;
    }
  };
  function apply(theme) {
    document.documentElement.dataset.theme = theme;
    document.querySelectorAll("[data-theme-toggle]").forEach((button) => {
      button.textContent = theme === "dark" ? "☀ Light mode" : "☾ Dark mode";
      button.setAttribute(
        "aria-label",
        theme === "dark" ? "Switch to light theme" : "Switch to dark theme",
      );
    });
  }
  apply(saved() || (system.matches ? "dark" : "light"));
  document.addEventListener("DOMContentLoaded", () => {
    apply(document.documentElement.dataset.theme);
    document.querySelectorAll("[data-theme-toggle]").forEach((button) =>
      button.addEventListener("click", () => {
        const theme =
          document.documentElement.dataset.theme === "dark" ? "light" : "dark";
        try {
          localStorage.setItem("followthrough-theme", theme);
        } catch {}
        apply(theme);
      }),
    );
  });
  system.addEventListener("change", () => {
    if (!saved()) apply(system.matches ? "dark" : "light");
  });
  window.addEventListener("storage", (event) => {
    if (event.key === "followthrough-theme")
      apply(saved() || (system.matches ? "dark" : "light"));
  });
})();
