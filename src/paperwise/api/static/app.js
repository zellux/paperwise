const uploadForm = document.getElementById("uploadForm");
const documentMetaForm = document.getElementById("documentMetaForm");
const backToDocsBtn = document.getElementById("backToDocsBtn");
const reprocessDocumentBtn = document.getElementById("reprocessDocumentBtn");
const viewDocumentFileBtn = document.getElementById("viewDocumentFileBtn");
const docsFilterForm = document.getElementById("docsFilterForm");
const clearFiltersBtn = document.getElementById("clearFiltersBtn");
const restartPendingBtn = document.getElementById("restartPendingBtn");
const pagePrevBtn = document.getElementById("pagePrevBtn");
const pageNextBtn = document.getElementById("pageNextBtn");
const pageIndicator = document.getElementById("pageIndicator");
const docsTotalLabel = document.getElementById("docsTotalLabel");
const settingsForm = document.getElementById("settingsForm");
const settingsThemeSelect = document.getElementById("settingsThemeSelect");
const settingsPageSizeSelect = document.getElementById("settingsPageSizeSelect");
const settingsLlmProviderSelect = document.getElementById("settingsLlmProviderSelect");
const settingsLlmModelInput = document.getElementById("settingsLlmModelInput");
const settingsLlmBaseUrlInput = document.getElementById("settingsLlmBaseUrlInput");
const settingsLlmApiKeyInput = document.getElementById("settingsLlmApiKeyInput");
const settingsTestLlmBtn = document.getElementById("settingsTestLlmBtn");
const settingsLlmTestStatus = document.getElementById("settingsLlmTestStatus");
const settingsOcrProviderSelect = document.getElementById("settingsOcrProviderSelect");
const authGate = document.getElementById("authGate");
const appShell = document.querySelector(".app-shell");
const signInForm = document.getElementById("signInForm");
const registerForm = document.getElementById("registerForm");
const authMessage = document.getElementById("authMessage");
const signOutBtn = document.getElementById("signOutBtn");
const sessionUserLabel = document.getElementById("sessionUserLabel");
const fileInput = document.getElementById("fileInput");
const uploadDropzone = document.getElementById("uploadDropzone");
const uploadSelectionLabel = document.getElementById("uploadSelectionLabel");
const uploadSubmitBtn = document.getElementById("uploadSubmitBtn");

const metaTitleInput = document.getElementById("metaTitle");
const metaDateInput = document.getElementById("metaDate");
const metaCorrespondentInput = document.getElementById("metaCorrespondent");
const metaTypeInput = document.getElementById("metaType");
const metaTagsInput = document.getElementById("metaTags");
const detailDocId = document.getElementById("detailDocId");
const detailOwnerId = document.getElementById("detailOwnerId");
const detailFilename = document.getElementById("detailFilename");
const detailStatus = document.getElementById("detailStatus");
const detailCreatedAt = document.getElementById("detailCreatedAt");
const detailContentType = document.getElementById("detailContentType");
const detailSizeBytes = document.getElementById("detailSizeBytes");
const detailChecksum = document.getElementById("detailChecksum");
const detailBlobUri = document.getElementById("detailBlobUri");
const documentHistoryList = document.getElementById("documentHistoryList");
const filterTag = document.getElementById("filterTag");
const filterCorrespondent = document.getElementById("filterCorrespondent");
const filterType = document.getElementById("filterType");
const filterStatus = document.getElementById("filterStatus");
const filterQuery = document.getElementById("filterQuery");
const filterSelects = [filterTag, filterCorrespondent, filterType, filterStatus];

const activityOutput = document.getElementById("activityOutput");
const docsTableBody = document.getElementById("docsTableBody");
const tagsTableBody = document.getElementById("tagsTableBody");
const documentTypesTableBody = document.getElementById("documentTypesTableBody");
const pendingTableBody = document.getElementById("pendingTableBody");
const processedDocsTableBody = document.getElementById("processedDocsTableBody");
const activityTokenTotal = document.getElementById("activityTokenTotal");
const navLinks = [...document.querySelectorAll(".nav-link")];
const views = [...document.querySelectorAll(".view")];
const filterDropdownState = new Map();
let activeFilterDropdown = null;
let currentViewId = "section-docs";
const VIEW_ID_TO_PARAM = {
  "section-docs": "docs",
  "section-document": "document",
  "section-tags": "tags",
  "section-document-types": "document-types",
  "section-pending": "pending",
  "section-upload": "upload",
  "section-activity": "activity",
  "section-settings": "settings",
};
const VIEW_PARAM_TO_ID = Object.fromEntries(
  Object.entries(VIEW_ID_TO_PARAM).map(([viewId, param]) => [param, viewId])
);
const PATH_TO_VIEW_ID = {
  "/ui/documents": "section-docs",
  "/ui/document": "section-document",
  "/ui/tags": "section-tags",
  "/ui/document-types": "section-document-types",
  "/ui/pending": "section-pending",
  "/ui/upload": "section-upload",
  "/ui/activity": "section-activity",
  "/ui/settings": "section-settings",
};
const VIEW_ID_TO_PATH = {
  "section-docs": "/ui/documents",
  "section-document": "/ui/document",
  "section-tags": "/ui/tags",
  "section-document-types": "/ui/document-types",
  "section-pending": "/ui/pending",
  "section-upload": "/ui/upload",
  "section-activity": "/ui/activity",
  "section-settings": "/ui/settings",
};

let currentDocumentId = "";
let authToken = window.localStorage.getItem("paperwise.auth.token") || "";
let currentUser = null;
let userPreferenceSaveTimer = null;
const SUPPORTED_THEMES = ["atlas", "ledger", "moss", "ember"];
let currentTheme = "atlas";
const SUPPORTED_LLM_PROVIDERS = ["openai", "claude", "gemini", "custom"];
const LLM_PROVIDER_DEFAULTS = {
  openai: {
    model: "gpt-4.1-mini",
    base_url: "https://api.openai.com/v1",
  },
  claude: {
    model: "claude-3-5-sonnet-latest",
    base_url: "https://api.anthropic.com",
  },
  gemini: {
    model: "gemini-2.0-flash",
    base_url: "https://generativelanguage.googleapis.com/v1beta",
  },
};
let llmSettings = {
  provider: "",
  model: "",
  base_url: "",
  api_key: "",
};
const SUPPORTED_OCR_PROVIDERS = ["tesseract", "llm"];
let ocrProvider = "tesseract";
let docsFilters = {
  q: "",
  tag: [],
  correspondent: [],
  document_type: [],
  status: ["ready"],
};
let docsPage = 1;
let docsPageSize = 20;
let docsTotalCount = 0;

function normalizePageSize(value) {
  const size = Number(value);
  if (!Number.isInteger(size) || size <= 0) {
    return 20;
  }
  return size;
}

function cloneDocsFilters(filters) {
  return {
    q: String(filters?.q || "").trim(),
    tag: [...(filters?.tag || [])],
    correspondent: [...(filters?.correspondent || [])],
    document_type: [...(filters?.document_type || [])],
    status: [...(filters?.status || ["ready"])],
  };
}

function sanitizeDocsFilters(filters) {
  const normalized = cloneDocsFilters(filters);
  normalized.tag = unique(normalized.tag);
  normalized.correspondent = unique(normalized.correspondent);
  normalized.document_type = unique(normalized.document_type);
  normalized.status = unique(normalized.status);
  if (!normalized.status.length) {
    normalized.status = ["ready"];
  }
  return normalized;
}

function hasExplicitNavigationState() {
  const path = window.location.pathname.replace(/\/+$/, "") || "/";
  const params = new URLSearchParams(window.location.search);
  if (params.toString()) {
    return true;
  }
  return path !== "/" && Object.prototype.hasOwnProperty.call(PATH_TO_VIEW_ID, path);
}

function normalizeThemeName(value) {
  const normalized = String(value || "").trim().toLowerCase();
  if (SUPPORTED_THEMES.includes(normalized)) {
    return normalized;
  }
  return "atlas";
}

function normalizeLlmProvider(value) {
  const normalized = String(value || "").trim().toLowerCase();
  if (SUPPORTED_LLM_PROVIDERS.includes(normalized)) {
    return normalized;
  }
  return "";
}

function getLlmProviderDefaults(provider) {
  const normalized = normalizeLlmProvider(provider);
  if (!normalized) {
    return null;
  }
  return LLM_PROVIDER_DEFAULTS[normalized] || null;
}

function normalizeOcrProvider(value) {
  const normalized = String(value || "").trim().toLowerCase();
  if (SUPPORTED_OCR_PROVIDERS.includes(normalized)) {
    return normalized;
  }
  return "tesseract";
}

function applyTheme(themeName) {
  currentTheme = normalizeThemeName(themeName);
  const classNames = SUPPORTED_THEMES.map((name) => `theme-${name}`);
  document.body.classList.remove(...classNames);
  document.body.classList.add(`theme-${currentTheme}`);
  if (settingsThemeSelect && settingsThemeSelect.value !== currentTheme) {
    settingsThemeSelect.value = currentTheme;
  }
}

function renderSettingsForm() {
  if (settingsThemeSelect && settingsThemeSelect.value !== currentTheme) {
    settingsThemeSelect.value = currentTheme;
  }
  if (settingsPageSizeSelect && settingsPageSizeSelect.value !== String(docsPageSize)) {
    settingsPageSizeSelect.value = String(docsPageSize);
  }
  if (settingsLlmProviderSelect && settingsLlmProviderSelect.value !== llmSettings.provider) {
    settingsLlmProviderSelect.value = llmSettings.provider;
  }
  if (settingsLlmModelInput && settingsLlmModelInput.value !== llmSettings.model) {
    settingsLlmModelInput.value = llmSettings.model;
  }
  if (settingsLlmBaseUrlInput && settingsLlmBaseUrlInput.value !== llmSettings.base_url) {
    settingsLlmBaseUrlInput.value = llmSettings.base_url;
  }
  if (settingsLlmApiKeyInput && settingsLlmApiKeyInput.value !== llmSettings.api_key) {
    settingsLlmApiKeyInput.value = llmSettings.api_key;
  }
  if (settingsOcrProviderSelect && settingsOcrProviderSelect.value !== ocrProvider) {
    settingsOcrProviderSelect.value = ocrProvider;
  }
  syncUploadAvailability();
}

function readLlmSettingsFromControls() {
  return {
    provider: normalizeLlmProvider(settingsLlmProviderSelect?.value || llmSettings.provider),
    model: String(settingsLlmModelInput?.value || "").trim(),
    base_url: String(settingsLlmBaseUrlInput?.value || "").trim(),
    api_key: String(settingsLlmApiKeyInput?.value || "").trim(),
  };
}

function applyLlmProviderDefaultsToControls(provider, options = {}) {
  const force = options.force === true;
  const defaults = getLlmProviderDefaults(provider);
  if (!defaults) {
    return;
  }
  if (settingsLlmModelInput) {
    const currentModel = String(settingsLlmModelInput.value || "").trim();
    if (force || !currentModel) {
      settingsLlmModelInput.value = defaults.model;
    }
  }
  if (settingsLlmBaseUrlInput) {
    const currentBaseUrl = String(settingsLlmBaseUrlInput.value || "").trim();
    if (force || !currentBaseUrl) {
      settingsLlmBaseUrlInput.value = defaults.base_url;
    }
  }
}

function getLlmUploadBlockReasonForSettings(candidateSettings) {
  const provider = normalizeLlmProvider(candidateSettings?.provider);
  if (!provider) {
    return "configure an LLM provider in Settings.";
  }
  if (!String(candidateSettings?.api_key || "").trim()) {
    return "add your LLM API key in Settings.";
  }
  if (provider === "custom" && !String(candidateSettings?.base_url || "").trim()) {
    return "set a custom LLM base URL in Settings.";
  }
  return "";
}

function getLlmUploadBlockReason() {
  return getLlmUploadBlockReasonForSettings(llmSettings);
}

function setSettingsLlmTestStatus(message, tone = "") {
  if (!settingsLlmTestStatus) {
    return;
  }
  settingsLlmTestStatus.textContent = message || "";
  settingsLlmTestStatus.classList.remove("is-success", "is-error");
  if (tone === "success") {
    settingsLlmTestStatus.classList.add("is-success");
  } else if (tone === "error") {
    settingsLlmTestStatus.classList.add("is-error");
  }
}

function syncUploadAvailability(options = {}) {
  const announce = options.announce === true;
  const navigateToSettings = options.navigateToSettings === true;
  const reason = getLlmUploadBlockReason();
  const blocked = Boolean(reason);

  if (uploadSubmitBtn) {
    uploadSubmitBtn.disabled = blocked;
  }
  if (fileInput) {
    fileInput.disabled = blocked;
  }
  if (uploadDropzone) {
    uploadDropzone.classList.toggle("is-disabled", blocked);
    uploadDropzone.setAttribute("aria-disabled", blocked ? "true" : "false");
    uploadDropzone.tabIndex = blocked ? -1 : 0;
  }

  if (blocked) {
    if (uploadSelectionLabel) {
      uploadSelectionLabel.textContent = "Upload disabled: update LLM settings first.";
    }
    if (announce) {
      logActivity(`Upload blocked: ${reason} Go to Settings first.`);
    }
    if (navigateToSettings) {
      setActiveView("section-settings");
      setActiveNav("section-settings");
      syncUrlFromFilters();
      renderSettingsForm();
    }
    return false;
  }

  updateSelectedFilesLabel();
  return true;
}

async function loadUserPreferences() {
  if (!authToken || !currentUser) {
    return {};
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
  if (!authToken || !currentUser) {
    return;
  }
  const payload = {
    preferences: {
      docs_filters: sanitizeDocsFilters(docsFilters),
      last_view: currentViewId,
      ui_theme: currentTheme,
      docs_page_size: docsPageSize,
      llm_provider: llmSettings.provider,
      llm_model: llmSettings.model,
      llm_base_url: llmSettings.base_url,
      llm_api_key: llmSettings.api_key,
      ocr_provider: ocrProvider,
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

function scheduleUserPreferenceSave() {
  if (!authToken || !currentUser) {
    return;
  }
  if (userPreferenceSaveTimer) {
    window.clearTimeout(userPreferenceSaveTimer);
  }
  userPreferenceSaveTimer = window.setTimeout(() => {
    userPreferenceSaveTimer = null;
    saveUserPreferences().catch(() => {});
  }, 250);
}

function applyUserPreferences(preferences, options = {}) {
  const includeLastView = options.includeLastView !== false;
  if (!preferences || typeof preferences !== "object") {
    return;
  }
  if (preferences.docs_filters && typeof preferences.docs_filters === "object") {
    docsFilters = sanitizeDocsFilters(preferences.docs_filters);
  }
  if (
    includeLastView &&
    typeof preferences.last_view === "string" &&
    views.some((view) => view.id === preferences.last_view)
  ) {
    currentViewId = preferences.last_view;
  }
  if (typeof preferences.ui_theme === "string") {
    applyTheme(preferences.ui_theme);
  }
  if (preferences.docs_page_size !== undefined) {
    docsPageSize = normalizePageSize(preferences.docs_page_size);
  }
  llmSettings = {
    provider: normalizeLlmProvider(preferences.llm_provider),
    model: String(preferences.llm_model || "").trim(),
    base_url: String(preferences.llm_base_url || "").trim(),
    api_key: String(preferences.llm_api_key || "").trim(),
  };
  const defaults = getLlmProviderDefaults(llmSettings.provider);
  if (defaults) {
    if (!llmSettings.model) {
      llmSettings.model = defaults.model;
    }
    if (!llmSettings.base_url) {
      llmSettings.base_url = defaults.base_url;
    }
  }
  ocrProvider = normalizeOcrProvider(preferences.ocr_provider);
}

async function hydrateUserPreferencesForSession() {
  const path = window.location.pathname.replace(/\/+$/, "") || "/";
  const explicitPath = path !== "/" && Object.prototype.hasOwnProperty.call(PATH_TO_VIEW_ID, path);
  const preferences = await loadUserPreferences();
  applyUserPreferences(preferences, { includeLastView: !explicitPath });
  if (hasExplicitNavigationState()) {
    readFiltersFromUrl();
    return;
  }
  syncUrlFromFilters();
}

// Avoid auth-gate flash on page load when we already have a stored token.
if (authToken && authGate && appShell) {
  authGate.classList.add("view-hidden");
  appShell.classList.remove("view-hidden");
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

function formatBytes(value) {
  const bytes = Number(value || 0);
  if (!Number.isFinite(bytes) || bytes <= 0) {
    return "0 B";
  }
  if (bytes < 1024) {
    return `${bytes} B`;
  }
  const kb = bytes / 1024;
  if (kb < 1024) {
    return `${kb.toFixed(1)} KB`;
  }
  const mb = kb / 1024;
  return `${mb.toFixed(2)} MB`;
}

function formatHistoryEventType(value) {
  const labels = {
    metadata_changed: "Metadata changed",
    tags_added: "Tags added",
    tags_removed: "Tags removed",
    file_moved: "File moved",
    processing_restarted: "Processing restarted",
    processing_completed: "Processing completed",
  };
  return labels[value] || formatStatus(value || "update");
}

function formatHistoryActor(event) {
  if (event.actor_type === "user") {
    return event.actor_id ? `User: ${event.actor_id}` : "User";
  }
  return "System";
}

function stringifyHistoryValue(value) {
  if (value === null || value === undefined || value === "") {
    return "(empty)";
  }
  return String(value);
}

function buildHistoryChangeLines(event) {
  const changes = event.changes || {};
  if (event.event_type === "metadata_changed") {
    const lines = [];
    for (const [field, values] of Object.entries(changes)) {
      const before = stringifyHistoryValue(values?.before);
      const after = stringifyHistoryValue(values?.after);
      lines.push(`${field}: ${before} -> ${after}`);
    }
    return lines;
  }
  if (event.event_type === "tags_added") {
    const tags = Array.isArray(changes.tags) ? changes.tags : [];
    return [tags.length ? `Added: ${tags.join(", ")}` : "Added tags"];
  }
  if (event.event_type === "tags_removed") {
    const tags = Array.isArray(changes.tags) ? changes.tags : [];
    return [tags.length ? `Removed: ${tags.join(", ")}` : "Removed tags"];
  }
  if (event.event_type === "file_moved") {
    const fromPath = toRelativeBlobPath(changes.from_blob_uri || "");
    const toPath = toRelativeBlobPath(changes.to_blob_uri || "");
    return [`From: ${fromPath}`, `To: ${toPath}`];
  }
  if (event.event_type === "processing_restarted") {
    const before = stringifyHistoryValue(changes.status?.before);
    const after = stringifyHistoryValue(changes.status?.after);
    return [`Status: ${before} -> ${after}`];
  }
  if (event.event_type === "processing_completed") {
    const before = stringifyHistoryValue(changes.status?.before);
    const after = stringifyHistoryValue(changes.status?.after);
    return [`Status: ${before} -> ${after}`];
  }
  try {
    return [JSON.stringify(changes)];
  } catch {
    return ["Details unavailable"];
  }
}

function renderDocumentHistory(events) {
  if (!documentHistoryList) {
    return;
  }
  if (!Array.isArray(events) || !events.length) {
    documentHistoryList.innerHTML =
      '<p class="document-history-empty">No history entries yet.</p>';
    return;
  }

  documentHistoryList.innerHTML = "";
  for (const event of events) {
    const item = document.createElement("article");
    item.className = "document-history-item";

    const header = document.createElement("div");
    header.className = "document-history-header";

    const type = document.createElement("span");
    type.className = "document-history-type";
    type.textContent = formatHistoryEventType(event.event_type);

    const meta = document.createElement("span");
    meta.className = "document-history-meta";
    const timestamp = event.created_at ? new Date(event.created_at).toLocaleString() : "-";
    meta.textContent = `${formatHistoryActor(event)} | ${event.source || "-"} | ${timestamp}`;

    const changes = document.createElement("div");
    changes.className = "document-history-changes";
    for (const line of buildHistoryChangeLines(event)) {
      const changeLine = document.createElement("p");
      changeLine.className = "document-history-change";
      changeLine.textContent = line;
      changes.appendChild(changeLine);
    }

    header.appendChild(type);
    header.appendChild(meta);
    item.appendChild(header);
    item.appendChild(changes);
    documentHistoryList.appendChild(item);
  }
}

function toRelativeBlobPath(blobUri) {
  if (!blobUri) {
    return "-";
  }
  try {
    const url = new URL(blobUri);
    if (url.protocol !== "file:") {
      return blobUri;
    }
    const absolutePath = decodeURIComponent(url.pathname);
    const marker = "/local/object-store/";
    const idx = absolutePath.indexOf(marker);
    if (idx >= 0) {
      return absolutePath.slice(idx + marker.length);
    }
    return absolutePath.replace(/^\/+/, "");
  } catch {
    return blobUri;
  }
}

function logActivity(message) {
  const now = new Date().toLocaleTimeString();
  activityOutput.textContent = `[${now}] ${message}\n${activityOutput.textContent}`;
}

function delay(ms) {
  return new Promise((resolve) => {
    window.setTimeout(resolve, ms);
  });
}

const SUPPORTED_UPLOAD_EXTENSIONS = new Set([".pdf", ".txt", ".md", ".markdown", ".doc", ".docx"]);

function collectSupportedFiles(fileList) {
  return [...(fileList || [])].filter((file) => {
    const name = (file.name || "").toLowerCase();
    const ext = name.includes(".") ? `.${name.split(".").pop()}` : "";
    return SUPPORTED_UPLOAD_EXTENSIONS.has(ext);
  });
}

function updateSelectedFilesLabel() {
  if (!uploadSelectionLabel || !fileInput) {
    return;
  }
  const files = fileInput.files ? [...fileInput.files] : [];
  if (!files.length) {
    uploadSelectionLabel.textContent = "Supports: PDF, TXT, MD, DOCX, DOC";
    return;
  }
  if (files.length === 1) {
    uploadSelectionLabel.textContent = `Selected: ${files[0].name}`;
    return;
  }
  uploadSelectionLabel.textContent = `Selected ${files.length} files`;
}

function setSelectedFiles(files) {
  if (!fileInput) {
    return;
  }
  const data = new DataTransfer();
  for (const file of files) {
    data.items.add(file);
  }
  fileInput.files = data.files;
  updateSelectedFilesLabel();
}

async function uploadDocumentFile(file) {
  const form = new FormData();
  form.append("file", file);
  const response = await apiFetch("/documents", { method: "POST", body: form });
  const payload = await response.json();
  if (!response.ok) {
    throw new Error(payload.detail || response.statusText);
  }
  return payload;
}

function setAuthMessage(message, isError = false) {
  if (!authMessage) {
    return;
  }
  authMessage.textContent = message;
  authMessage.style.color = isError ? "#9f3f1d" : "";
}

function persistSession(token, user) {
  authToken = token || "";
  currentUser = user || null;
  if (authToken) {
    window.localStorage.setItem("paperwise.auth.token", authToken);
  } else {
    window.localStorage.removeItem("paperwise.auth.token");
  }
}

function renderSessionState() {
  const signedIn = Boolean(authToken && currentUser);
  authGate.classList.toggle("view-hidden", signedIn);
  appShell.classList.toggle("view-hidden", !signedIn);
  if (sessionUserLabel) {
    sessionUserLabel.textContent = signedIn
      ? `${currentUser.full_name} (${currentUser.email})`
      : "Not signed in";
  }
}

function clearSession() {
  persistSession("", null);
  applyTheme("atlas");
  llmSettings = {
    provider: "",
    model: "",
    base_url: "",
    api_key: "",
  };
  ocrProvider = "tesseract";
  docsPage = 1;
  docsPageSize = 20;
  docsFilters = sanitizeDocsFilters({
    tag: [],
    correspondent: [],
    document_type: [],
    status: ["ready"],
  });
  currentViewId = "section-docs";
  renderSettingsForm();
  renderActivityTokenTotal(0);
  renderSessionState();
  syncUploadAvailability();
}

async function apiFetch(url, options = {}) {
  const headers = new Headers(options.headers || {});
  if (authToken) {
    headers.set("Authorization", `Bearer ${authToken}`);
  }
  const response = await window.fetch(url, { ...options, headers });
  if (response.status === 401) {
    clearSession();
    throw new Error("Authentication required");
  }
  return response;
}

async function restoreSession() {
  if (!authToken) {
    renderSessionState();
    return;
  }
  try {
    const response = await apiFetch("/users/me");
    if (!response.ok) {
      clearSession();
      return;
    }
    currentUser = await response.json();
  } catch {
    clearSession();
    return;
  }
  renderSessionState();
}

function setActiveNav(targetId) {
  for (const link of navLinks) {
    link.classList.toggle("active", link.dataset.target === targetId);
  }
}

function setActiveView(targetId) {
  if (!views.some((view) => view.id === targetId)) {
    return;
  }
  currentViewId = targetId;
  for (const view of views) {
    view.classList.toggle("view-hidden", view.id !== targetId);
  }
}

function getCurrentPathViewId() {
  const path = window.location.pathname.replace(/\/+$/, "") || "/";
  return PATH_TO_VIEW_ID[path] || "section-docs";
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

function getFilterKey(selectEl) {
  if (selectEl === filterTag) {
    return "tag";
  }
  if (selectEl === filterCorrespondent) {
    return "correspondent";
  }
  if (selectEl === filterType) {
    return "document_type";
  }
  return "status";
}

function getSelectedValues(selectEl) {
  return [...selectEl.selectedOptions].map((option) => option.value).filter((value) => value);
}

function setSelectedValues(selectEl, values) {
  const selected = new Set(values || []);
  for (const option of selectEl.options) {
    option.selected = selected.has(option.value);
  }
}

function summarizeSelectedValues(selectedValues, selectEl) {
  if (!selectedValues.length) {
    return "Any";
  }
  const displayValues = selectedValues.map((value) =>
    selectEl === filterStatus ? formatStatus(value) : value
  );
  if (selectedValues.length === 1) {
    return displayValues[0];
  }
  return `${selectedValues.length} selected`;
}

function closeFilterDropdown(selectEl) {
  const state = filterDropdownState.get(selectEl);
  if (!state) {
    return;
  }
  state.panel.hidden = true;
  state.trigger.setAttribute("aria-expanded", "false");
  state.chip.classList.remove("is-open");
  if (activeFilterDropdown === selectEl) {
    activeFilterDropdown = null;
  }
}

function openFilterDropdown(selectEl) {
  if (activeFilterDropdown && activeFilterDropdown !== selectEl) {
    closeFilterDropdown(activeFilterDropdown);
  }
  const state = filterDropdownState.get(selectEl);
  if (!state) {
    return;
  }
  state.panel.hidden = false;
  state.trigger.setAttribute("aria-expanded", "true");
  state.chip.classList.add("is-open");
  activeFilterDropdown = selectEl;
  state.search.focus();
}

async function toggleFilterOption(selectEl, value) {
  for (const option of selectEl.options) {
    if (option.value === value) {
      option.selected = !option.selected;
      break;
    }
  }
  await applyFiltersFromControls();
}

function renderFilterDropdownOptions(selectEl) {
  const state = filterDropdownState.get(selectEl);
  if (!state) {
    return;
  }

  const query = state.search.value.trim().toLowerCase();
  const options = [...selectEl.options].filter((option) => {
    if (!query) {
      return true;
    }
    return option.textContent.toLowerCase().includes(query);
  });

  state.options.innerHTML = "";

  if (!options.length) {
    const empty = document.createElement("div");
    empty.className = "filter-dropdown-empty";
    empty.textContent = "No matches.";
    state.options.appendChild(empty);
    return;
  }

  for (const option of options) {
    const row = document.createElement("button");
    row.type = "button";
    row.className = "filter-dropdown-option";
    row.dataset.value = option.value;
    row.setAttribute("aria-pressed", option.selected ? "true" : "false");
    if (option.selected) {
      row.classList.add("is-selected");
    }

    const check = document.createElement("span");
    check.className = "filter-dropdown-check";
    check.textContent = option.selected ? "x" : "";

    const label = document.createElement("span");
    label.className = "filter-dropdown-option-label";
    label.textContent = option.textContent;

    row.appendChild(check);
    row.appendChild(label);
    state.options.appendChild(row);
  }
}

function renderFilterDropdown(selectEl) {
  const state = filterDropdownState.get(selectEl);
  if (!state) {
    return;
  }
  const selectedValues = getSelectedValues(selectEl);
  state.value.textContent = summarizeSelectedValues(selectedValues, selectEl);
  renderFilterDropdownOptions(selectEl);
}

function setupFilterDropdown(selectEl) {
  if (!selectEl || filterDropdownState.has(selectEl)) {
    return;
  }

  const chip = selectEl.closest(".filter-chip");
  if (!chip) {
    return;
  }

  const labelText = chip.querySelector(".chip-prefix")?.textContent?.trim() || "Filter";
  selectEl.classList.add("filter-select-native");

  const dropdown = document.createElement("div");
  dropdown.className = "filter-dropdown";

  const trigger = document.createElement("button");
  trigger.type = "button";
  trigger.className = "filter-dropdown-trigger";
  trigger.setAttribute("aria-expanded", "false");

  const triggerValue = document.createElement("span");
  triggerValue.className = "filter-dropdown-value";
  triggerValue.textContent = "Any";

  const triggerCaret = document.createElement("span");
  triggerCaret.className = "filter-dropdown-caret";
  triggerCaret.textContent = "▾";

  trigger.appendChild(triggerValue);
  trigger.appendChild(triggerCaret);

  const panel = document.createElement("div");
  panel.className = "filter-dropdown-panel";
  panel.hidden = true;

  const search = document.createElement("input");
  search.type = "search";
  search.className = "filter-dropdown-search";
  search.placeholder = `Filter ${labelText.toLowerCase()}`;

  const options = document.createElement("div");
  options.className = "filter-dropdown-options";

  panel.appendChild(search);
  panel.appendChild(options);
  dropdown.appendChild(trigger);
  dropdown.appendChild(panel);
  chip.appendChild(dropdown);

  filterDropdownState.set(selectEl, {
    chip,
    trigger,
    panel,
    search,
    options,
    value: triggerValue,
  });

  trigger.addEventListener("click", () => {
    if (panel.hidden) {
      openFilterDropdown(selectEl);
      renderFilterDropdownOptions(selectEl);
      return;
    }
    closeFilterDropdown(selectEl);
  });

  search.addEventListener("input", () => {
    renderFilterDropdownOptions(selectEl);
  });

  options.addEventListener("click", async (event) => {
    const button = event.target.closest(".filter-dropdown-option");
    if (!button) {
      return;
    }
    const value = button.dataset.value;
    if (!value) {
      return;
    }
    await toggleFilterOption(selectEl, value);
    renderFilterDropdown(selectEl);
  });
}

function applyFiltersToControls() {
  if (filterQuery) {
    filterQuery.value = docsFilters.q || "";
  }
  setSelectedValues(filterTag, docsFilters.tag);
  setSelectedValues(filterCorrespondent, docsFilters.correspondent);
  setSelectedValues(filterType, docsFilters.document_type);
  setSelectedValues(filterStatus, docsFilters.status);
  for (const selectEl of filterSelects) {
    renderFilterDropdown(selectEl);
  }
}

function setSelectOptions(selectEl, values) {
  const key = getFilterKey(selectEl);
  const selectedValues = docsFilters[key] || [];
  const mergedValues = sortValues(unique([...values, ...selectedValues]));
  selectEl.innerHTML = "";

  for (const value of mergedValues) {
    const option = document.createElement("option");
    option.value = value;
    option.textContent = key === "status" ? formatStatus(value) : value;
    selectEl.appendChild(option);
  }
  setSelectedValues(selectEl, selectedValues);
  renderFilterDropdown(selectEl);
}

function readFiltersFromControls() {
  docsFilters.q = String(filterQuery?.value || "").trim();
  docsFilters.tag = getSelectedValues(filterTag);
  docsFilters.correspondent = getSelectedValues(filterCorrespondent);
  docsFilters.document_type = getSelectedValues(filterType);
  docsFilters.status = getSelectedValues(filterStatus);
}

function refreshFilterOptionsFromDocuments(documents) {
  const tags = new Set();
  const correspondents = new Set();
  const documentTypes = new Set();
  const statuses = new Set();

  for (const doc of documents) {
    if (doc.status) {
      statuses.add(doc.status);
    }
    const metadata = doc.llm_metadata;
    if (!metadata) {
      continue;
    }
    if (metadata.correspondent) {
      correspondents.add(metadata.correspondent);
    }
    if (metadata.document_type) {
      documentTypes.add(metadata.document_type);
    }
    for (const tag of metadata.tags || []) {
      if (tag) {
        tags.add(tag);
      }
    }
  }

  setSelectOptions(filterTag, [...tags]);
  setSelectOptions(filterCorrespondent, [...correspondents]);
  setSelectOptions(filterType, [...documentTypes]);
  setSelectOptions(filterStatus, ["received", "processing", "ready", ...statuses]);
}

function syncUrlFromFilters() {
  const url = new URL(window.location.href);
  url.searchParams.delete("q");
  url.searchParams.delete("tag");
  url.searchParams.delete("correspondent");
  url.searchParams.delete("document_type");
  url.searchParams.delete("status");
  url.searchParams.delete("view");
  url.searchParams.delete("page");
  url.searchParams.delete("page_size");

  if (docsFilters.q) {
    url.searchParams.set("q", docsFilters.q);
  }
  for (const value of docsFilters.tag) {
    url.searchParams.append("tag", value);
  }
  for (const value of docsFilters.correspondent) {
    url.searchParams.append("correspondent", value);
  }
  for (const value of docsFilters.document_type) {
    url.searchParams.append("document_type", value);
  }
  for (const value of docsFilters.status) {
    url.searchParams.append("status", value);
  }
  if (docsPage > 1) {
    url.searchParams.set("page", String(docsPage));
  }
  if (docsPageSize !== 20) {
    url.searchParams.set("page_size", String(docsPageSize));
  }
  const viewPath = VIEW_ID_TO_PATH[currentViewId];
  if (viewPath) {
    url.pathname = viewPath;
  }

  const qs = url.searchParams.toString();
  window.history.replaceState(null, "", qs ? `${url.pathname}?${qs}` : url.pathname);
  scheduleUserPreferenceSave();
}

function readFiltersFromUrl() {
  const params = new URLSearchParams(window.location.search);
  docsFilters.q = String(params.get("q") || "").trim();
  docsFilters.tag = unique(params.getAll("tag"));
  docsFilters.correspondent = unique(params.getAll("correspondent"));
  docsFilters.document_type = unique(params.getAll("document_type"));
  const statusValues = unique(params.getAll("status"));
  docsFilters.status = statusValues.length ? statusValues : ["ready"];
  const pageValue = Number(params.get("page") || "1");
  docsPage = Number.isInteger(pageValue) && pageValue > 0 ? pageValue : 1;
  const pageSizeValue = params.get("page_size") || String(docsPageSize || 20);
  docsPageSize = normalizePageSize(pageSizeValue);
  const viewFromUrl = params.get("view");
  const mappedViewId = viewFromUrl ? (VIEW_PARAM_TO_ID[viewFromUrl] || viewFromUrl) : "";
  const pathViewId = getCurrentPathViewId();
  if (pathViewId && views.some((view) => view.id === pathViewId)) {
    currentViewId = pathViewId;
  } else if (mappedViewId && views.some((view) => view.id === mappedViewId)) {
    // Backward compatibility for old links that use ?view=...
    currentViewId = mappedViewId;
  } else {
    currentViewId = "section-docs";
  }
}

async function applyFiltersFromControls() {
  readFiltersFromControls();
  docsPage = 1;
  syncUrlFromFilters();
  await loadDocumentsList();
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

function createActionIcon(name) {
  const ns = "http://www.w3.org/2000/svg";
  const svg = document.createElementNS(ns, "svg");
  svg.setAttribute("viewBox", "0 0 24 24");
  svg.setAttribute("fill", "none");
  svg.setAttribute("stroke", "currentColor");
  svg.setAttribute("stroke-width", "2");
  svg.setAttribute("stroke-linecap", "round");
  svg.setAttribute("stroke-linejoin", "round");
  svg.classList.add("action-icon-svg");

  const addPath = (d) => {
    const path = document.createElementNS(ns, "path");
    path.setAttribute("d", d);
    svg.appendChild(path);
  };
  const addLine = (x1, y1, x2, y2) => {
    const line = document.createElementNS(ns, "line");
    line.setAttribute("x1", x1);
    line.setAttribute("y1", y1);
    line.setAttribute("x2", x2);
    line.setAttribute("y2", y2);
    svg.appendChild(line);
  };
  const addPolyline = (points) => {
    const polyline = document.createElementNS(ns, "polyline");
    polyline.setAttribute("points", points);
    svg.appendChild(polyline);
  };

  if (name === "external-link") {
    addPath("M15 3h6v6");
    addPath("M10 14 21 3");
    addPath("M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6");
    return svg;
  }
  if (name === "file-text") {
    addPath("M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z");
    addPolyline("14 2 14 8 20 8");
    addLine("16", "13", "8", "13");
    addLine("16", "17", "8", "17");
    addPolyline("10 9 9 9 8 9");
    return svg;
  }
  if (name === "eye") {
    addPath("M2.062 12.348a1 1 0 0 1 0-.696 10.75 10.75 0 0 1 19.876 0 1 1 0 0 1 0 .696 10.75 10.75 0 0 1-19.876 0");
    addPath("M12 15a3 3 0 1 0 0-6 3 3 0 0 0 0 6");
    return svg;
  }
  if (name === "edit") {
    addPath("M12 20h9");
    addPath("M16.5 3.5a2.1 2.1 0 0 1 3 3L7 19l-4 1 1-4Z");
    return svg;
  }

  addPath("M12 5v14");
  addPath("M5 12h14");
  return svg;
}

function createIconActionButton({ icon, label, onClick }) {
  const button = document.createElement("button");
  button.className = "action-icon-btn";
  button.type = "button";
  button.title = label;
  button.setAttribute("aria-label", label);
  button.appendChild(createActionIcon(icon));
  button.addEventListener("click", onClick);
  return button;
}

function getSuggestedTitle(doc) {
  if (doc.llm_metadata && doc.llm_metadata.suggested_title) {
    return doc.llm_metadata.suggested_title;
  }
  return "(Pending title)";
}

function renderDocsList(documents) {
  if (!documents.length) {
    docsTableBody.innerHTML = '<tr><td colspan="7">No documents found.</td></tr>';
    return;
  }
  docsTableBody.innerHTML = "";
  for (const doc of documents) {
    const row = document.createElement("tr");

    let suggestedTitle = "-";
    let documentType = "-";
    let correspondent = "-";
    let tags = "-";
    let documentDate = "-";
    if (doc.llm_metadata) {
      const m = doc.llm_metadata;
      suggestedTitle = m.suggested_title || "-";
      documentType = m.document_type || "-";
      correspondent = m.correspondent || "-";
      tags = Array.isArray(m.tags) && m.tags.length ? m.tags.join(", ") : "-";
      documentDate = m.document_date || "-";
    }

    const titleCell = document.createElement("td");
    titleCell.setAttribute("data-label", "Title");
    const titleButton = document.createElement("button");
    titleButton.className = "link-button";
    titleButton.type = "button";
    titleButton.textContent = suggestedTitle;
    titleButton.addEventListener("click", () => {
      navigateToDocument(doc.id);
    });
    titleCell.appendChild(titleButton);

    const typeCell = document.createElement("td");
    typeCell.setAttribute("data-label", "Type");
    typeCell.textContent = documentType;
    const correspondentCell = document.createElement("td");
    correspondentCell.setAttribute("data-label", "Correspondent");
    correspondentCell.textContent = correspondent;
    const tagsCell = document.createElement("td");
    tagsCell.setAttribute("data-label", "Tags");
    if (doc.llm_metadata && Array.isArray(doc.llm_metadata.tags) && doc.llm_metadata.tags.length) {
      const pills = document.createElement("div");
      pills.className = "tag-pills";
      for (const tag of doc.llm_metadata.tags) {
        const pill = document.createElement("span");
        pill.className = "tag-pill";
        pill.textContent = tag;
        pills.appendChild(pill);
      }
      tagsCell.appendChild(pills);
    } else {
      tagsCell.textContent = tags;
    }
    const dateCell = document.createElement("td");
    dateCell.setAttribute("data-label", "Date");
    dateCell.textContent = documentDate;
    const statusCell = document.createElement("td");
    statusCell.setAttribute("data-label", "Status");
    statusCell.textContent = formatStatus(doc.status);

    const actionCell = document.createElement("td");
    actionCell.setAttribute("data-label", "Action");
    const actionsWrap = document.createElement("div");
    actionsWrap.className = "table-actions";
    actionsWrap.appendChild(
      createIconActionButton({
        icon: "edit",
        label: "Open document",
        onClick: () => navigateToDocument(doc.id),
      })
    );
    actionsWrap.appendChild(
      createIconActionButton({
        icon: "eye",
        label: "View file",
        onClick: async () => {
          try {
            await openDocumentFile(doc.id);
          } catch (error) {
            logActivity(`Failed to open file: ${error.message}`);
          }
        },
      })
    );
    actionCell.appendChild(actionsWrap);

    row.appendChild(titleCell);
    row.appendChild(typeCell);
    row.appendChild(correspondentCell);
    row.appendChild(tagsCell);
    row.appendChild(dateCell);
    row.appendChild(statusCell);
    row.appendChild(actionCell);
    docsTableBody.appendChild(row);
  }
}

function renderTagsList(tagStats) {
  if (!tagStats.length) {
    tagsTableBody.innerHTML = '<tr><td colspan="3">No tags found.</td></tr>';
    return;
  }
  tagsTableBody.innerHTML = "";
  for (const stat of tagStats) {
    const row = document.createElement("tr");
    const tagCell = document.createElement("td");
    tagCell.setAttribute("data-label", "Tag");
    tagCell.textContent = stat.tag;
    const countCell = document.createElement("td");
    countCell.setAttribute("data-label", "Documents");
    countCell.textContent = String(stat.document_count);
    const actionCell = document.createElement("td");
    actionCell.setAttribute("data-label", "Action");

    const actionsWrap = document.createElement("div");
    actionsWrap.className = "table-actions";
    actionsWrap.appendChild(
      createIconActionButton({
        icon: "eye",
        label: `View documents for tag ${stat.tag}`,
        onClick: async () => {
          docsFilters.tag = [stat.tag];
          docsFilters.correspondent = [];
          docsFilters.document_type = [];
          docsFilters.status = [];
          docsPage = 1;
          applyFiltersToControls();
          setActiveView("section-docs");
          setActiveNav("section-docs");
          syncUrlFromFilters();
          await loadDocumentsList();
          logActivity(`Filtered documents by tag: ${stat.tag}`);
        },
      })
    );
    actionCell.appendChild(actionsWrap);
    row.appendChild(tagCell);
    row.appendChild(countCell);
    row.appendChild(actionCell);
    tagsTableBody.appendChild(row);
  }
}

function renderDocumentTypesList(typeStats) {
  if (!typeStats.length) {
    documentTypesTableBody.innerHTML = '<tr><td colspan="3">No document types found.</td></tr>';
    return;
  }
  documentTypesTableBody.innerHTML = "";
  for (const stat of typeStats) {
    const row = document.createElement("tr");
    const typeCell = document.createElement("td");
    typeCell.setAttribute("data-label", "Document Type");
    typeCell.textContent = stat.document_type;
    const countCell = document.createElement("td");
    countCell.setAttribute("data-label", "Documents");
    countCell.textContent = String(stat.document_count);
    const actionCell = document.createElement("td");
    actionCell.setAttribute("data-label", "Action");

    const actionsWrap = document.createElement("div");
    actionsWrap.className = "table-actions";
    actionsWrap.appendChild(
      createIconActionButton({
        icon: "eye",
        label: `View documents for type ${stat.document_type}`,
        onClick: async () => {
          docsFilters.tag = [];
          docsFilters.correspondent = [];
          docsFilters.document_type = [stat.document_type];
          docsFilters.status = [];
          docsPage = 1;
          applyFiltersToControls();
          setActiveView("section-docs");
          setActiveNav("section-docs");
          syncUrlFromFilters();
          await loadDocumentsList();
          logActivity(`Filtered documents by type: ${stat.document_type}`);
        },
      })
    );
    actionCell.appendChild(actionsWrap);
    row.appendChild(typeCell);
    row.appendChild(countCell);
    row.appendChild(actionCell);
    documentTypesTableBody.appendChild(row);
  }
}

function renderPendingList(documents) {
  if (!documents.length) {
    pendingTableBody.innerHTML = '<tr><td colspan="4">No pending documents.</td></tr>';
    return;
  }
  pendingTableBody.innerHTML = "";
  for (const doc of documents) {
    const row = document.createElement("tr");

    const titleCell = document.createElement("td");
    titleCell.setAttribute("data-label", "Title");
    const titleButton = document.createElement("button");
    titleButton.className = "link-button";
    titleButton.type = "button";
    titleButton.textContent = getSuggestedTitle(doc);
    titleButton.addEventListener("click", () => {
      navigateToDocument(doc.id);
    });
    titleCell.appendChild(titleButton);

    const statusCell = document.createElement("td");
    statusCell.setAttribute("data-label", "Status");
    statusCell.textContent = formatStatus(doc.status);
    const createdCell = document.createElement("td");
    createdCell.setAttribute("data-label", "Created");
    createdCell.textContent = new Date(doc.created_at).toLocaleString();
    const actionCell = document.createElement("td");
    actionCell.setAttribute("data-label", "Action");

    const button = document.createElement("button");
    button.className = "btn";
    button.type = "button";
    button.textContent = "Open";
    button.addEventListener("click", () => {
      navigateToDocument(doc.id);
    });
    actionCell.appendChild(button);

    row.appendChild(titleCell);
    row.appendChild(statusCell);
    row.appendChild(createdCell);
    row.appendChild(actionCell);
    pendingTableBody.appendChild(row);
  }
}

function renderProcessedDocsActivity(documents) {
  if (!processedDocsTableBody) {
    return;
  }
  if (!documents.length) {
    processedDocsTableBody.innerHTML = '<tr><td colspan="4">No processed documents.</td></tr>';
    return;
  }
  processedDocsTableBody.innerHTML = "";
  for (const doc of documents) {
    const row = document.createElement("tr");

    const titleCell = document.createElement("td");
    titleCell.setAttribute("data-label", "Title");
    const titleButton = document.createElement("button");
    titleButton.className = "link-button";
    titleButton.type = "button";
    titleButton.textContent = getSuggestedTitle(doc);
    titleButton.addEventListener("click", () => {
      navigateToDocument(doc.id);
    });
    titleCell.appendChild(titleButton);

    const statusCell = document.createElement("td");
    statusCell.setAttribute("data-label", "Status");
    statusCell.textContent = formatStatus(doc.status);

    const uploadedCell = document.createElement("td");
    uploadedCell.setAttribute("data-label", "Uploaded");
    uploadedCell.textContent = doc.created_at ? new Date(doc.created_at).toLocaleString() : "-";

    const actionCell = document.createElement("td");
    actionCell.setAttribute("data-label", "Action");
    const actionsWrap = document.createElement("div");
    actionsWrap.className = "table-actions";
    actionsWrap.appendChild(
      createIconActionButton({
        icon: "edit",
        label: "Open document",
        onClick: () => navigateToDocument(doc.id),
      })
    );
    actionsWrap.appendChild(
      createIconActionButton({
        icon: "eye",
        label: "View file",
        onClick: async () => {
          try {
            await openDocumentFile(doc.id);
          } catch (error) {
            logActivity(`Failed to open file: ${error.message}`);
          }
        },
      })
    );
    actionCell.appendChild(actionsWrap);

    row.appendChild(titleCell);
    row.appendChild(statusCell);
    row.appendChild(uploadedCell);
    row.appendChild(actionCell);
    processedDocsTableBody.appendChild(row);
  }
}

function setRestartPendingButtonEnabled(enabled) {
  if (!restartPendingBtn) {
    return;
  }
  restartPendingBtn.disabled = !enabled;
}

async function loadDocumentsList() {
  const query = new URLSearchParams({
    limit: String(docsPageSize),
    offset: String((docsPage - 1) * docsPageSize),
  });
  if (docsFilters.q) {
    query.set("q", docsFilters.q);
  }
  for (const value of docsFilters.tag) {
    query.append("tag", value);
  }
  for (const value of docsFilters.correspondent) {
    query.append("correspondent", value);
  }
  for (const value of docsFilters.document_type) {
    query.append("document_type", value);
  }
  for (const value of docsFilters.status) {
    query.append("status", value);
  }

  const [listResponse, countResponse] = await Promise.all([
    apiFetch(`/documents?${query.toString()}`),
    apiFetch(`/documents/count?${query.toString()}`),
  ]);
  const payload = await listResponse.json();
  const countPayload = await countResponse.json();
  if (!listResponse.ok) {
    logActivity(`Document list failed: ${payload.detail || listResponse.statusText}`);
    return;
  }
  if (!countResponse.ok) {
    logActivity(`Document count failed: ${countPayload.detail || countResponse.statusText}`);
    return;
  }
  docsTotalCount = Number(countPayload.total || 0);
  renderDocsList(payload);
  refreshFilterOptionsFromDocuments(payload);
  renderPaginationControls(payload.length);
  logActivity(`Loaded ${payload.length} document(s) of ${docsTotalCount} total`);
}

function renderPaginationControls(currentCount) {
  const totalPages = Math.max(1, Math.ceil(docsTotalCount / docsPageSize));
  if (docsPage > totalPages) {
    docsPage = totalPages;
  }
  if (docsTotalLabel) {
    docsTotalLabel.textContent = `Total documents: ${docsTotalCount.toLocaleString()}`;
  }
  if (pageIndicator) {
    pageIndicator.textContent = `Page ${docsPage} / ${totalPages}`;
  }
  if (pagePrevBtn) {
    pagePrevBtn.disabled = docsPage <= 1;
  }
  if (pageNextBtn) {
    pageNextBtn.disabled = docsPage >= totalPages || currentCount < docsPageSize;
  }
}

async function loadPendingDocuments() {
  const response = await apiFetch("/documents/pending?limit=200");
  const payload = await response.json();
  if (!response.ok) {
    setRestartPendingButtonEnabled(false);
    logActivity(`Pending list failed: ${payload.detail || response.statusText}`);
    return;
  }
  renderPendingList(payload);
  setRestartPendingButtonEnabled(payload.length > 0);
  logActivity(`Loaded ${payload.length} pending document(s)`);
}

function renderActivityTokenTotal(totalTokens) {
  if (!activityTokenTotal) {
    return;
  }
  const value = Number.isFinite(totalTokens) && totalTokens > 0 ? Math.floor(totalTokens) : 0;
  activityTokenTotal.textContent = `LLM tokens processed: ${value.toLocaleString()}`;
}

async function loadProcessedDocumentsActivity() {
  const allDocuments = [];
  const batchSize = 200;
  const maxDocuments = 5_000;
  let offset = 0;
  while (offset < maxDocuments) {
    const response = await apiFetch(
      `/documents?status=ready&limit=${batchSize}&offset=${offset}`
    );
    const payload = await response.json();
    if (!response.ok) {
      logActivity(`Processed documents load failed: ${payload.detail || response.statusText}`);
      return;
    }
    allDocuments.push(...payload);
    if (payload.length < batchSize) {
      break;
    }
    offset += batchSize;
  }
  renderProcessedDocsActivity(allDocuments);
  const preferences = await loadUserPreferences();
  const totalTokens = Number(preferences.llm_total_tokens_processed || 0);
  renderActivityTokenTotal(totalTokens);
  logActivity(`Loaded ${allDocuments.length} processed document(s).`);
}

async function loadTagStats() {
  const response = await apiFetch("/documents/metadata/tag-stats");
  const payload = await response.json();
  if (!response.ok) {
    logActivity(`Tag stats load failed: ${payload.detail || response.statusText}`);
    return;
  }
  renderTagsList(payload);
  logActivity(`Loaded ${payload.length} tag(s)`);
}

async function loadDocumentTypeStats() {
  const response = await apiFetch("/documents/metadata/document-type-stats");
  const payload = await response.json();
  if (!response.ok) {
    logActivity(`Document type stats load failed: ${payload.detail || response.statusText}`);
    return;
  }
  renderDocumentTypesList(payload);
  logActivity(`Loaded ${payload.length} document type(s)`);
}

async function openDocumentView(documentId) {
  const response = await apiFetch(`/documents/${documentId}/detail`);
  const payload = await response.json();
  if (!response.ok) {
    throw new Error(payload.detail || "Failed to load document detail");
  }

  const doc = payload.document;
  const metadata = payload.llm_metadata;
  currentDocumentId = doc.id;

  metaTitleInput.value = metadata?.suggested_title || doc.filename;
  metaDateInput.value = metadata?.document_date || "";
  metaCorrespondentInput.value = metadata?.correspondent || "";
  metaTypeInput.value = metadata?.document_type || "";
  metaTagsInput.value = metadata?.tags?.join(", ") || "";
  detailDocId.textContent = doc.id || "-";
  detailOwnerId.textContent = doc.owner_id || "-";
  detailFilename.textContent = doc.filename || "-";
  detailStatus.textContent = formatStatus(doc.status);
  detailCreatedAt.textContent = doc.created_at
    ? new Date(doc.created_at).toLocaleString()
    : "-";
  detailContentType.textContent = doc.content_type || "-";
  detailSizeBytes.textContent = `${formatBytes(doc.size_bytes)} (${doc.size_bytes || 0} bytes)`;
  detailChecksum.textContent = doc.checksum_sha256 || "-";
  detailBlobUri.textContent = toRelativeBlobPath(doc.blob_uri);
  detailBlobUri.title = doc.blob_uri || "";

  const historyResponse = await apiFetch(`/documents/${documentId}/history?limit=100`);
  const historyPayload = await historyResponse.json();
  if (!historyResponse.ok) {
    renderDocumentHistory([]);
    logActivity(`History load failed: ${historyPayload.detail || historyResponse.statusText}`);
  } else {
    renderDocumentHistory(historyPayload);
  }

  setActiveView("section-document");
  setActiveNav("section-document");
  syncUrlFromFilters();
  logActivity(`Opened document ${documentId}`);
}

async function waitForDocumentReady(documentId, timeoutMs = 45000, intervalMs = 1500) {
  const deadline = Date.now() + timeoutMs;
  while (Date.now() < deadline) {
    const response = await apiFetch(`/documents/${documentId}`);
    const payload = await response.json();
    if (!response.ok) {
      throw new Error(payload.detail || "Failed to refresh document status");
    }
    if (payload.status === "ready") {
      return true;
    }
    await delay(intervalMs);
  }
  return false;
}

signInForm?.addEventListener("submit", async (event) => {
  event.preventDefault();
  const email = document.getElementById("signInEmail").value.trim();
  const password = document.getElementById("signInPassword").value;
  const response = await apiFetch("/users/login", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password }),
  });
  const payload = await response.json();
  if (!response.ok) {
    setAuthMessage(payload.detail || response.statusText, true);
    return;
  }
  persistSession(payload.access_token, payload.user);
  renderSessionState();
  setAuthMessage(`Signed in as ${payload.user.email}.`);
  await hydrateUserPreferencesForSession();
  applyFiltersToControls();
  setActiveView(currentViewId);
  setActiveNav(currentViewId);
  await loadDocumentsList();
  await loadTagStats();
  await loadDocumentTypeStats();
  await loadPendingDocuments();
});

registerForm?.addEventListener("submit", async (event) => {
  event.preventDefault();
  const fullName = document.getElementById("registerName").value.trim();
  const email = document.getElementById("registerEmail").value.trim();
  const password = document.getElementById("registerPassword").value;
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
    body: JSON.stringify({ email, password }),
  });
  const loginPayload = await loginResponse.json();
  if (!loginResponse.ok) {
    setAuthMessage(loginPayload.detail || loginResponse.statusText, true);
    return;
  }
  persistSession(loginPayload.access_token, loginPayload.user);
  renderSessionState();
  setAuthMessage(`Registered ${registerPayload.email}.`);
  await hydrateUserPreferencesForSession();
  applyFiltersToControls();
  setActiveView(currentViewId);
  setActiveNav(currentViewId);
  await loadDocumentsList();
  await loadTagStats();
  await loadDocumentTypeStats();
  await loadPendingDocuments();
});

signOutBtn?.addEventListener("click", () => {
  clearSession();
  setAuthMessage("Signed out.");
});

settingsForm?.addEventListener("submit", async (event) => {
  event.preventDefault();
  const nextTheme = normalizeThemeName(settingsThemeSelect?.value || currentTheme);
  const nextPageSize = normalizePageSize(settingsPageSizeSelect?.value || docsPageSize);
  llmSettings = readLlmSettingsFromControls();
  ocrProvider = normalizeOcrProvider(settingsOcrProviderSelect?.value || ocrProvider);
  syncUploadAvailability();
  applyTheme(nextTheme);
  docsPageSize = nextPageSize;
  docsPage = 1;
  syncUrlFromFilters();
  await saveUserPreferences();
  if (currentViewId === "section-docs") {
    await loadDocumentsList();
  }
  logActivity("Saved settings.");
});

settingsLlmProviderSelect?.addEventListener("change", () => {
  const nextProvider = normalizeLlmProvider(settingsLlmProviderSelect.value);
  applyLlmProviderDefaultsToControls(nextProvider, { force: true });
  setSettingsLlmTestStatus("");
});

settingsTestLlmBtn?.addEventListener("click", async () => {
  const candidateSettings = readLlmSettingsFromControls();
  const reason = getLlmUploadBlockReasonForSettings(candidateSettings);
  if (reason) {
    setSettingsLlmTestStatus(reason, "error");
    logActivity(`LLM API test blocked: ${reason}`);
    return;
  }

  const previousText = settingsTestLlmBtn.textContent;
  settingsTestLlmBtn.disabled = true;
  settingsTestLlmBtn.textContent = "Testing...";
  setSettingsLlmTestStatus("Testing...", "");
  logActivity("Testing LLM API connection...");
  try {
    const response = await apiFetch("/documents/llm/test", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        provider: candidateSettings.provider,
        model: candidateSettings.model,
        base_url: candidateSettings.base_url,
        api_key: candidateSettings.api_key,
      }),
    });
    const payload = await response.json();
    if (!response.ok) {
      setSettingsLlmTestStatus(payload.detail || response.statusText, "error");
      logActivity(`LLM API test failed: ${payload.detail || response.statusText}`);
      return;
    }
    setSettingsLlmTestStatus(`Success (${payload.provider} / ${payload.model})`, "success");
    logActivity(`LLM API test passed (${payload.provider} / ${payload.model}).`);
  } catch (error) {
    setSettingsLlmTestStatus(error.message, "error");
    logActivity(`LLM API test failed: ${error.message}`);
  } finally {
    settingsTestLlmBtn.disabled = false;
    settingsTestLlmBtn.textContent = previousText || "Test LLM API";
  }
});

uploadForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  if (!syncUploadAvailability({ announce: true, navigateToSettings: true })) {
    return;
  }

  const files = collectSupportedFiles(fileInput?.files || []);
  if (!files.length) {
    logActivity("Upload blocked: select at least one supported document file.");
    return;
  }

  const uploadedIds = [];
  for (const file of files) {
    logActivity(`Uploading ${file.name}...`);
    try {
      const payload = await uploadDocumentFile(file);
      uploadedIds.push(payload.id);
      logActivity(`Uploaded ${file.name} => document ${payload.id}`);
    } catch (error) {
      logActivity(`Upload failed for ${file.name}: ${error.message}`);
    }
  }

  updateSelectedFilesLabel();
  if (!uploadedIds.length) {
    return;
  }
  if (uploadedIds.length === 1) {
    navigateToDocument(uploadedIds[0]);
    return;
  }
  logActivity(`Uploaded ${uploadedIds.length} files.`);
  setActiveView("section-docs");
  setActiveNav("section-docs");
  syncUrlFromFilters();
  await loadDocumentsList();
  await loadPendingDocuments();
});

fileInput?.addEventListener("change", () => {
  updateSelectedFilesLabel();
});

uploadDropzone?.addEventListener("click", (event) => {
  if (!syncUploadAvailability({ announce: true, navigateToSettings: true })) {
    return;
  }
  if (event.target === fileInput) {
    return;
  }
  fileInput?.click();
});

uploadDropzone?.addEventListener("keydown", (event) => {
  if (!syncUploadAvailability({ announce: true, navigateToSettings: true })) {
    return;
  }
  if (event.key !== "Enter" && event.key !== " ") {
    return;
  }
  event.preventDefault();
  fileInput?.click();
});

["dragenter", "dragover"].forEach((eventName) => {
  uploadDropzone?.addEventListener(eventName, (event) => {
    if (!syncUploadAvailability()) {
      return;
    }
    event.preventDefault();
    uploadDropzone.classList.add("is-drag-over");
  });
});

["dragleave", "drop"].forEach((eventName) => {
  uploadDropzone?.addEventListener(eventName, (event) => {
    event.preventDefault();
    uploadDropzone.classList.remove("is-drag-over");
  });
});

uploadDropzone?.addEventListener("drop", (event) => {
  if (!syncUploadAvailability({ announce: true, navigateToSettings: true })) {
    return;
  }
  const dropped = collectSupportedFiles(event.dataTransfer?.files || []);
  if (!dropped.length) {
    logActivity("Drop ignored: only supported document types are accepted.");
    return;
  }
  setSelectedFiles(dropped);
  logActivity(`Ready to upload ${dropped.length} file(s).`);
});

documentMetaForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  if (!currentDocumentId) {
    logActivity("No document selected.");
    return;
  }

  const response = await apiFetch(`/documents/${currentDocumentId}/metadata`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      suggested_title: metaTitleInput.value.trim(),
      document_date: metaDateInput.value || null,
      correspondent: metaCorrespondentInput.value.trim(),
      document_type: metaTypeInput.value.trim(),
      tags: splitTags(metaTagsInput.value),
    }),
  });
  const payload = await response.json();
  if (!response.ok) {
    logActivity(`Metadata save failed: ${payload.detail || response.statusText}`);
    return;
  }

  logActivity(`Saved metadata for ${currentDocumentId}`);
  await openDocumentView(currentDocumentId);
  await loadDocumentsList();
  await loadPendingDocuments();
  await loadTagStats();
  await loadDocumentTypeStats();
});

reprocessDocumentBtn?.addEventListener("click", async () => {
  if (!currentDocumentId) {
    logActivity("No document selected.");
    return;
  }

  const response = await apiFetch(`/documents/${currentDocumentId}/reprocess`, {
    method: "POST",
  });
  const payload = await response.json();
  if (!response.ok) {
    logActivity(`Reprocess failed: ${payload.detail || response.statusText}`);
    return;
  }

  logActivity(
    `Reprocessing queued for ${currentDocumentId} (job ${payload.job_id}).`
  );
  await openDocumentView(currentDocumentId);
  await loadDocumentsList();
  await loadPendingDocuments();
  const completed = await waitForDocumentReady(currentDocumentId);
  if (completed) {
    logActivity(`Reprocessing completed for ${currentDocumentId}.`);
    await openDocumentView(currentDocumentId);
    await loadDocumentsList();
    await loadPendingDocuments();
    await loadTagStats();
    await loadDocumentTypeStats();
  } else {
    logActivity(`Reprocessing still running for ${currentDocumentId}. Refresh to check later.`);
  }
});

viewDocumentFileBtn?.addEventListener("click", async () => {
  if (!currentDocumentId) {
    logActivity("No document selected.");
    return;
  }
  try {
    await openDocumentFile(currentDocumentId);
  } catch (error) {
    logActivity(`Failed to open file: ${error.message}`);
  }
});

backToDocsBtn.addEventListener("click", () => {
  const url = new URL("/ui/documents", window.location.origin);
  window.location.href = `${url.pathname}?${url.searchParams.toString()}`;
});

docsFilterForm.addEventListener("submit", (event) => {
  event.preventDefault();
});

for (const selectEl of filterSelects) {
  selectEl.addEventListener("change", async () => {
    await applyFiltersFromControls();
  });
}

for (const selectEl of filterSelects) {
  setupFilterDropdown(selectEl);
}

document.addEventListener("click", (event) => {
  if (!activeFilterDropdown) {
    return;
  }
  const state = filterDropdownState.get(activeFilterDropdown);
  if (!state) {
    return;
  }
  if (!state.chip.contains(event.target)) {
    closeFilterDropdown(activeFilterDropdown);
  }
});

document.addEventListener("keydown", (event) => {
  if (event.key === "Escape" && activeFilterDropdown) {
    closeFilterDropdown(activeFilterDropdown);
  }
});

clearFiltersBtn.addEventListener("click", async () => {
  docsFilters.q = "";
  docsFilters.tag = [];
  docsFilters.correspondent = [];
  docsFilters.document_type = [];
  docsFilters.status = ["ready"];
  docsPage = 1;
  applyFiltersToControls();
  syncUrlFromFilters();
  await loadDocumentsList();
});

filterQuery?.addEventListener("input", async () => {
  await applyFiltersFromControls();
});

pagePrevBtn?.addEventListener("click", async () => {
  if (docsPage <= 1) {
    return;
  }
  docsPage -= 1;
  syncUrlFromFilters();
  await loadDocumentsList();
});

pageNextBtn?.addEventListener("click", async () => {
  docsPage += 1;
  syncUrlFromFilters();
  await loadDocumentsList();
});

restartPendingBtn?.addEventListener("click", async () => {
  if (restartPendingBtn.disabled) {
    return;
  }
  const confirmed = window.confirm(
    "Restart analysis for all documents that are not ready?"
  );
  if (!confirmed) {
    return;
  }

  const response = await apiFetch("/documents/pending/restart?limit=200", {
    method: "POST",
  });
  const payload = await response.json();
  if (!response.ok) {
    logActivity(`Restart failed: ${payload.detail || response.statusText}`);
    return;
  }

  logActivity(
    `Restarted ${payload.restarted_count} pending document(s). ` +
      `${payload.skipped_ready_count} ready document(s) skipped.`
  );
  await loadPendingDocuments();
  await loadDocumentsList();
});

window.addEventListener("popstate", async () => {
  if (!authToken || !currentUser) {
    return;
  }
  readFiltersFromUrl();
  applyFiltersToControls();
  renderSettingsForm();
  setActiveView(currentViewId);
  setActiveNav(currentViewId);
  if (currentViewId === "section-tags") {
    await loadTagStats();
    return;
  }
  if (currentViewId === "section-document-types") {
    await loadDocumentTypeStats();
    return;
  }
  if (currentViewId === "section-activity") {
    await loadProcessedDocumentsActivity();
    return;
  }
  if (currentViewId === "section-pending") {
    await loadPendingDocuments();
    return;
  }
  if (currentViewId === "section-document" && currentDocumentId) {
    await openDocumentView(currentDocumentId);
    return;
  }
  if (currentViewId === "section-settings") {
    renderSettingsForm();
    return;
  }
  await loadDocumentsList();
});

async function initializeApp() {
  await restoreSession();
  if (!authToken || !currentUser) {
    return;
  }

  await hydrateUserPreferencesForSession();
  applyFiltersToControls();
  renderSettingsForm();
  syncUploadAvailability();
  setActiveView(currentViewId);
  setActiveNav(currentViewId);

  if (currentViewId === "section-docs") {
    loadDocumentsList().catch((error) => {
      logActivity(`Initial document list failed: ${error.message}`);
    });
  }

  if (currentViewId === "section-tags") {
    loadTagStats().catch((error) => {
      logActivity(`Initial tag stats failed: ${error.message}`);
    });
  }

  if (currentViewId === "section-document-types") {
    loadDocumentTypeStats().catch((error) => {
      logActivity(`Initial document type stats failed: ${error.message}`);
    });
  }

  if (currentViewId === "section-pending") {
    loadPendingDocuments().catch((error) => {
      logActivity(`Initial pending list failed: ${error.message}`);
    });
  }

  if (currentViewId === "section-activity") {
    loadProcessedDocumentsActivity().catch((error) => {
      logActivity(`Initial processed activity failed: ${error.message}`);
    });
  }

  if (currentViewId === "section-document") {
    const docId = new URLSearchParams(window.location.search).get("id");
    if (docId) {
      openDocumentView(docId).catch((error) => {
        logActivity(`Initial document detail failed: ${error.message}`);
      });
    }
  }

  if (currentViewId === "section-settings") {
    renderSettingsForm();
  }
}

applyTheme(currentTheme);

initializeApp().catch((error) => {
  setAuthMessage(error.message || "Failed to initialize app.", true);
});
