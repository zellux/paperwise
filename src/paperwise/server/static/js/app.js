let currentDocumentId = "";
let currentUser = null;
const THEME_STORAGE_KEY =
  document.documentElement?.dataset?.uiThemeStorageKey || "paperwise.ui.theme";
let currentTheme = "forge";
const LLM_TASK_LABELS = {
  metadata: "Metadata Extraction",
  grounded_qa: "Search and Ask Your Docs",
  ocr: "OCR",
};
let ocrProvider = "llm";
let ocrImageDetail = "auto";
let ocrAutoSwitch = false;
let llmConnections = [];
let llmRouting = {
  metadata: { connection_id: "", model: "" },
  grounded_qa: { connection_id: "", model: "" },
  ocr: { engine: "llm", connection_id: "", model: "" },
};
const connectionTestStatuses = new Map();
const taskTestStatuses = new Map();
const taskTestsInFlight = new Set();
let ocrStatusRequestSeq = 0;
let docsPageSize = 20;
let groundedQaTopK = 18;
let groundedQaMaxDocuments = 12;
let initialDataCache;
let initialUserPreferencesConsumed = false;
let supportedThemesCache;
let supportedLlmProvidersCache;
let supportedOcrProvidersCache;
let llmProviderDefaultsCache;
let ocrLlmProviderDefaultsCache;

function normalizePageSize(value) {
  const size = Number(value);
  if (!Number.isInteger(size) || size <= 0) {
    return 20;
  }
  return size;
}

function normalizeSortDirection(value) {
  const normalized = String(value || "").trim().toLowerCase();
  if (normalized === "asc" || normalized === "desc") {
    return normalized;
  }
  return "";
}

function normalizeSortField(value, allowedFields) {
  const normalized = String(value || "").trim();
  if (allowedFields.has(normalized)) {
    return normalized;
  }
  return "";
}

function normalizeSortState(value, allowedFields) {
  const field = normalizeSortField(value?.field, allowedFields);
  const direction = normalizeSortDirection(value?.direction);
  if (!field || !direction) {
    return { field: "", direction: "" };
  }
  return { field, direction };
}

function getNextSortState(currentState, field) {
  if (currentState.field !== field || !currentState.direction) {
    return { field, direction: "asc" };
  }
  if (currentState.direction === "asc") {
    return { field, direction: "desc" };
  }
  return { field: "", direction: "" };
}

function normalizeGroundedQaTopK(value) {
  const size = Number(value);
  if (!Number.isInteger(size)) {
    return 18;
  }
  return Math.max(3, Math.min(60, size));
}

function normalizeGroundedQaMaxDocuments(value) {
  const size = Number(value);
  if (!Number.isInteger(size)) {
    return 12;
  }
  return Math.max(1, Math.min(50, size));
}

function normalizeThemeName(value) {
  const normalized = String(value || "").trim().toLowerCase();
  if (getSupportedThemes().includes(normalized)) {
    return normalized;
  }
  return getDefaultTheme();
}

function getSupportedThemes() {
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

function getDefaultTheme() {
  const defaultTheme = String(readInitialData().default_ui_theme || "forge").trim().toLowerCase();
  return getSupportedThemes().includes(defaultTheme) ? defaultTheme : "forge";
}

function getSupportedLlmProviders() {
  if (supportedLlmProvidersCache !== undefined) {
    return supportedLlmProvidersCache;
  }
  const initialProviders = readInitialData().llm_supported_providers;
  supportedLlmProvidersCache = Array.isArray(initialProviders)
    ? initialProviders
        .map((provider) => String(provider || "").trim().toLowerCase())
        .filter((provider) => provider.length > 0)
    : [];
  if (!supportedLlmProvidersCache.length) {
    supportedLlmProvidersCache = ["openai", "gemini", "custom"];
  }
  return supportedLlmProvidersCache;
}

function getSupportedOcrProviders() {
  if (supportedOcrProvidersCache !== undefined) {
    return supportedOcrProvidersCache;
  }
  const initialProviders = readInitialData().ocr_supported_providers;
  supportedOcrProvidersCache = Array.isArray(initialProviders)
    ? initialProviders
        .map((provider) => String(provider || "").trim().toLowerCase())
        .filter((provider) => provider.length > 0)
    : [];
  if (!supportedOcrProvidersCache.length) {
    supportedOcrProvidersCache = ["tesseract", "llm"];
  }
  return supportedOcrProvidersCache;
}

function readBootTheme() {
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

function normalizeLlmProvider(value) {
  const normalized = String(value || "").trim().toLowerCase();
  if (getSupportedLlmProviders().includes(normalized)) {
    return normalized;
  }
  return "";
}

function getLlmProviderDefaults(provider) {
  const normalized = normalizeLlmProvider(provider);
  if (!normalized) {
    return null;
  }
  return getInitialLlmProviderDefaults()[normalized] || null;
}

function getOcrLlmProviderDefaults(provider) {
  const normalized = normalizeLlmProvider(provider);
  if (!normalized) {
    return null;
  }
  return getInitialOcrLlmProviderDefaults()[normalized] || null;
}

function normalizeProviderDefaults(rawDefaults) {
  if (!rawDefaults || typeof rawDefaults !== "object") {
    return {};
  }
  const defaults = {};
  for (const [provider, values] of Object.entries(rawDefaults)) {
    const normalizedProvider = normalizeLlmProvider(provider);
    if (!normalizedProvider || !values || typeof values !== "object") {
      continue;
    }
    defaults[normalizedProvider] = {
      model: String(values.model || "").trim(),
      base_url: String(values.base_url || "").trim(),
    };
  }
  return defaults;
}

function getInitialLlmProviderDefaults() {
  if (llmProviderDefaultsCache !== undefined) {
    return llmProviderDefaultsCache;
  }
  llmProviderDefaultsCache = normalizeProviderDefaults(readInitialData().llm_provider_defaults);
  return llmProviderDefaultsCache;
}

function getInitialOcrLlmProviderDefaults() {
  if (ocrLlmProviderDefaultsCache !== undefined) {
    return ocrLlmProviderDefaultsCache;
  }
  ocrLlmProviderDefaultsCache = normalizeProviderDefaults(readInitialData().ocr_llm_provider_defaults);
  return ocrLlmProviderDefaultsCache;
}

function providerUsesManagedBaseUrl(provider) {
  const normalized = normalizeLlmProvider(provider);
  return normalized === "openai" || normalized === "gemini";
}

function providerShowsBaseUrlField(provider) {
  return !providerUsesManagedBaseUrl(provider);
}

function getConnectionBaseUrlHelpText(provider) {
  const normalized = normalizeLlmProvider(provider);
  if (normalized === "gemini") {
    return "Uses Google's default Gemini API endpoint automatically.";
  }
  if (normalized === "openai") {
    return "Uses OpenAI's default API endpoint automatically.";
  }
  if (normalized === "custom") {
    return "Required for OpenAI-compatible providers.";
  }
  return "";
}

function getConnectionApiKeyPlaceholder(provider) {
  const normalized = normalizeLlmProvider(provider);
  if (normalized === "gemini") {
    return "AIza...";
  }
  return "sk-...";
}

function getConnectionApiKeyValidationError(provider, apiKey) {
  const normalized = normalizeLlmProvider(provider);
  const normalizedApiKey = String(apiKey || "").trim();
  if (!normalizedApiKey) {
    return "";
  }
  if (normalized === "gemini" && normalizedApiKey.startsWith("sk-")) {
    return "Gemini API keys should not start with sk-.";
  }
  return "";
}

function formatApiErrorDetail(detail) {
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

function normalizeOcrProvider(value) {
  const normalized = String(value || "").trim().toLowerCase();
  if (getSupportedOcrProviders().includes(normalized)) {
    return normalized;
  }
  return "llm";
}

function normalizeOcrImageDetail(value) {
  const normalized = String(value || "").trim().toLowerCase();
  if (["auto", "low", "high"].includes(normalized)) {
    return normalized;
  }
  return "auto";
}

function normalizeOcrAutoSwitch(value) {
  if (typeof value === "boolean") {
    return value;
  }
  const normalized = String(value || "").trim().toLowerCase();
  return normalized === "true" || normalized === "1" || normalized === "on" || normalized === "yes";
}

function applyTheme(themeName) {
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

function createEmptyConnection(index = llmConnections.length + 1) {
  return {
    id: `connection-${Date.now()}-${index}`,
    name: `Connection ${index}`,
    provider: "",
    base_url: "",
    api_key: "",
  };
}

function createDefaultLlmRouting() {
  return {
    metadata: { connection_id: "", model: "" },
    grounded_qa: { connection_id: "", model: "" },
    ocr: { engine: "llm", connection_id: "", model: "" },
  };
}

function normalizeConnection(connection, index = 0) {
  const provider = normalizeLlmProvider(connection?.provider);
  const normalized = {
    id: String(connection?.id || `connection-${index + 1}`).trim() || `connection-${index + 1}`,
    name: String(connection?.name || "").trim(),
    provider,
    base_url: String(connection?.base_url || "").trim(),
    api_key: String(connection?.api_key || "").trim(),
    default_model: String(connection?.default_model || "").trim(),
  };
  if (
    !normalized.name &&
    !normalized.provider &&
    !normalized.base_url &&
    !normalized.api_key &&
    !normalized.default_model
  ) {
    return null;
  }
  if (!normalized.name) {
    normalized.name = provider ? provider[0].toUpperCase() + provider.slice(1) : `Connection ${index + 1}`;
  }
  if (providerUsesManagedBaseUrl(provider)) {
    normalized.base_url = "";
  }
  return normalized;
}

function normalizeLlmPreferences(preferences) {
  if (
    Array.isArray(preferences?.llm_connections) &&
    preferences?.llm_routing &&
    typeof preferences.llm_routing === "object"
  ) {
    const connections = preferences.llm_connections
      .map((connection, index) => normalizeConnection(connection, index))
      .filter(Boolean);
    const routing = createDefaultLlmRouting();
    const rawRouting = preferences.llm_routing || {};
    routing.metadata.connection_id = String(rawRouting.metadata?.connection_id || "").trim();
    routing.metadata.model = String(rawRouting.metadata?.model || "").trim();
    routing.grounded_qa.connection_id = String(rawRouting.grounded_qa?.connection_id || "").trim();
    routing.grounded_qa.model = String(rawRouting.grounded_qa?.model || "").trim();
    routing.ocr.engine = normalizeOcrProvider(rawRouting.ocr?.engine || "llm");
    routing.ocr.connection_id = String(rawRouting.ocr?.connection_id || "").trim();
    routing.ocr.model = String(rawRouting.ocr?.model || "").trim();
    return { llm_connections: connections, llm_routing: routing };
  }
  return { llm_connections: [], llm_routing: createDefaultLlmRouting() };
}

function sanitizeLlmRouting(connections, routing) {
  const connectionIds = new Set(connections.map((connection) => connection.id));
  const nextRouting = createDefaultLlmRouting();
  nextRouting.metadata.connection_id = connectionIds.has(routing?.metadata?.connection_id)
    ? routing.metadata.connection_id
    : connections[0]?.id || "";
  nextRouting.metadata.model = String(routing?.metadata?.model || "").trim();
  nextRouting.grounded_qa.connection_id = connectionIds.has(routing?.grounded_qa?.connection_id)
    ? routing.grounded_qa.connection_id
    : connections[0]?.id || "";
  nextRouting.grounded_qa.model = String(routing?.grounded_qa?.model || "").trim();
  nextRouting.ocr.engine = normalizeOcrProvider(routing?.ocr?.engine || "llm");
  nextRouting.ocr.connection_id = connectionIds.has(routing?.ocr?.connection_id)
    ? routing.ocr.connection_id
    : connections[0]?.id || "";
  nextRouting.ocr.model = String(routing?.ocr?.model || "").trim();
  return nextRouting;
}

function getConnectionById(connectionId) {
  return llmConnections.find((connection) => connection.id === connectionId) || null;
}

function getResolvedTaskSettings(task) {
  if (task === "ocr") {
    if (llmRouting.ocr.engine === "tesseract") {
      return null;
    }
  } else if (!llmRouting[task]) {
    return null;
  }
  const effectiveRoute = llmRouting[task];
  const connection = getConnectionById(effectiveRoute.connection_id);
  if (!connection) {
    return null;
  }
  const defaults = task === "ocr"
    ? getOcrLlmProviderDefaults(connection.provider)
    : getLlmProviderDefaults(connection.provider);
  return {
    connection_id: connection.id,
    connection_name: connection.name,
    provider: connection.provider,
    base_url: connection.base_url || defaults?.base_url || "",
    api_key: connection.api_key,
    model: String(effectiveRoute.model || "").trim() || String(connection.default_model || "").trim() || defaults?.model || "",
  };
}

function getConnectionValidationError(connection) {
  const provider = normalizeLlmProvider(connection?.provider);
  if (!provider) {
    return "configure a provider.";
  }
  if (!String(connection?.api_key || "").trim()) {
    return "add an API key.";
  }
  const apiKeyError = getConnectionApiKeyValidationError(provider, connection?.api_key);
  if (apiKeyError) {
    return apiKeyError;
  }
  if (provider === "custom" && !String(connection?.base_url || "").trim()) {
    return "set a custom base URL.";
  }
  return "";
}

function getLlmUploadBlockReason() {
  const metadataSettings = getResolvedTaskSettings("metadata");
  if (!metadataSettings) {
    return "configure a metadata LLM connection in Settings.";
  }
  const metadataError = getConnectionValidationError(metadataSettings);
  if (metadataError) {
    return `${metadataError} Metadata extraction needs a working LLM connection.`;
  }
  if (ocrProvider === "llm") {
    const ocrSettings = getResolvedTaskSettings("ocr");
    if (!ocrSettings) {
      return "configure an OCR LLM connection or switch OCR to Local Tesseract.";
    }
    const ocrError = getConnectionValidationError(ocrSettings);
    if (ocrError) {
      return `${ocrError} OCR needs a working connection.`;
    }
  }
  return "";
}

function refreshUploadAvailability(options = {}) {
  if (typeof syncUploadAvailability === "function") {
    return syncUploadAvailability(options);
  }
  return true;
}

function refreshSettingsForm() {
  if (typeof renderSettingsForm === "function") {
    renderSettingsForm();
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

async function saveUserPreferences() {
  if (!currentUser) {
    return;
  }
  const payload = {
    preferences: {
      ui_theme: currentTheme,
      grounded_qa_top_k_chunks: groundedQaTopK,
      grounded_qa_max_documents: groundedQaMaxDocuments,
      llm_connections: llmConnections,
      llm_routing: llmRouting,
      ocr_provider: ocrProvider,
      ocr_auto_switch: ocrAutoSwitch,
      ocr_image_detail: ocrImageDetail,
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

function applyUserPreferences(preferences) {
  if (!preferences || typeof preferences !== "object") {
    return;
  }
  if (typeof preferences.ui_theme === "string") {
    applyTheme(preferences.ui_theme);
  }
  groundedQaTopK = normalizeGroundedQaTopK(preferences.grounded_qa_top_k_chunks);
  groundedQaMaxDocuments = normalizeGroundedQaMaxDocuments(preferences.grounded_qa_max_documents);
  const normalizedLlmPreferences = normalizeLlmPreferences(preferences);
  llmConnections = normalizedLlmPreferences.llm_connections;
  llmRouting = sanitizeLlmRouting(llmConnections, normalizedLlmPreferences.llm_routing);
  ocrProvider = llmRouting.ocr.engine === "tesseract" ? "tesseract" : "llm";
  ocrAutoSwitch = normalizeOcrAutoSwitch(preferences.ocr_auto_switch);
  ocrImageDetail = normalizeOcrImageDetail(preferences.ocr_image_detail);
}

async function hydrateUserPreferencesForSession() {
  const preferences = await loadUserPreferences();
  applyUserPreferences(preferences);
  if (typeof searchAskThreadList !== "undefined" && searchAskThreadList) {
    await loadSearchAskThreads();
  }
  if (typeof readDocumentListStateFromUrl === "function") {
    readDocumentListStateFromUrl();
  }
}

function getAuthElements() {
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

// Avoid auth-gate flash on page load when the server rendered an authenticated shell.
if (document.documentElement.classList.contains("has-session")) {
  const { authGate, appShell } = getAuthElements();
  renderSortHeaders();
  authGate?.classList.add("view-hidden");
  appShell?.classList.remove("view-hidden");
}

function formatStatus(value) {
  if (!value) {
    return "-";
  }
  return value
    .split("_")
    .join(" ")
    .toUpperCase();
}

function logActivity(message) {
  const activityOutput = document.getElementById("activityOutput");
  if (!activityOutput) {
    return;
  }
  const now = new Date().toLocaleTimeString();
  activityOutput.textContent = `[${now}] ${message}\n${activityOutput.textContent}`;
}

function delay(ms) {
  return new Promise((resolve) => {
    window.setTimeout(resolve, ms);
  });
}

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}

function setAuthMessage(message, isError = false) {
  const { authMessage } = getAuthElements();
  if (!authMessage) {
    return;
  }
  authMessage.textContent = message;
  authMessage.style.color = isError ? "#9f3f1d" : "";
}

function setActiveAuthTab(tab) {
  const isSignUp = tab === "signup";
  const { authTabSignIn, authTabSignUp, authPanelSignIn, authPanelSignUp } = getAuthElements();
  authTabSignIn?.classList.toggle("is-active", !isSignUp);
  authTabSignIn?.setAttribute("aria-selected", String(!isSignUp));
  authTabSignUp?.classList.toggle("is-active", isSignUp);
  authTabSignUp?.setAttribute("aria-selected", String(isSignUp));
  authPanelSignIn?.classList.toggle("view-hidden", isSignUp);
  authPanelSignUp?.classList.toggle("view-hidden", !isSignUp);
}

function readInitialData() {
  if (initialDataCache !== undefined) {
    return initialDataCache;
  }
  const element = document.getElementById("paperwiseInitialData");
  if (!element) {
    initialDataCache = {};
    return initialDataCache;
  }
  try {
    initialDataCache = JSON.parse(element.textContent || "{}") || {};
  } catch {
    initialDataCache = {};
  }
  return initialDataCache;
}

function persistSession(user) {
  currentUser = user || null;
}

function renderSessionState() {
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

function clearSession() {
  persistSession(null);
  applyTheme(getDefaultTheme());
  llmConnections = [];
  llmRouting = createDefaultLlmRouting();
  ocrProvider = "llm";
  ocrAutoSwitch = false;
  ocrImageDetail = "auto";
  connectionTestStatuses.clear();
  docsPageSize = 20;
  if (typeof clearDocumentListStateForSession === "function") {
    clearDocumentListStateForSession();
  }
  if (typeof clearCatalogStateForSession === "function") {
    clearCatalogStateForSession();
  }
  if (typeof clearSearchStateForSession === "function") {
    clearSearchStateForSession();
  }
  refreshSettingsForm();
  renderSortHeaders();
  if (typeof renderActivityTokenTotal === "function") {
    renderActivityTokenTotal(0);
  }
  renderSessionState();
  refreshUploadAvailability();
}

function restoreSession() {
  const initialData = readInitialData();
  if (initialData.authenticated === true && initialData.current_user) {
    persistSession(initialData.current_user);
    renderSessionState();
    return;
  }
  clearSession();
}

function splitTags(value) {
  return value
    .split(",")
    .map((part) => part.trim())
    .filter((part) => part.length > 0);
}

function unique(values) {
  return [...new Set(values.filter((item) => item && item.trim()))];
}

function sortValues(values) {
  return [...values].sort((a, b) => a.localeCompare(b, undefined, { sensitivity: "base" }));
}

function getSortStateForTable(tableName) {
  if (tableName === "docs") {
    return typeof getDocumentListSortState === "function"
      ? getDocumentListSortState()
      : { field: "", direction: "" };
  }
  if (tableName === "tags") {
    return typeof tagStatsSort !== "undefined" ? tagStatsSort : { field: "", direction: "" };
  }
  if (tableName === "document-types") {
    return typeof documentTypesSort !== "undefined"
      ? documentTypesSort
      : { field: "", direction: "" };
  }
  return { field: "", direction: "" };
}

function getSortableHeaders() {
  return [...document.querySelectorAll("th[data-sort-table][data-sort-field]")];
}

function renderSortHeaders() {
  for (const header of getSortableHeaders()) {
    const tableName = header.dataset.sortTable || "";
    const field = header.dataset.sortField || "";
    const sortState = getSortStateForTable(tableName);
    const direction = sortState.field === field ? sortState.direction : "";
    const button = header.querySelector(".table-sort-button");
    const indicator = header.querySelector(".table-sort-indicator");
    header.setAttribute(
      "aria-sort",
      direction === "asc" ? "ascending" : direction === "desc" ? "descending" : "none"
    );
    if (indicator) {
      indicator.textContent = direction === "asc" ? "▲" : direction === "desc" ? "▼" : "⇅";
    }
    if (button) {
      const label = button.querySelector("span")?.textContent?.trim() || field;
      const nextDirection = getNextSortState(sortState, field).direction || "none";
      button.title = `Sort ${label} (${nextDirection})`;
    }
  }
}

function navigateToDocument(documentId) {
  const url = new URL("/ui/document", window.location.origin);
  url.searchParams.set("id", documentId);
  window.location.href = `${url.pathname}?${url.searchParams.toString()}`;
}

async function openDocumentFile(documentId) {
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

async function deleteDocumentById(documentId, options = {}) {
  const documentLabel = String(options.documentLabel || documentId || "").trim() || "this document";
  const confirmMessage = `Delete "${documentLabel}"? This permanently removes the file and its metadata.`;
  if (!window.confirm(confirmMessage)) {
    return false;
  }

  if (typeof prepareDocumentListDelete === "function") {
    prepareDocumentListDelete();
  }

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
      typeof buildDocumentsUrl === "function" ? buildDocumentsUrl() : "/ui/documents";
    return true;
  }

  if (typeof refreshDocumentListAfterDelete === "function") {
    await refreshDocumentListAfterDelete();
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

function hydrateSettingsFormFromInitialPreferences() {
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

function applyDocumentDetailPartial(partialRoot) {
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
}

async function initializeCurrentPageData() {
  if (typeof window.initializePaperwisePage !== "function") {
    return;
  }
  await window.initializePaperwisePage({
    authenticated: Boolean(currentUser),
    initialData: readInitialData(),
  });
}

async function openDocumentView(documentId) {
  const query = new URLSearchParams({ id: documentId });
  const payload = await fetchHtmlPartial(`/ui/partials/document?${query.toString()}`);
  applyDocumentDetailPartial(payload);
  logActivity(`Opened document ${documentId}`);
}

async function waitForDocumentReady(
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
    await hydrateUserPreferencesForSession();
    if (typeof applyDocumentListFiltersToControls === "function") {
      applyDocumentListFiltersToControls();
    }
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
    await hydrateUserPreferencesForSession();
    if (typeof applyDocumentListFiltersToControls === "function") {
      applyDocumentListFiltersToControls();
    }
    await initializeCurrentPageData();
  } catch (error) {
    setAuthMessage(error.message || "Failed to create account.", true);
  }
}

async function handleSignOutClick() {
  await apiFetch("/users/logout", { method: "POST", allowUnauthorized: true }).catch(() => {});
  clearSession();
  setAuthMessage("Signed out.");
}

function bindAppShellEvents() {
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

async function initializeApp() {
  restoreSession();
  if (!currentUser) {
    renderSortHeaders();
    return;
  }

  await hydrateUserPreferencesForSession();
  if (typeof applyDocumentListFiltersToControls === "function") {
    applyDocumentListFiltersToControls();
  }
  refreshSettingsForm();
  renderSortHeaders();
  refreshUploadAvailability();
  initializeCurrentPageData().catch((error) => {
    logActivity(`Initial page load failed: ${error.message}`);
  });
}

applyTheme(currentTheme);

document.addEventListener("DOMContentLoaded", () => {
  bindAppShellEvents();
  initializeApp().catch((error) => {
    setAuthMessage(error.message || "Failed to initialize app.", true);
  });
});
