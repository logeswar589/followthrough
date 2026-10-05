(() => {
  const palettes = [
    {
      id: "neon",
      name: "Neon green",
      color: "#b6ff43",
      detail: "Electric green on ink black",
    },
    {
      id: "cyan",
      name: "Glacier",
      color: "#58e7ff",
      detail: "Cool cyan, crisp and calm",
    },
    {
      id: "violet",
      name: "After hours",
      color: "#c2a0ff",
      detail: "Soft violet with a little glow",
    },
    {
      id: "amber",
      name: "Golden hour",
      color: "#ffc45c",
      detail: "Warm amber, late-night energy",
    },
    {
      id: "mono",
      name: "Graphite",
      color: "#e1e6ec",
      detail: "Quiet silver and charcoal",
    },
  ];
  const read = (key) => {
    try {
      return localStorage.getItem(key);
    } catch {
      return null;
    }
  };
  const validPalette = (id) => palettes.some((p) => p.id === id);
  const savedPalette = read("followthrough-color-scheme");
  let palette = validPalette(savedPalette) ? savedPalette : "neon";
  // New palette preferences start with the requested dark design.
  let theme =
    validPalette(savedPalette) && read("followthrough-theme") === "light"
      ? "light"
      : "dark";
  function apply() {
    const root = document.documentElement;
    root.dataset.theme = theme;
    root.dataset.colorScheme = palette;
    root.style.colorScheme = theme;
    document.querySelectorAll("[data-theme-toggle]").forEach((button) => {
      button.textContent = theme === "dark" ? "☀ Light mode" : "☾ Dark mode";
      button.setAttribute(
        "aria-label",
        theme === "dark" ? "Switch to light theme" : "Switch to dark theme",
      );
    });
    document.querySelectorAll("[name=color-scheme]").forEach((input) => {
      input.checked = input.value === palette;
    });
    document
      .querySelectorAll("[data-appearance-mode]")
      .forEach((button) =>
        button.setAttribute(
          "aria-pressed",
          String(button.dataset.appearanceMode === theme),
        ),
      );
    const current = document.querySelector("#appearanceCurrent");
    if (current)
      current.textContent = `${palettes.find((p) => p.id === palette).name} · ${theme} mode. Saved on this device.`;
  }
  function save() {
    try {
      localStorage.setItem("followthrough-color-scheme", palette);
      localStorage.setItem("followthrough-theme", theme);
    } catch {}
    apply();
  }
  apply();
  document.addEventListener("DOMContentLoaded", () => {
    const dialog = document.createElement("dialog");
    dialog.id = "appearanceDialog";
    dialog.className = "appearance-dialog";
    dialog.setAttribute("aria-labelledby", "appearanceTitle");
    dialog.innerHTML = `
      <div class="appearance-heading"><div><span class="eyebrow">MAKE IT YOURS</span><h2 id="appearanceTitle">Workspace settings</h2></div><button type="button" data-close-appearance aria-label="Close settings">×</button></div>
      <p class="appearance-intro">A different mood. The same space for your thoughts.</p>
      <fieldset class="appearance-fieldset"><legend>Color scheme</legend><div class="palette-grid">
        ${palettes
          .map(
            (p) => `<label class="palette-option" style="--swatch:${p.color}">
          <input type="radio" name="color-scheme" value="${p.id}">
          <span class="palette-preview" aria-hidden="true"><i class="palette-preview-side"></i><i class="palette-preview-line"></i><i class="palette-preview-line short"></i><i class="palette-preview-action"></i></span>
          <span class="palette-name">${p.name}<span class="palette-selected" aria-hidden="true">✓</span></span><span class="palette-description">${p.detail}</span>
        </label>`,
          )
          .join("")}
      </div></fieldset>
      <fieldset class="appearance-fieldset appearance-mode"><legend>Appearance</legend><div><button type="button" data-appearance-mode="dark">☾ Dark</button><button type="button" data-appearance-mode="light">☀ Light</button></div></fieldset>
      <p id="appearanceCurrent" role="status" aria-live="polite"></p>
      <div class="appearance-footer"><span>Changes apply instantly.</span><button type="button" class="primary" data-close-appearance>Done</button></div>`;
    document.body.append(dialog);
    apply();
    document
      .querySelectorAll("[data-open-appearance]")
      .forEach((button) =>
        button.addEventListener("click", () => dialog.showModal()),
      );
    dialog
      .querySelectorAll("[data-close-appearance]")
      .forEach((button) =>
        button.addEventListener("click", () => dialog.close()),
      );
    dialog.addEventListener("click", (event) => {
      if (event.target === dialog) {
        const box = dialog.getBoundingClientRect();
        if (
          event.clientX < box.left ||
          event.clientX > box.right ||
          event.clientY < box.top ||
          event.clientY > box.bottom
        )
          dialog.close();
      }
    });
    dialog.querySelectorAll("[name=color-scheme]").forEach((input) =>
      input.addEventListener("change", () => {
        palette = input.value;
        save();
      }),
    );
    document.querySelectorAll("[data-theme-toggle]").forEach((button) =>
      button.addEventListener("click", () => {
        theme = theme === "dark" ? "light" : "dark";
        save();
      }),
    );
    dialog.querySelectorAll("[data-appearance-mode]").forEach((button) =>
      button.addEventListener("click", () => {
        theme = button.dataset.appearanceMode;
        save();
      }),
    );
  });
  window.addEventListener("storage", (event) => {
    if (
      ["followthrough-theme", "followthrough-color-scheme", null].includes(
        event.key,
      )
    ) {
      const saved = read("followthrough-color-scheme");
      palette = validPalette(saved) ? saved : "neon";
      theme = read("followthrough-theme") === "light" ? "light" : "dark";
      apply();
    }
  });
})();
