import {
  apiFetch,
  fetchHtmlPartial,
  replaceElementHtml,
} from "paperwise/shared";
import { readInitialData } from "./state/initialData.js";
import {
  applyLlmPreferences,
  llmState,
  resetLlmState,
} from "./state/llm.js";
import {
  normalizeGroundedQaMaxDocuments,
  normalizeGroundedQaTopK,
  normalizePageSize,
} from "./state/preferences.js";
import {
  renderSessionState as renderAuthSessionState,
  setActiveAuthTab,
  setAuthMessage,
  showAuthenticatedShell,
} from "./ui/auth.js";
import {
  getSortableHeaders,
  renderSortHeaders as renderSortHeadersForState,
} from "./ui/sortHeaders.js";

export { readInitialData } from "./state/initialData.js";
export {
  getAuthElements,
  setActiveAuthTab,
  setAuthMessage,
} from "./ui/auth.js";
export {
  LLM_TASK_LABELS,
  createEmptyConnection,
  createDefaultLlmRouting,
  getConnectionApiKeyPlaceholder,
  getConnectionBaseUrlHelpText,
  getConnectionById,
  getConnectionValidationError,
  getInitialLlmProviderDefaults,
  getInitialOcrLlmProviderDefaults,
  getLlmProviderDefaults,
  getLlmUploadBlockReason,
  getOcrLlmProviderDefaults,
  getResolvedTaskSettings,
  getSupportedLlmProviders,
  getSupportedOcrProviders,
  normalizeConnection,
  normalizeLlmPreferences,
  normalizeLlmProvider,
  normalizeOcrProvider,
  normalizeProviderDefaults,
  providerShowsBaseUrlField,
  providerUsesManagedBaseUrl,
  sanitizeLlmRouting,
} from "./state/llm.js";
export {
  getNextSortState,
  normalizeGroundedQaMaxDocuments,
  normalizeGroundedQaTopK,
  normalizePageSize,
  normalizeSortDirection,
  normalizeSortField,
  normalizeSortState,
} from "./state/preferences.js";
export { escapeHtml } from "./ui/escape.js";
export { getSortableHeaders } from "./ui/sortHeaders.js";
export { sortValues, splitTags, unique } from "./ui/values.js";

let currentDocumentId = "";
let currentUser = null;
const THEME_STORAGE_KEY =
  document.documentElement?.dataset?.uiThemeStorageKey || "paperwise.ui.theme";
let currentTheme = "forge";
let ocrStatusRequestSeq = 0;
let docsPageSize = 20;
let groundedQaTopK = 18;
let groundedQaMaxDocuments = 12;
let initialUserPreferencesConsumed = false;
let supportedThemesCache;
let activePageModule = null;
let activePageModuleName = "";
let activePageAssetQuery = "";

// Session shell visibility is implemented in ui/auth.js:
// document.documentElement.classList.toggle("has-session", signedIn)

export const appState = {
  get currentDocumentId() {
    return currentDocumentId;
  },
  set currentDocumentId(value) {
    currentDocumentId = String(value || "");
  },
  get currentUser() {
    return currentUser;
  },
  get currentTheme() {
    return currentTheme;
  },
  get docsPageSize() {
    return docsPageSize;
  },
  set docsPageSize(value) {
    docsPageSize = normalizePageSize(value);
  },
  get groundedQaTopK() {
    return groundedQaTopK;
  },
  set groundedQaTopK(value) {
    groundedQaTopK = normalizeGroundedQaTopK(value);
  },
  get groundedQaMaxDocuments() {
    return groundedQaMaxDocuments;
  },
  set groundedQaMaxDocuments(value) {
    groundedQaMaxDocuments = normalizeGroundedQaMaxDocuments(value);
  },
  get ocrProvider() {
    return llmState.ocrProvider;
  },
  set ocrProvider(value) {
    llmState.ocrProvider = value;
  },
  get ocrAutoSwitch() {
    return llmState.ocrAutoSwitch;
  },
  set ocrAutoSwitch(value) {
    llmState.ocrAutoSwitch = value;
  },
  get ocrImageDetail() {
    return llmState.ocrImageDetail;
  },
  set ocrImageDetail(value) {
    llmState.ocrImageDetail = value;
  },
  get llmConnections() {
    return llmState.llmConnections;
  },
  set llmConnections(value) {
    llmState.llmConnections = value;
  },
  get llmRouting() {
    return llmState.llmRouting;
  },
  set llmRouting(value) {
    llmState.llmRouting = value;
  },
  connectionTestStatuses: llmState.connectionTestStatuses,
  taskTestStatuses: llmState.taskTestStatuses,
  taskTestsInFlight: llmState.taskTestsInFlight,
  get ocrStatusRequestSeq() {
    return ocrStatusRequestSeq;
  },
  set ocrStatusRequestSeq(value) {
    ocrStatusRequestSeq = Number(value) || 0;
  },
};

export function normalizeThemeName(value) {
  const normalized = String(value || "").trim().toLowerCase();
  if (getSupportedThemes().includes(normalized)) {
    return normalized;
  }
  return getDefaultTheme();
}

export function getSupportedThemes() {
  if (supportedThemesCache !== undefined) {
    return supportedThemesCache;
  }
  const initialThemes = readInitialData().ui_themes;
  supportedThemesCache = Array.isArray(initialThemes)
    ? initialThemes
        .map((name) => String(name || "").trim().toLowerCase())
        .filter((name) => name.length > 0)
    : [];
  if (!supportedThemesCache.length) {
    supportedThemesCache = ["forge"];
  }
  return supportedThemesCache;
}

export function getDefaultTheme() {
  const defaultTheme = String(readInitialData().default_ui_theme || "forge").trim().toLowerCase();
  return getSupportedThemes().includes(defaultTheme) ? defaultTheme : "forge";
}

export function readBootTheme() {
  const bootTheme = normalizeThemeName(document.documentElement?.dataset?.uiTheme || "");
  if (bootTheme !== getDefaultTheme()) {
    return bootTheme;
  }
  try {
    return normalizeThemeName(window.localStorage.getItem(THEME_STORAGE_KEY));
  } catch {
    return getDefaultTheme();
  }
}

currentTheme = readBootTheme();

export function formatApiErrorDetail(detail) {
  if (typeof detail === "string") {
    return detail;
  }
  if (detail == null) {
    return "";
  }
  try {
    return JSON.stringify(detail);
  } catch (_error) {
    return String(detail);
  }
}

export function applyTheme(themeName) {
  currentTheme = normalizeThemeName(themeName);
  const classNames = getSupportedThemes().map((name) => `theme-${name}`);
  if (document.documentElement) {
    document.documentElement.classList.remove(...classNames);
    document.documentElement.classList.add(`theme-${currentTheme}`);
    document.documentElement.dataset.uiTheme = currentTheme;
  }
  if (document.body) {
    document.body.classList.remove(...classNames);
    document.body.classList.add(`theme-${currentTheme}`);
  }
  try {
    window.localStorage.setItem(THEME_STORAGE_KEY, currentTheme);
  } catch {
    // Ignore storage write errors (private mode, blocked storage, etc.).
  }
  const themeSelect = document.getElementById("settingsThemeSelect");
  if (themeSelect && themeSelect.value !== currentTheme) {
    themeSelect.value = currentTheme;
  }
}

export function refreshUploadAvailability(options = {}) {
  if (typeof activePageModule?.syncUploadAvailability === "function") {
    return activePageModule.syncUploadAvailability(options);
  }
  return true;
}

export function refreshSettingsForm() {
  if (typeof activePageModule?.renderSettingsForm === "function") {
    activePageModule.renderSettingsForm();
  }
}

async function loadUserPreferences() {
  if (!currentUser) {
    return {};
  }
  const initialData = readInitialData();
  if (
    !initialUserPreferencesConsumed &&
    initialData.authenticated === true &&
    initialData.user_preferences &&
    typeof initialData.user_preferences === "object"
  ) {
    initialUserPreferencesConsumed = true;
    return initialData.user_preferences;
  }
  try {
    const response = await apiFetch("/users/me/preferences");
    const payload = await response.json();
    if (!response.ok) {
      logActivity(`Preference load failed: ${payload.detail || response.statusText}`);
      return {};
    }
    return payload.preferences || {};
  } catch (error) {
    logActivity(`Preference load failed: ${error.message}`);
    return {};
  }
}

export async function saveUserPreferences() {
  if (!currentUser) {
    return;
  }
  const payload = {
    preferences: {
      ui_theme: currentTheme,
      page_size: docsPageSize,
      grounded_qa_top_k_chunks: groundedQaTopK,
      grounded_qa_max_documents: groundedQaMaxDocuments,
      llm_connections: llmState.llmConnections,
      llm_routing: llmState.llmRouting,
      ocr_provider: llmState.ocrProvider,
      ocr_auto_switch: llmState.ocrAutoSwitch,
      ocr_image_detail: llmState.ocrImageDetail,
    },
  };
  try {
    const response = await apiFetch("/users/me/preferences", {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    if (!response.ok) {
      const body = await response.json().catch(() => ({}));
      logActivity(`Preference save failed: ${body.detail || response.statusText}`);
    }
  } catch (error) {
    logActivity(`Preference save failed: ${error.message}`);
  }
}

export function applyUserPreferences(preferences) {
  if (!preferences || typeof preferences !== "object") {
    return;
  }
  if (typeof preferences.ui_theme === "string") {
    applyTheme(preferences.ui_theme);
  }
  docsPageSize = normalizePageSize(preferences.page_size);
  groundedQaTopK = normalizeGroundedQaTopK(preferences.grounded_qa_top_k_chunks);
  groundedQaMaxDocuments = normalizeGroundedQaMaxDocuments(preferences.grounded_qa_max_documents);
  applyLlmPreferences(preferences);
}

async function hydrateUserPreferencesForSession() {
  const preferences = await loadUserPreferences();
  applyUserPreferences(preferences);
}

// Avoid auth-gate flash on page load when the server rendered an authenticated shell.
if (document.documentElement.classList.contains("has-session")) {
  renderSortHeaders();
  showAuthenticatedShell();
}

export function formatStatus(value) {
  if (!value) {
    return "-";
  }
  return value
    .split("_")
    .join(" ")
    .toUpperCase();
}

export function logActivity(message) {
  const activityOutput = document.getElementById("activityOutput");
  if (!activityOutput) {
    return;
  }
  const now = new Date().toLocaleTimeString();
  activityOutput.textContent = `[${now}] ${message}\n${activityOutput.textContent}`;
}

export function delay(ms) {
  return new Promise((resolve) => {
    window.setTimeout(resolve, ms);
  });
}

export function persistSession(user) {
  currentUser = user || null;
}

export function renderSessionState() {
  renderAuthSessionState(currentUser);
}

export function clearSession() {
  persistSession(null);
  applyTheme(getDefaultTheme());
  resetLlmState();
  docsPageSize = 20;
  activePageModule?.clearSessionState?.();
  refreshSettingsForm();
  renderSortHeaders();
  activePageModule?.renderActivityTokenTotal?.(0);
  renderSessionState();
  refreshUploadAvailability();
}

export function restoreSession() {
  const initialData = readInitialData();
  if (initialData.authenticated === true && initialData.current_user) {
    persistSession(initialData.current_user);
    renderSessionState();
    return;
  }
  clearSession();
}

export function getSortStateForTable(tableName) {
  if (typeof activePageModule?.getSortStateForTable === "function") {
    return activePageModule.getSortStateForTable(tableName);
  }
  return { field: "", direction: "" };
}

export function renderSortHeaders() {
  renderSortHeadersForState(getSortStateForTable);
}

export function navigateToDocument(documentId) {
  const url = new URL("/ui/document", window.location.origin);
  url.searchParams.set("id", documentId);
  window.location.href = `${url.pathname}?${url.searchParams.toString()}`;
}

export async function openDocumentFile(documentId) {
  const response = await apiFetch(`/documents/${documentId}/file`);
  if (!response.ok) {
    const payload = await response.json().catch(() => ({}));
    throw new Error(payload.detail || response.statusText);
  }
  const blob = await response.blob();
  const url = window.URL.createObjectURL(blob);
  window.open(url, "_blank", "noopener,noreferrer");
  window.setTimeout(() => window.URL.revokeObjectURL(url), 60_000);
}

export async function deleteDocumentById(documentId, options = {}) {
  const documentLabel = String(options.documentLabel || documentId || "").trim() || "this document";
  const confirmMessage = `Delete "${documentLabel}"? This permanently removes the file and its metadata.`;
  if (!window.confirm(confirmMessage)) {
    return false;
  }

  activePageModule?.prepareDocumentListDelete?.();

  const response = await apiFetch(`/documents/${documentId}`, {
    method: "DELETE",
  });
  if (!response.ok) {
    const payload = await response.json().catch(() => ({}));
    logActivity(`Document delete failed: ${payload.detail || response.statusText}`);
    return false;
  }

  if (currentDocumentId === documentId) {
    currentDocumentId = "";
    window.location.href =
      typeof activePageModule?.buildDocumentsUrl === "function"
        ? activePageModule.buildDocumentsUrl()
        : "/ui/documents";
    return true;
  }

  if (typeof activePageModule?.refreshDocumentListAfterDelete === "function") {
    await activePageModule.refreshDocumentListAfterDelete();
  } else {
    await initializeCurrentPageData();
  }

  logActivity(`Deleted document ${documentId}.`);
  return true;
}

window.document.addEventListener("click", async (event) => {
  const button =
    event.target instanceof Element ? event.target.closest("[data-delete-doc-id]") : null;
  if (!(button instanceof HTMLButtonElement)) {
    return;
  }
  const documentId = button.dataset.deleteDocId || "";
  if (!documentId) {
    return;
  }
  button.disabled = true;
  try {
    await deleteDocumentById(documentId, {
      documentLabel: button.dataset.deleteDocTitle || documentId,
    });
  } finally {
    button.disabled = false;
  }
});

export function hydrateSettingsFormFromInitialPreferences() {
  const initialData = readInitialData();
  if (
    initialData.authenticated !== true ||
    !initialData.user_preferences ||
    typeof initialData.user_preferences !== "object"
  ) {
    return false;
  }
  applyUserPreferences(initialData.user_preferences);
  refreshSettingsForm();
  refreshUploadAvailability();
  return true;
}

export function applyDocumentDetailPartial(partialRoot) {
  currentDocumentId = String(partialRoot?.dataset?.documentId || "");
  partialRoot?.querySelectorAll("template[data-text-target]").forEach((template) => {
    const element = document.getElementById(template.dataset.textTarget || "");
    if (element) {
      element.textContent = template.content.textContent || "";
    }
  });
  partialRoot?.querySelectorAll("template[data-html-target]").forEach((template) => {
    replaceElementHtml(
      document.getElementById(template.dataset.htmlTarget || ""),
      template.innerHTML,
    );
  });
  partialRoot?.querySelectorAll("template[data-input-target]").forEach((template) => {
    const element = document.getElementById(template.dataset.inputTarget || "");
    if (element instanceof HTMLInputElement) {
      element.value = template.content.textContent || "";
    }
  });
  const detailBlobUri = document.getElementById("detailBlobUri");
  if (detailBlobUri && partialRoot?.dataset?.blobUri) {
    detailBlobUri.title = partialRoot.dataset.blobUri;
  }
  const detailFilePreview = document.getElementById("detailFilePreview");
  if (detailFilePreview instanceof HTMLIFrameElement && partialRoot?.dataset?.previewUrl) {
    detailFilePreview.src = partialRoot.dataset.previewUrl;
  }
  const pageStrip = document.getElementById("pageStrip");
  if (pageStrip instanceof HTMLElement && partialRoot?.dataset?.pageCount) {
    pageStrip.dataset.pageCount = partialRoot.dataset.pageCount;
  }
  document.dispatchEvent(new CustomEvent("paperwise:document-detail-updated"));
}

export async function initializeCurrentPageData() {
  if (typeof activePageModule?.initializePage !== "function") {
    return;
  }
  await activePageModule.initializePage({
    authenticated: Boolean(currentUser),
    initialData: readInitialData(),
  });
}

export async function openDocumentView(documentId) {
  const query = new URLSearchParams({ id: documentId });
  const payload = await fetchHtmlPartial(`/ui/partials/document?${query.toString()}`);
  applyDocumentDetailPartial(payload);
  logActivity(`Opened document ${documentId}`);
}

export async function waitForDocumentReady(
  documentId,
  fastPhaseMs = 45000,
  fastIntervalMs = 1500,
  slowPhaseMs = 300000,
  slowIntervalMs = 10000
) {
  const fastDeadline = Date.now() + fastPhaseMs;
  while (Date.now() < fastDeadline) {
    const response = await apiFetch(`/documents/${documentId}`);
    const payload = await response.json();
    if (!response.ok) {
      throw new Error(payload.detail || "Failed to refresh document status");
    }
    if (payload.status === "ready") {
      return true;
    }
    await delay(fastIntervalMs);
  }

  const slowDeadline = Date.now() + slowPhaseMs;
  while (Date.now() < slowDeadline) {
    const response = await apiFetch(`/documents/${documentId}`);
    const payload = await response.json();
    if (!response.ok) {
      throw new Error(payload.detail || "Failed to refresh document status");
    }
    if (payload.status === "ready") {
      return true;
    }
    await delay(slowIntervalMs);
  }

  return false;
}

async function handleSignInSubmit(event) {
  event.preventDefault();
  const email = document.getElementById("signInEmail").value.trim();
  const password = document.getElementById("signInPassword").value;
  setAuthMessage("Signing in...");
  try {
    const response = await apiFetch("/users/login", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      allowUnauthorized: true,
      body: JSON.stringify({ email, password }),
    });
    const payload = await response.json();
    if (!response.ok) {
      setAuthMessage(payload.detail || response.statusText, true);
      return;
    }
    persistSession(payload.user);
    renderSessionState();
    setAuthMessage(`Signed in as ${payload.user.email}.`);
    if (activePageModule?.requiresServerSessionRender === true) {
      window.location.reload();
      return;
    }
    await hydrateUserPreferencesForSession();
    await initializeCurrentPageData();
  } catch (error) {
    setAuthMessage(error.message || "Failed to sign in.", true);
  }
}

async function handleRegisterSubmit(event) {
  event.preventDefault();
  const fullName = document.getElementById("registerName").value.trim();
  const email = document.getElementById("registerEmail").value.trim();
  const password = document.getElementById("registerPassword").value;
  setAuthMessage("Creating account...");
  try {
    const registerResponse = await apiFetch("/users", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        full_name: fullName,
        email,
        password,
      }),
    });
    const registerPayload = await registerResponse.json();
    if (!registerResponse.ok) {
      setAuthMessage(registerPayload.detail || registerResponse.statusText, true);
      return;
    }
    const loginResponse = await apiFetch("/users/login", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      allowUnauthorized: true,
      body: JSON.stringify({ email, password }),
    });
    const loginPayload = await loginResponse.json();
    if (!loginResponse.ok) {
      setAuthMessage(loginPayload.detail || loginResponse.statusText, true);
      return;
    }
    persistSession(loginPayload.user);
    renderSessionState();
    setAuthMessage(`Registered ${registerPayload.email}.`);
    if (activePageModule?.requiresServerSessionRender === true) {
      window.location.reload();
      return;
    }
    await hydrateUserPreferencesForSession();
    await initializeCurrentPageData();
  } catch (error) {
    setAuthMessage(error.message || "Failed to create account.", true);
  }
}

export async function handleSignOutClick() {
  await apiFetch("/users/logout", { method: "POST", allowUnauthorized: true }).catch(() => {});
  clearSession();
  setAuthMessage("Signed out.");
}

export function bindAppShellEvents() {
  document.getElementById("signInForm")?.addEventListener("submit", handleSignInSubmit);
  document.getElementById("registerForm")?.addEventListener("submit", handleRegisterSubmit);
  document.getElementById("authTabSignIn")?.addEventListener("click", () => {
    setActiveAuthTab("signin");
  });
  document.getElementById("authTabSignUp")?.addEventListener("click", () => {
    setActiveAuthTab("signup");
  });
  document.getElementById("signOutBtn")?.addEventListener("click", handleSignOutClick);
  document.getElementById("brandHomeBtn")?.addEventListener("click", () => {
    window.location.href = "/ui/documents";
  });
}

async function loadActivePageModule() {
  if (!activePageModuleName || activePageModule) {
    return activePageModule;
  }
  activePageModule = await import(`/static/js/${activePageModuleName}${activePageAssetQuery}`);
  return activePageModule;
}

export async function initializeApp() {
  await loadActivePageModule();
  restoreSession();
  if (!currentUser) {
    renderSortHeaders();
    return;
  }

  await hydrateUserPreferencesForSession();
  refreshSettingsForm();
  renderSortHeaders();
  refreshUploadAvailability();
  initializeCurrentPageData().catch((error) => {
    logActivity(`Initial page load failed: ${error.message}`);
  });
}

applyTheme(currentTheme);

export function startApp({ pageModuleName = "", assetQuery = "" } = {}) {
  activePageModuleName = String(pageModuleName || "");
  activePageAssetQuery = String(assetQuery || "");
  document.addEventListener("DOMContentLoaded", () => {
    bindAppShellEvents();
    initializeApp().catch((error) => {
      setAuthMessage(error.message || "Failed to initialize app.", true);
    });
  });
}
