let themeButtons = [];
let styleLabBody = null;

function bindStyleLabElements() {
  themeButtons = [...document.querySelectorAll(".theme-btn")];
  styleLabBody = document.body;
}

function setTheme(themeName) {
  styleLabBody?.classList.remove("theme-atlas", "theme-ledger", "theme-signal", "theme-studio");
  styleLabBody?.classList.add(`theme-${themeName}`);
  for (const button of themeButtons) {
    button.classList.toggle("active", button.dataset.theme === themeName);
  }
  window.location.hash = themeName;
}

function initializeStyleLab() {
  bindStyleLabElements();
  for (const button of themeButtons) {
    button.addEventListener("click", () => {
      setTheme(button.dataset.theme);
    });
  }

  const initialTheme = window.location.hash.replace("#", "").trim();
  if (["atlas", "ledger", "signal", "studio"].includes(initialTheme)) {
    setTheme(initialTheme);
  }
}

initializeStyleLab();
