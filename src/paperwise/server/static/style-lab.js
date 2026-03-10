const themeButtons = [...document.querySelectorAll(".theme-btn")];
const body = document.body;

function setTheme(themeName) {
  body.classList.remove("theme-atlas", "theme-ledger", "theme-signal", "theme-studio");
  body.classList.add(`theme-${themeName}`);
  for (const button of themeButtons) {
    button.classList.toggle("active", button.dataset.theme === themeName);
  }
  window.location.hash = themeName;
}

for (const button of themeButtons) {
  button.addEventListener("click", () => {
    setTheme(button.dataset.theme);
  });
}

const initialTheme = window.location.hash.replace("#", "").trim();
if (["atlas", "ledger", "signal", "studio"].includes(initialTheme)) {
  setTheme(initialTheme);
}
