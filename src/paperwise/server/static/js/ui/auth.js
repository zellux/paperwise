export function getAuthElements() {
  return {
    authGate: document.getElementById("authGate"),
    appShell: document.querySelector(".app-shell"),
    authTabSignIn: document.getElementById("authTabSignIn"),
    authTabSignUp: document.getElementById("authTabSignUp"),
    authPanelSignIn: document.getElementById("authPanelSignIn"),
    authPanelSignUp: document.getElementById("authPanelSignUp"),
    authMessage: document.getElementById("authMessage"),
    sessionUserLabel: document.getElementById("sessionUserLabel"),
  };
}

export function showAuthenticatedShell() {
  const { authGate, appShell } = getAuthElements();
  authGate?.classList.add("view-hidden");
  appShell?.classList.remove("view-hidden");
}

export function setAuthMessage(message, isError = false) {
  const { authMessage } = getAuthElements();
  if (!authMessage) {
    return;
  }
  authMessage.textContent = message;
  authMessage.style.color = isError ? "#9f3f1d" : "";
}

export function setActiveAuthTab(tab) {
  const isSignUp = tab === "signup";
  const { authTabSignIn, authTabSignUp, authPanelSignIn, authPanelSignUp } = getAuthElements();
  authTabSignIn?.classList.toggle("is-active", !isSignUp);
  authTabSignIn?.setAttribute("aria-selected", String(!isSignUp));
  authTabSignUp?.classList.toggle("is-active", isSignUp);
  authTabSignUp?.setAttribute("aria-selected", String(isSignUp));
  authPanelSignIn?.classList.toggle("view-hidden", isSignUp);
  authPanelSignUp?.classList.toggle("view-hidden", !isSignUp);
}

export function renderSessionState(currentUser) {
  const signedIn = Boolean(currentUser);
  const { authGate, appShell, sessionUserLabel } = getAuthElements();
  document.documentElement.classList.toggle("has-session", signedIn);
  authGate?.classList.toggle("view-hidden", signedIn);
  appShell?.classList.toggle("view-hidden", !signedIn);
  if (sessionUserLabel) {
    sessionUserLabel.textContent = signedIn
      ? `${currentUser.full_name} (${currentUser.email})`
      : "Not signed in";
  }
}
