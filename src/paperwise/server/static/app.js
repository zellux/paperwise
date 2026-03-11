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
const searchCollectionCreateForm = document.getElementById("searchCollectionCreateForm");
const searchCollectionNameInput = document.getElementById("searchCollectionName");
const searchCollectionDescriptionInput = document.getElementById("searchCollectionDescription");
const searchRefreshCollectionsBtn = document.getElementById("searchRefreshCollectionsBtn");
const searchScopeSelect = document.getElementById("searchScopeSelect");
const searchUseAllScopeBtn = document.getElementById("searchUseAllScopeBtn");
const searchScopeTagsInput = document.getElementById("searchScopeTagsInput");
const searchScopeTypesInput = document.getElementById("searchScopeTypesInput");
const collectionsTableBody = document.getElementById("collectionsTableBody");
const searchCollectionDocsLabel = document.getElementById("searchCollectionDocsLabel");
const searchCollectionDocsCount = document.getElementById("searchCollectionDocsCount");
const searchCollectionDocFilter = document.getElementById("searchCollectionDocFilter");
const searchCollectionDocPicker = document.getElementById("searchCollectionDocPicker");
const searchCollectionDocsTableBody = document.getElementById("searchCollectionDocsTableBody");
const searchAddDocsBtn = document.getElementById("searchAddDocsBtn");
const searchKeywordForm = document.getElementById("searchKeywordForm");
const searchKeywordInput = document.getElementById("searchKeywordInput");
const searchKeywordLimitSelect = document.getElementById("searchKeywordLimitSelect");
const searchResultsMeta = document.getElementById("searchResultsMeta");
const searchResultsTableBody = document.getElementById("searchResultsTableBody");
const searchAskForm = document.getElementById("searchAskForm");
const searchAskQuestion = document.getElementById("searchAskQuestion");
const searchAskTopKInput = document.getElementById("searchAskTopKInput");
const searchAskDebugToggle = document.getElementById("searchAskDebugToggle");
const searchAskAnswer = document.getElementById("searchAskAnswer");
const searchAskDebugOutput = document.getElementById("searchAskDebugOutput");
const searchAskCitationsBody = document.getElementById("searchAskCitationsBody");
const searchSubsections = [...document.querySelectorAll(".search-subsection")];
const settingsThemeSelect = document.getElementById("settingsThemeSelect");
const settingsPageSizeSelect = document.getElementById("settingsPageSizeSelect");
const settingsLlmProviderSelect = document.getElementById("settingsLlmProviderSelect");
const settingsLlmModelInput = document.getElementById("settingsLlmModelInput");
const settingsLlmBaseUrlInput = document.getElementById("settingsLlmBaseUrlInput");
const settingsLlmApiKeyInput = document.getElementById("settingsLlmApiKeyInput");
const settingsTestLlmBtn = document.getElementById("settingsTestLlmBtn");
const settingsLlmTestStatus = document.getElementById("settingsLlmTestStatus");
const settingsOcrProviderSelect = document.getElementById("settingsOcrProviderSelect");
const settingsOcrStatus = document.getElementById("settingsOcrStatus");
const settingsOcrAutoSwitchCheckbox = document.getElementById("settingsOcrAutoSwitchCheckbox");
const settingsOcrImageDetailSelect = document.getElementById("settingsOcrImageDetailSelect");
const settingsCurrentPasswordInput = document.getElementById("settingsCurrentPasswordInput");
const settingsNewPasswordInput = document.getElementById("settingsNewPasswordInput");
const settingsConfirmPasswordInput = document.getElementById("settingsConfirmPasswordInput");
const settingsChangePasswordBtn = document.getElementById("settingsChangePasswordBtn");
const settingsPasswordStatus = document.getElementById("settingsPasswordStatus");
const settingsOcrLlmProviderSelect = document.getElementById("settingsOcrLlmProviderSelect");
const settingsOcrLlmModelInput = document.getElementById("settingsOcrLlmModelInput");
const settingsOcrLlmBaseUrlInput = document.getElementById("settingsOcrLlmBaseUrlInput");
const settingsOcrLlmApiKeyInput = document.getElementById("settingsOcrLlmApiKeyInput");
const settingsOcrSeparateOnlyFields = [
  ...document.querySelectorAll(".ocr-separate-only"),
];
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
const detailOcrContent = document.getElementById("detailOcrContent");
const detailCreatedAt = document.getElementById("detailCreatedAt");
const detailOcrParsedAt = document.getElementById("detailOcrParsedAt");
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
  "section-search": "search",
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
  "/ui/collections": "section-search",
  "/ui/search": "section-search",
  "/ui/grounded-qa": "section-search",
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
  "section-search": "/ui/collections",
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
const THEME_STORAGE_KEY = "paperwise.ui.theme";
let currentTheme = "atlas";
const SUPPORTED_LLM_PROVIDERS = ["openai", "gemini", "custom"];
const LLM_PROVIDER_DEFAULTS = {
  openai: {
    model: "gpt-4.1-mini",
    base_url: "https://api.openai.com/v1",
  },
  gemini: {
    model: "gemini-2.0-flash",
    base_url: "https://generativelanguage.googleapis.com/v1beta",
  },
};
const OCR_LLM_PROVIDER_DEFAULTS = {
  openai: {
    model: "gpt-4.1-nano",
    base_url: "https://api.openai.com/v1",
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
const SUPPORTED_OCR_PROVIDERS = ["tesseract", "llm", "llm_separate"];
let ocrProvider = "llm";
let ocrImageDetail = "auto";
let ocrLlmSettings = {
  provider: "",
  model: "",
  base_url: "",
  api_key: "",
};
let ocrAutoSwitch = false;
let ocrStatusRequestSeq = 0;
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
let docsListRequestSeq = 0;
let pendingDocsRequestSeq = 0;
let processedActivityRequestSeq = 0;
let tagStatsRequestSeq = 0;
let documentTypeStatsRequestSeq = 0;
let searchCollectionsRequestSeq = 0;
let searchDocsCatalogRequestSeq = 0;
let searchCollectionDocsRequestSeq = 0;
let searchCollections = [];
let searchDocsCatalog = [];
let searchSelectedCollectionId = "";
let searchSelectedCollectionDocumentIds = [];
let searchActiveSectionId = "search-section-collections";
const PATH_TO_SEARCH_SECTION_ID = {
  "/ui/collections": "search-section-collections",
  "/ui/search": "search-section-keyword",
  "/ui/grounded-qa": "search-section-ask",
};

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

function readBootTheme() {
  const bootTheme = normalizeThemeName(document.documentElement?.dataset?.uiTheme || "");
  if (bootTheme !== "atlas") {
    return bootTheme;
  }
  try {
    return normalizeThemeName(window.localStorage.getItem(THEME_STORAGE_KEY));
  } catch {
    return "atlas";
  }
}

currentTheme = readBootTheme();

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

function getOcrLlmProviderDefaults(provider) {
  const normalized = normalizeLlmProvider(provider);
  if (!normalized) {
    return null;
  }
  return OCR_LLM_PROVIDER_DEFAULTS[normalized] || null;
}

function normalizeOcrProvider(value) {
  const normalized = String(value || "").trim().toLowerCase();
  if (SUPPORTED_OCR_PROVIDERS.includes(normalized)) {
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
  const classNames = SUPPORTED_THEMES.map((name) => `theme-${name}`);
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
  if (
    settingsOcrLlmProviderSelect &&
    settingsOcrLlmProviderSelect.value !== ocrLlmSettings.provider
  ) {
    settingsOcrLlmProviderSelect.value = ocrLlmSettings.provider;
  }
  if (settingsOcrLlmModelInput && settingsOcrLlmModelInput.value !== ocrLlmSettings.model) {
    settingsOcrLlmModelInput.value = ocrLlmSettings.model;
  }
  if (settingsOcrLlmBaseUrlInput && settingsOcrLlmBaseUrlInput.value !== ocrLlmSettings.base_url) {
    settingsOcrLlmBaseUrlInput.value = ocrLlmSettings.base_url;
  }
  if (settingsOcrLlmApiKeyInput && settingsOcrLlmApiKeyInput.value !== ocrLlmSettings.api_key) {
    settingsOcrLlmApiKeyInput.value = ocrLlmSettings.api_key;
  }
  if (settingsOcrAutoSwitchCheckbox) {
    settingsOcrAutoSwitchCheckbox.checked = ocrAutoSwitch;
  }
  if (settingsOcrImageDetailSelect && settingsOcrImageDetailSelect.value !== ocrImageDetail) {
    settingsOcrImageDetailSelect.value = ocrImageDetail;
  }
  syncOcrSeparateSettingsVisibility();
  refreshLocalOcrStatus().catch(() => {});
  setSettingsPasswordStatus("");
  syncUploadAvailability();
}

function syncOcrSeparateSettingsVisibility() {
  const selectedProvider = normalizeOcrProvider(settingsOcrProviderSelect?.value || ocrProvider);
  const showOcrLlmFields = selectedProvider === "llm_separate";
  settingsOcrSeparateOnlyFields.forEach((element) => {
    element.hidden = !showOcrLlmFields;
  });
}

function readLlmSettingsFromControls() {
  return {
    provider: normalizeLlmProvider(settingsLlmProviderSelect?.value || llmSettings.provider),
    model: String(settingsLlmModelInput?.value || "").trim(),
    base_url: String(settingsLlmBaseUrlInput?.value || "").trim(),
    api_key: String(settingsLlmApiKeyInput?.value || "").trim(),
  };
}

function readOcrLlmSettingsFromControls() {
  return {
    provider: normalizeLlmProvider(settingsOcrLlmProviderSelect?.value || ocrLlmSettings.provider),
    model: String(settingsOcrLlmModelInput?.value || "").trim(),
    base_url: String(settingsOcrLlmBaseUrlInput?.value || "").trim(),
    api_key: String(settingsOcrLlmApiKeyInput?.value || "").trim(),
  };
}

function applyLlmProviderDefaultsToControls(provider, modelInput, baseUrlInput, options = {}) {
  const force = options.force === true;
  const defaults = getLlmProviderDefaults(provider);
  if (!defaults) {
    return;
  }
  if (modelInput) {
    const currentModel = String(modelInput.value || "").trim();
    if (force || !currentModel) {
      modelInput.value = defaults.model;
    }
  }
  if (baseUrlInput) {
    const currentBaseUrl = String(baseUrlInput.value || "").trim();
    if (force || !currentBaseUrl) {
      baseUrlInput.value = defaults.base_url;
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

function setSettingsOcrStatus(message, tone = "") {
  if (!settingsOcrStatus) {
    return;
  }
  settingsOcrStatus.textContent = message || "";
  settingsOcrStatus.classList.remove("is-success", "is-error");
  if (tone === "success") {
    settingsOcrStatus.classList.add("is-success");
  } else if (tone === "error") {
    settingsOcrStatus.classList.add("is-error");
  }
}

function setSettingsPasswordStatus(message, tone = "") {
  if (!settingsPasswordStatus) {
    return;
  }
  settingsPasswordStatus.textContent = message || "";
  settingsPasswordStatus.classList.remove("is-success", "is-error");
  if (tone === "success") {
    settingsPasswordStatus.classList.add("is-success");
  } else if (tone === "error") {
    settingsPasswordStatus.classList.add("is-error");
  }
}

async function refreshLocalOcrStatus() {
  const selectedProvider = normalizeOcrProvider(settingsOcrProviderSelect?.value || ocrProvider);
  if (selectedProvider !== "tesseract") {
    setSettingsOcrStatus("");
    return;
  }

  const requestId = ++ocrStatusRequestSeq;
  setSettingsOcrStatus("Checking local OCR tools...");
  try {
    const response = await apiFetch("/documents/ocr/local-status");
    const payload = await response.json();
    if (requestId !== ocrStatusRequestSeq) {
      return;
    }
    if (!response.ok) {
      setSettingsOcrStatus(payload.detail || response.statusText, "error");
      return;
    }
    setSettingsOcrStatus(
      payload.detail || "Local OCR tools status unknown.",
      payload.available ? "success" : "error"
    );
  } catch (error) {
    if (requestId !== ocrStatusRequestSeq) {
      return;
    }
    setSettingsOcrStatus(error.message || "Failed to check local OCR tools.", "error");
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
      ocr_auto_switch: ocrAutoSwitch,
      ocr_image_detail: ocrImageDetail,
      ocr_llm_provider: ocrLlmSettings.provider,
      ocr_llm_model: ocrLlmSettings.model,
      ocr_llm_base_url: ocrLlmSettings.base_url,
      ocr_llm_api_key: ocrLlmSettings.api_key,
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
  ocrAutoSwitch = normalizeOcrAutoSwitch(preferences.ocr_auto_switch);
  ocrImageDetail = normalizeOcrImageDetail(preferences.ocr_image_detail);
  ocrLlmSettings = {
    provider: normalizeLlmProvider(preferences.ocr_llm_provider),
    model: String(preferences.ocr_llm_model || "").trim(),
    base_url: String(preferences.ocr_llm_base_url || "").trim(),
    api_key: String(preferences.ocr_llm_api_key || "").trim(),
  };
  const ocrDefaults = getOcrLlmProviderDefaults(ocrLlmSettings.provider);
  if (ocrDefaults) {
    if (!ocrLlmSettings.model) {
      ocrLlmSettings.model = ocrDefaults.model;
    }
    if (!ocrLlmSettings.base_url) {
      ocrLlmSettings.base_url = ocrDefaults.base_url;
    }
  }
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
  ocrProvider = "llm";
  ocrAutoSwitch = false;
  ocrImageDetail = "auto";
  ocrLlmSettings = {
    provider: "",
    model: "",
    base_url: "",
    api_key: "",
  };
  docsPage = 1;
  docsPageSize = 20;
  docsFilters = sanitizeDocsFilters({
    tag: [],
    correspondent: [],
    document_type: [],
    status: ["ready"],
  });
  searchCollections = [];
  searchDocsCatalog = [];
  searchSelectedCollectionId = "";
  searchSelectedCollectionDocumentIds = [];
  searchActiveSectionId = "search-section-collections";
  currentViewId = "section-docs";
  setActiveSearchSection(searchActiveSectionId);
  renderSearchScopeOptions();
  renderCollectionsTable();
  renderSearchCollectionDocumentsTable();
  renderSearchResultsTable({ hits: [] });
  renderSearchResultsMeta("No search run yet.");
  renderSearchAskAnswer(null);
  renderSearchAskDebugOutput(null, false);
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
  const allowUnauthorized = options.allowUnauthorized === true;
  const { allowUnauthorized: _allowUnauthorized, ...fetchOptions } = options;
  const response = await window.fetch(url, { ...fetchOptions, headers });
  if (response.status === 401 && !allowUnauthorized) {
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
  const currentPath = window.location.pathname.replace(/\/+$/, "") || "/";
  for (const link of navLinks) {
    const linkTarget = link.dataset.target;
    if (targetId === "section-search" && linkTarget === "section-search") {
      const linkPath = (link.getAttribute("href") || "").replace(/\/+$/, "") || "/";
      link.classList.toggle("active", linkPath === currentPath);
      continue;
    }
    link.classList.toggle("active", linkTarget === targetId);
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

function setActiveSearchSection(sectionId) {
  const defaultSectionId = "search-section-collections";
  const nextSectionId = searchSubsections.some((section) => section.id === sectionId)
    ? sectionId
    : defaultSectionId;
  searchActiveSectionId = nextSectionId;
  for (const section of searchSubsections) {
    section.classList.toggle("view-hidden", section.id !== nextSectionId);
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
  const path = window.location.pathname.replace(/\/+$/, "") || "/";
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
  const pathSearchSectionId = PATH_TO_SEARCH_SECTION_ID[path];
  if (pathViewId && views.some((view) => view.id === pathViewId)) {
    currentViewId = pathViewId;
  } else if (mappedViewId && views.some((view) => view.id === mappedViewId)) {
    // Backward compatibility for old links that use ?view=...
    currentViewId = mappedViewId;
  } else {
    currentViewId = "section-docs";
  }
  if (pathSearchSectionId) {
    searchActiveSectionId = pathSearchSectionId;
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
  if (name === "trash") {
    addPath("M3 6h18");
    addPath("M8 6V4h8v2");
    addPath("M19 6l-1 14H6L5 6");
    addLine("10", "11", "10", "17");
    addLine("14", "11", "14", "17");
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
    row.dataset.pendingDocId = doc.id || "";

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

function getCollectionById(collectionId) {
  if (!collectionId) {
    return null;
  }
  return searchCollections.find((item) => item.id === collectionId) || null;
}

function getSearchScopeLabel() {
  const selected = getCollectionById(searchSelectedCollectionId);
  if (!selected) {
    return "All Documents";
  }
  return selected.name;
}

function parseScopeList(value) {
  const seen = new Set();
  const output = [];
  for (const part of String(value || "").split(",")) {
    const cleaned = part.trim();
    if (!cleaned) {
      continue;
    }
    const key = cleaned.toLowerCase();
    if (seen.has(key)) {
      continue;
    }
    seen.add(key);
    output.push(cleaned);
  }
  return output;
}

function readSearchScopeFilters() {
  return {
    tag: parseScopeList(searchScopeTagsInput?.value || ""),
    document_type: parseScopeList(searchScopeTypesInput?.value || ""),
  };
}

function formatSearchScopeSummary() {
  const filters = readSearchScopeFilters();
  const parts = [`Scope: ${getSearchScopeLabel()}`];
  if (filters.tag.length) {
    parts.push(`Tags: ${filters.tag.join(", ")}`);
  }
  if (filters.document_type.length) {
    parts.push(`Types: ${filters.document_type.join(", ")}`);
  }
  return parts.join(" | ");
}

function getSearchCatalogTitle(doc) {
  if (doc.llm_metadata && doc.llm_metadata.suggested_title) {
    return doc.llm_metadata.suggested_title;
  }
  return doc.filename || doc.id;
}

function renderSearchScopeOptions() {
  if (!searchScopeSelect) {
    return;
  }
  searchScopeSelect.innerHTML = "";
  const allOption = document.createElement("option");
  allOption.value = "";
  allOption.textContent = "All Documents";
  searchScopeSelect.appendChild(allOption);
  for (const collection of searchCollections) {
    const option = document.createElement("option");
    option.value = collection.id;
    option.textContent = `${collection.name} (${collection.document_count})`;
    searchScopeSelect.appendChild(option);
  }
  searchScopeSelect.value = searchSelectedCollectionId;
  if (searchUseAllScopeBtn) {
    searchUseAllScopeBtn.disabled = !searchSelectedCollectionId;
  }
}

function renderCollectionsTable() {
  if (!collectionsTableBody) {
    return;
  }
  if (!searchCollections.length) {
    collectionsTableBody.innerHTML = '<tr><td colspan="3">No collections yet.</td></tr>';
    return;
  }
  collectionsTableBody.innerHTML = "";
  for (const collection of searchCollections) {
    const row = document.createElement("tr");

    const nameCell = document.createElement("td");
    nameCell.setAttribute("data-label", "Name");
    nameCell.textContent = collection.name;

    const countCell = document.createElement("td");
    countCell.setAttribute("data-label", "Documents");
    countCell.textContent = String(collection.document_count || 0);

    const actionCell = document.createElement("td");
    actionCell.setAttribute("data-label", "Action");
    const actionsWrap = document.createElement("div");
    actionsWrap.className = "table-actions";

    actionsWrap.appendChild(
      createIconActionButton({
        icon: "eye",
        label: `Use collection ${collection.name}`,
        onClick: async () => {
          searchSelectedCollectionId = collection.id;
          renderSearchScopeOptions();
          await loadSearchCollectionDocuments(collection.id);
          logActivity(`Using collection scope: ${collection.name}`);
        },
      })
    );
    actionsWrap.appendChild(
      createIconActionButton({
        icon: "file-text",
        label: `Manage documents in ${collection.name}`,
        onClick: async () => {
          searchSelectedCollectionId = collection.id;
          renderSearchScopeOptions();
          await loadSearchCollectionDocuments(collection.id);
        },
      })
    );
    actionsWrap.appendChild(
      createIconActionButton({
        icon: "trash",
        label: `Delete collection ${collection.name}`,
        onClick: async () => {
          const confirmed = window.confirm(`Delete collection "${collection.name}"?`);
          if (!confirmed) {
            return;
          }
          await deleteSearchCollection(collection.id);
        },
      })
    );
    actionCell.appendChild(actionsWrap);

    row.appendChild(nameCell);
    row.appendChild(countCell);
    row.appendChild(actionCell);
    collectionsTableBody.appendChild(row);
  }
}

function renderSearchCollectionDocPicker() {
  if (!searchCollectionDocPicker) {
    return;
  }
  searchCollectionDocPicker.innerHTML = "";
  if (!searchSelectedCollectionId) {
    searchCollectionDocPicker.disabled = true;
    return;
  }
  searchCollectionDocPicker.disabled = false;
  const selectedIds = new Set(searchSelectedCollectionDocumentIds);
  const filterText = String(searchCollectionDocFilter?.value || "").trim().toLowerCase();
  let visibleOptions = 0;
  for (const doc of searchDocsCatalog) {
    const title = getSearchCatalogTitle(doc);
    const filename = String(doc.filename || "");
    if (
      filterText &&
      !title.toLowerCase().includes(filterText) &&
      !filename.toLowerCase().includes(filterText)
    ) {
      continue;
    }
    const option = document.createElement("option");
    option.value = doc.id;
    option.textContent = title;
    option.disabled = selectedIds.has(doc.id);
    searchCollectionDocPicker.appendChild(option);
    visibleOptions += 1;
  }
  if (visibleOptions === 0) {
    const option = document.createElement("option");
    option.value = "";
    option.textContent = "No matching documents";
    option.disabled = true;
    searchCollectionDocPicker.appendChild(option);
  }
}

function renderSearchCollectionDocumentsTable() {
  if (!searchCollectionDocsTableBody || !searchCollectionDocsLabel || !searchCollectionDocsCount) {
    return;
  }
  if (!searchSelectedCollectionId) {
    searchCollectionDocsLabel.textContent = "Select a collection to manage document scope.";
    searchCollectionDocsCount.textContent = "Documents in collection: 0";
    searchCollectionDocsTableBody.innerHTML = '<tr><td colspan="2">No collection selected.</td></tr>';
    if (searchAddDocsBtn) {
      searchAddDocsBtn.disabled = true;
    }
    renderSearchCollectionDocPicker();
    return;
  }
  const collection = getCollectionById(searchSelectedCollectionId);
  searchCollectionDocsLabel.textContent = collection
    ? `Editing collection: ${collection.name}`
    : "Editing selected collection";
  searchCollectionDocsCount.textContent = `Documents in collection: ${searchSelectedCollectionDocumentIds.length}`;
  if (searchAddDocsBtn) {
    searchAddDocsBtn.disabled = false;
  }
  if (!searchSelectedCollectionDocumentIds.length) {
    searchCollectionDocsTableBody.innerHTML = '<tr><td colspan="2">No documents in this collection.</td></tr>';
    renderSearchCollectionDocPicker();
    return;
  }
  const byId = new Map(searchDocsCatalog.map((doc) => [doc.id, doc]));
  searchCollectionDocsTableBody.innerHTML = "";
  for (const documentId of searchSelectedCollectionDocumentIds) {
    const row = document.createElement("tr");
    const doc = byId.get(documentId);
    const title = doc ? getSearchCatalogTitle(doc) : documentId;
    const titleCell = document.createElement("td");
    titleCell.setAttribute("data-label", "Document");
    const titleBtn = document.createElement("button");
    titleBtn.type = "button";
    titleBtn.className = "link-button";
    titleBtn.textContent = title;
    titleBtn.addEventListener("click", () => navigateToDocument(documentId));
    titleCell.appendChild(titleBtn);

    const actionCell = document.createElement("td");
    actionCell.setAttribute("data-label", "Action");
    const actionsWrap = document.createElement("div");
    actionsWrap.className = "table-actions";
    actionsWrap.appendChild(
      createIconActionButton({
        icon: "trash",
        label: "Remove from collection",
        onClick: async () => {
          await removeDocumentFromSearchCollection(searchSelectedCollectionId, documentId);
        },
      })
    );
    actionCell.appendChild(actionsWrap);

    row.appendChild(titleCell);
    row.appendChild(actionCell);
    searchCollectionDocsTableBody.appendChild(row);
  }
  renderSearchCollectionDocPicker();
}

function renderSearchResultsMeta(message) {
  if (!searchResultsMeta) {
    return;
  }
  searchResultsMeta.textContent = message;
}

function renderSearchResultsTable(payload) {
  if (!searchResultsTableBody) {
    return;
  }
  const hits = Array.isArray(payload?.hits) ? payload.hits : [];
  if (!hits.length) {
    searchResultsTableBody.innerHTML = '<tr><td colspan="6">No matches found.</td></tr>';
    return;
  }
  searchResultsTableBody.innerHTML = "";
  for (const hit of hits) {
    const row = document.createElement("tr");

    const titleCell = document.createElement("td");
    titleCell.setAttribute("data-label", "Title");
    const titleBtn = document.createElement("button");
    titleBtn.type = "button";
    titleBtn.className = "link-button";
    titleBtn.textContent = hit.title || hit.filename || hit.document_id;
    titleBtn.addEventListener("click", () => navigateToDocument(hit.document_id));
    titleCell.appendChild(titleBtn);

    const typeCell = document.createElement("td");
    typeCell.setAttribute("data-label", "Type");
    typeCell.textContent = hit.document_type || "-";

    const correspondentCell = document.createElement("td");
    correspondentCell.setAttribute("data-label", "Correspondent");
    correspondentCell.textContent = hit.correspondent || "-";

    const tagsCell = document.createElement("td");
    tagsCell.setAttribute("data-label", "Tags");
    tagsCell.textContent = Array.isArray(hit.tags) && hit.tags.length ? hit.tags.join(", ") : "-";

    const scoreCell = document.createElement("td");
    scoreCell.setAttribute("data-label", "Score");
    scoreCell.textContent = Number(hit.score || 0).toFixed(3);

    const snippetCell = document.createElement("td");
    snippetCell.setAttribute("data-label", "Snippet");
    snippetCell.textContent = hit.snippet || "-";

    row.appendChild(titleCell);
    row.appendChild(typeCell);
    row.appendChild(correspondentCell);
    row.appendChild(tagsCell);
    row.appendChild(scoreCell);
    row.appendChild(snippetCell);
    searchResultsTableBody.appendChild(row);
  }
}

function renderSearchAskAnswer(payload) {
  if (!searchAskAnswer || !searchAskCitationsBody) {
    return;
  }
  if (!payload) {
    searchAskAnswer.textContent = "No answer yet.";
    searchAskCitationsBody.innerHTML = '<tr><td colspan="2">No citations.</td></tr>';
    return;
  }
  const answer = String(payload.answer || "").trim();
  const note = payload.insufficient_evidence ? "\n\n[Insufficient evidence in selected scope]" : "";
  searchAskAnswer.textContent = answer ? `${answer}${note}` : "No answer returned.";
  const citations = Array.isArray(payload.citations) ? payload.citations : [];
  if (!citations.length) {
    searchAskCitationsBody.innerHTML = '<tr><td colspan="2">No citations.</td></tr>';
    return;
  }
  searchAskCitationsBody.innerHTML = "";
  for (const citation of citations) {
    const row = document.createElement("tr");
    const sourceCell = document.createElement("td");
    sourceCell.setAttribute("data-label", "Source");
    const sourceBtn = document.createElement("button");
    sourceBtn.type = "button";
    sourceBtn.className = "link-button";
    sourceBtn.textContent = citation.title || citation.document_id;
    sourceBtn.addEventListener("click", () => navigateToDocument(citation.document_id));
    sourceCell.appendChild(sourceBtn);

    const quoteCell = document.createElement("td");
    quoteCell.setAttribute("data-label", "Quote");
    quoteCell.textContent = citation.quote || "-";
    row.appendChild(sourceCell);
    row.appendChild(quoteCell);
    searchAskCitationsBody.appendChild(row);
  }
}

function renderSearchAskDebugOutput(debugPayload, enabled) {
  if (!searchAskDebugOutput) {
    return;
  }
  if (!enabled) {
    searchAskDebugOutput.classList.add("view-hidden");
    searchAskDebugOutput.textContent = "Debug output disabled.";
    return;
  }
  searchAskDebugOutput.classList.remove("view-hidden");
  if (!debugPayload) {
    searchAskDebugOutput.textContent = "No debug payload returned.";
    return;
  }
  try {
    searchAskDebugOutput.textContent = JSON.stringify(debugPayload, null, 2);
  } catch {
    searchAskDebugOutput.textContent = String(debugPayload);
  }
}

function setButtonBusy(button, busy, busyLabel = "Loading...") {
  if (!button) {
    return;
  }
  if (busy) {
    if (!button.dataset.originalLabel) {
      button.dataset.originalLabel = button.textContent || "";
    }
    button.textContent = busyLabel;
    button.disabled = true;
    return;
  }
  button.disabled = false;
  if (button.dataset.originalLabel) {
    button.textContent = button.dataset.originalLabel;
  }
}

async function fetchAllDocumentsForSearchCatalog() {
  const limit = 200;
  const maxDocuments = 5000;
  let offset = 0;
  let allDocuments = [];
  while (offset < maxDocuments) {
    const response = await apiFetch(`/documents?limit=${limit}&offset=${offset}`);
    const payload = await response.json();
    if (!response.ok) {
      throw new Error(payload.detail || response.statusText);
    }
    const page = Array.isArray(payload) ? payload : [];
    allDocuments = allDocuments.concat(page);
    if (page.length < limit) {
      break;
    }
    offset += limit;
  }
  return allDocuments.slice(0, maxDocuments);
}

async function loadSearchCollections() {
  const requestSeq = ++searchCollectionsRequestSeq;
  renderTableLoading(collectionsTableBody, 3, "Loading collections...");
  const response = await apiFetch("/collections");
  if (requestSeq !== searchCollectionsRequestSeq) {
    return;
  }
  const payload = await response.json();
  if (requestSeq !== searchCollectionsRequestSeq) {
    return;
  }
  if (!response.ok) {
    logActivity(`Collections load failed: ${payload.detail || response.statusText}`);
    collectionsTableBody.innerHTML = '<tr><td colspan="3">Failed to load collections.</td></tr>';
    return;
  }
  searchCollections = Array.isArray(payload) ? payload : [];
  if (searchSelectedCollectionId && !getCollectionById(searchSelectedCollectionId)) {
    searchSelectedCollectionId = "";
    searchSelectedCollectionDocumentIds = [];
  }
  renderSearchScopeOptions();
  renderCollectionsTable();
  renderSearchCollectionDocumentsTable();
  renderSearchResultsMeta(formatSearchScopeSummary());
}

async function loadSearchDocumentsCatalog() {
  const requestSeq = ++searchDocsCatalogRequestSeq;
  if (searchCollectionDocPicker) {
    searchCollectionDocPicker.innerHTML = "";
    searchCollectionDocPicker.disabled = true;
  }
  try {
    const payload = await fetchAllDocumentsForSearchCatalog();
    if (requestSeq !== searchDocsCatalogRequestSeq) {
      return;
    }
    searchDocsCatalog = payload;
  } catch (error) {
    if (requestSeq !== searchDocsCatalogRequestSeq) {
      return;
    }
    logActivity(`Search document catalog load failed: ${error.message}`);
    searchDocsCatalog = [];
  }
  renderSearchCollectionDocPicker();
}

async function loadSearchCollectionDocuments(collectionId) {
  searchSelectedCollectionId = collectionId || "";
  if (!searchSelectedCollectionId) {
    searchSelectedCollectionDocumentIds = [];
    renderSearchScopeOptions();
    renderSearchCollectionDocumentsTable();
    return;
  }
  const requestSeq = ++searchCollectionDocsRequestSeq;
  renderSearchScopeOptions();
  renderTableLoading(searchCollectionDocsTableBody, 2, "Loading collection documents...");
  const response = await apiFetch(`/collections/${searchSelectedCollectionId}/documents`);
  if (requestSeq !== searchCollectionDocsRequestSeq) {
    return;
  }
  const payload = await response.json();
  if (requestSeq !== searchCollectionDocsRequestSeq) {
    return;
  }
  if (!response.ok) {
    logActivity(`Collection documents load failed: ${payload.detail || response.statusText}`);
    searchSelectedCollectionDocumentIds = [];
    renderSearchCollectionDocumentsTable();
    return;
  }
  searchSelectedCollectionDocumentIds = Array.isArray(payload.document_ids) ? payload.document_ids : [];
  renderSearchCollectionDocumentsTable();
}

async function createSearchCollection() {
  const name = String(searchCollectionNameInput?.value || "").trim();
  const description = String(searchCollectionDescriptionInput?.value || "").trim();
  if (!name) {
    logActivity("Collection name is required.");
    return;
  }
  setButtonBusy(searchCollectionCreateForm?.querySelector("button[type='submit']"), true, "Creating...");
  try {
    const response = await apiFetch("/collections", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ name, description }),
    });
    const payload = await response.json();
    if (!response.ok) {
      logActivity(`Collection create failed: ${payload.detail || response.statusText}`);
      return;
    }
    if (searchCollectionNameInput) {
      searchCollectionNameInput.value = "";
    }
    if (searchCollectionDescriptionInput) {
      searchCollectionDescriptionInput.value = "";
    }
    searchSelectedCollectionId = payload.id || "";
    await loadSearchCollections();
    await loadSearchCollectionDocuments(searchSelectedCollectionId);
    logActivity(`Created collection: ${payload.name}`);
  } finally {
    setButtonBusy(searchCollectionCreateForm?.querySelector("button[type='submit']"), false);
  }
}

async function deleteSearchCollection(collectionId) {
  const response = await apiFetch(`/collections/${collectionId}`, { method: "DELETE" });
  if (!response.ok) {
    const payload = await response.json().catch(() => ({}));
    logActivity(`Collection delete failed: ${payload.detail || response.statusText}`);
    return;
  }
  if (searchSelectedCollectionId === collectionId) {
    searchSelectedCollectionId = "";
    searchSelectedCollectionDocumentIds = [];
  }
  await loadSearchCollections();
  logActivity("Collection deleted.");
}

async function addDocumentsToSearchCollection() {
  if (!searchSelectedCollectionId || !searchCollectionDocPicker) {
    return;
  }
  const pickedIds = [...searchCollectionDocPicker.selectedOptions].map((option) => option.value);
  if (!pickedIds.length) {
    logActivity("Select one or more documents to add.");
    return;
  }
  const merged = [...new Set([...searchSelectedCollectionDocumentIds, ...pickedIds])];
  const response = await apiFetch(`/collections/${searchSelectedCollectionId}/documents`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ document_ids: merged }),
  });
  const payload = await response.json();
  if (!response.ok) {
    logActivity(`Add to collection failed: ${payload.detail || response.statusText}`);
    return;
  }
  searchSelectedCollectionDocumentIds = Array.isArray(payload.document_ids) ? payload.document_ids : [];
  await loadSearchCollections();
  renderSearchCollectionDocumentsTable();
  logActivity(`Added ${pickedIds.length} document(s) to collection.`);
}

async function removeDocumentFromSearchCollection(collectionId, documentId) {
  const response = await apiFetch(`/collections/${collectionId}/documents/${documentId}`, {
    method: "DELETE",
  });
  const payload = await response.json();
  if (!response.ok) {
    logActivity(`Remove from collection failed: ${payload.detail || response.statusText}`);
    return;
  }
  searchSelectedCollectionDocumentIds = Array.isArray(payload.document_ids) ? payload.document_ids : [];
  await loadSearchCollections();
  renderSearchCollectionDocumentsTable();
}

async function runScopedKeywordSearch() {
  const query = String(searchKeywordInput?.value || "").trim();
  if (!query) {
    renderSearchResultsMeta("Enter a query.");
    return;
  }
  const limit = Math.max(1, Math.min(100, Number(searchKeywordLimitSelect?.value || 20)));
  const filters = readSearchScopeFilters();
  renderTableLoading(searchResultsTableBody, 6, "Searching...");
  renderSearchResultsMeta(`Searching... ${formatSearchScopeSummary()}`);
  setButtonBusy(searchKeywordForm?.querySelector("button[type='submit']"), true, "Searching...");
  try {
    const path = searchSelectedCollectionId
      ? `/collections/${searchSelectedCollectionId}/search`
      : "/collections/search";
    const response = await apiFetch(path, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ query, limit, ...filters }),
    });
    const payload = await response.json();
    if (!response.ok) {
      logActivity(`Search failed: ${payload.detail || response.statusText}`);
      renderSearchResultsTable({ hits: [] });
      renderSearchResultsMeta("Search failed.");
      return;
    }
    renderSearchResultsTable(payload);
    const totalHits = Number(payload.total_hits || 0);
    renderSearchResultsMeta(`Found ${totalHits} result(s). ${formatSearchScopeSummary()}`);
    logActivity(`Search completed: ${totalHits} result(s).`);
  } finally {
    setButtonBusy(searchKeywordForm?.querySelector("button[type='submit']"), false);
  }
}

async function runScopedAsk() {
  const question = String(searchAskQuestion?.value || "").trim();
  const debugEnabled = Boolean(searchAskDebugToggle?.checked);
  if (!question) {
    renderSearchAskAnswer({
      answer: "Enter a question.",
      insufficient_evidence: true,
      citations: [],
    });
    renderSearchAskDebugOutput(null, debugEnabled);
    return;
  }
  const topK = Math.max(3, Math.min(60, Number(searchAskTopKInput?.value || 18)));
  const filters = readSearchScopeFilters();
  renderSearchAskAnswer({
    answer: `Querying... ${formatSearchScopeSummary()}`,
    insufficient_evidence: false,
    citations: [],
  });
  renderSearchAskDebugOutput({ status: "waiting_for_response" }, debugEnabled);
  setButtonBusy(searchAskForm?.querySelector("button[type='submit']"), true, "Asking...");
  try {
    const path = searchSelectedCollectionId
      ? `/collections/${searchSelectedCollectionId}/ask`
      : "/collections/ask";
    const response = await apiFetch(path, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ question, top_k_chunks: topK, debug: debugEnabled, ...filters }),
    });
    const payload = await response.json();
    if (!response.ok) {
      renderSearchAskAnswer({
        answer: payload.detail || response.statusText,
        insufficient_evidence: true,
        citations: [],
      });
      renderSearchAskDebugOutput(payload?.debug || null, debugEnabled);
      logActivity(`Ask failed: ${payload.detail || response.statusText}`);
      return;
    }
    renderSearchAskAnswer(payload);
    renderSearchAskDebugOutput(payload?.debug || null, debugEnabled);
    logActivity(`Grounded ask completed in ${getSearchScopeLabel()}.`);
  } finally {
    setButtonBusy(searchAskForm?.querySelector("button[type='submit']"), false);
  }
}

async function initializeSearchView() {
  await Promise.all([loadSearchCollections(), loadSearchDocumentsCatalog()]);
  setActiveSearchSection(searchActiveSectionId);
  if (searchSelectedCollectionId) {
    await loadSearchCollectionDocuments(searchSelectedCollectionId);
  } else {
    renderSearchCollectionDocumentsTable();
  }
  renderSearchResultsMeta(`Ready. ${formatSearchScopeSummary()}`);
}

function setRestartPendingButtonEnabled(enabled) {
  if (!restartPendingBtn) {
    return;
  }
  restartPendingBtn.disabled = !enabled;
}

function isRestartablePendingDocument(doc) {
  const status = String(doc?.status || "").trim().toLowerCase();
  return status.length > 0 && status !== "ready";
}

function getVisiblePendingRowCount() {
  if (!pendingTableBody) {
    return 0;
  }
  return pendingTableBody.querySelectorAll("tr[data-pending-doc-id]").length;
}

async function loadDocumentsList() {
  const requestSeq = ++docsListRequestSeq;
  renderTableLoading(docsTableBody, 7, "Loading documents...");
  renderPaginationControls(0, { hasExactTotal: false });
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

  const listResponse = await apiFetch(`/documents?${query.toString()}`);
  if (requestSeq !== docsListRequestSeq) {
    return;
  }
  const payload = await listResponse.json();
  if (requestSeq !== docsListRequestSeq) {
    return;
  }
  if (!listResponse.ok) {
    logActivity(`Document list failed: ${payload.detail || listResponse.statusText}`);
    return;
  }
  renderDocsList(payload);
  refreshFilterOptionsFromDocuments(payload);
  renderPaginationControls(payload.length, { hasExactTotal: false });

  const countResponse = await apiFetch(`/documents/count?${query.toString()}`);
  if (requestSeq !== docsListRequestSeq) {
    return;
  }
  const countPayload = await countResponse.json();
  if (requestSeq !== docsListRequestSeq) {
    return;
  }
  if (!countResponse.ok) {
    renderPaginationControls(payload.length, { hasExactTotal: false });
    logActivity(`Document count failed: ${countPayload.detail || countResponse.statusText}`);
    return;
  }
  docsTotalCount = Number(countPayload.total || 0);
  renderPaginationControls(payload.length, { hasExactTotal: true });
  logActivity(`Loaded ${payload.length} document(s) of ${docsTotalCount} total`);
}

function renderPaginationControls(currentCount, options = {}) {
  const hasExactTotal = options.hasExactTotal !== false;
  if (!hasExactTotal) {
    if (docsTotalLabel) {
      docsTotalLabel.textContent = "Total documents: loading...";
    }
    if (pageIndicator) {
      pageIndicator.textContent = `Page ${docsPage} / ...`;
    }
    if (pagePrevBtn) {
      pagePrevBtn.disabled = docsPage <= 1;
    }
    if (pageNextBtn) {
      pageNextBtn.disabled = currentCount < docsPageSize;
    }
    return;
  }
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
  const requestSeq = ++pendingDocsRequestSeq;
  renderTableLoading(pendingTableBody, 4, "Loading pending documents...");
  const response = await apiFetch("/documents/pending?limit=200");
  if (requestSeq !== pendingDocsRequestSeq) {
    return;
  }
  const payload = await response.json();
  if (requestSeq !== pendingDocsRequestSeq) {
    return;
  }
  if (!response.ok) {
    // Keep restart enabled if the UI still has visible pending rows.
    setRestartPendingButtonEnabled(getVisiblePendingRowCount() > 0);
    logActivity(`Pending list failed: ${payload.detail || response.statusText}`);
    return;
  }
  renderPendingList(payload);
  const hasRestartable = Array.isArray(payload) && payload.some((doc) => isRestartablePendingDocument(doc));
  setRestartPendingButtonEnabled(hasRestartable);
  logActivity(`Loaded ${payload.length} pending document(s)`);
}

function renderActivityTokenTotal(totalTokens) {
  if (!activityTokenTotal) {
    return;
  }
  const value = Number.isFinite(totalTokens) && totalTokens > 0 ? Math.floor(totalTokens) : 0;
  activityTokenTotal.textContent = `LLM tokens processed: ${value.toLocaleString()}`;
}

function renderActivityTokenLoading() {
  if (!activityTokenTotal) {
    return;
  }
  activityTokenTotal.textContent = "LLM tokens processed: loading...";
}

function renderTableLoading(tbody, colspan, message) {
  if (!tbody) {
    return;
  }
  tbody.innerHTML = `<tr><td colspan="${colspan}">${message}</td></tr>`;
}

async function loadProcessedDocumentsActivity() {
  const requestSeq = ++processedActivityRequestSeq;
  const limit = Math.max(1, normalizePageSize(docsPageSize));
  renderTableLoading(processedDocsTableBody, 4, "Loading processed documents...");
  renderActivityTokenLoading();
  const preferencesPromise = loadUserPreferences().catch(() => ({}));
  const response = await apiFetch(`/documents?status=ready&limit=${limit}&offset=0`);
  if (requestSeq !== processedActivityRequestSeq) {
    return;
  }
  const payload = await response.json();
  if (requestSeq !== processedActivityRequestSeq) {
    return;
  }
  if (!response.ok) {
    logActivity(`Processed documents load failed: ${payload.detail || response.statusText}`);
    return;
  }
  renderProcessedDocsActivity(payload);
  const preferences = await preferencesPromise;
  if (requestSeq !== processedActivityRequestSeq) {
    return;
  }
  const totalTokens = Number(preferences.llm_total_tokens_processed || 0);
  renderActivityTokenTotal(totalTokens);
  logActivity(`Loaded ${payload.length} latest processed document(s).`);
}

async function loadTagStats() {
  const requestSeq = ++tagStatsRequestSeq;
  renderTableLoading(tagsTableBody, 3, "Loading tags...");
  const response = await apiFetch("/documents/metadata/tag-stats");
  if (requestSeq !== tagStatsRequestSeq) {
    return;
  }
  const payload = await response.json();
  if (requestSeq !== tagStatsRequestSeq) {
    return;
  }
  if (!response.ok) {
    logActivity(`Tag stats load failed: ${payload.detail || response.statusText}`);
    return;
  }
  renderTagsList(payload);
  logActivity(`Loaded ${payload.length} tag(s)`);
}

async function loadDocumentTypeStats() {
  const requestSeq = ++documentTypeStatsRequestSeq;
  renderTableLoading(documentTypesTableBody, 3, "Loading document types...");
  const response = await apiFetch("/documents/metadata/document-type-stats");
  if (requestSeq !== documentTypeStatsRequestSeq) {
    return;
  }
  const payload = await response.json();
  if (requestSeq !== documentTypeStatsRequestSeq) {
    return;
  }
  if (!response.ok) {
    logActivity(`Document type stats load failed: ${payload.detail || response.statusText}`);
    return;
  }
  renderDocumentTypesList(payload);
  logActivity(`Loaded ${payload.length} document type(s)`);
}

async function loadDataForCurrentView() {
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
  if (currentViewId === "section-search") {
    await initializeSearchView();
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
  detailOcrContent.textContent = String(payload.ocr_text_preview || "").trim() || "-";
  detailCreatedAt.textContent = doc.created_at
    ? new Date(doc.created_at).toLocaleString()
    : "-";
  detailOcrParsedAt.textContent = payload.ocr_parsed_at
    ? new Date(payload.ocr_parsed_at).toLocaleString()
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

signInForm?.addEventListener("submit", async (event) => {
  event.preventDefault();
  const email = document.getElementById("signInEmail").value.trim();
  const password = document.getElementById("signInPassword").value;
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
  persistSession(payload.access_token, payload.user);
  renderSessionState();
  setAuthMessage(`Signed in as ${payload.user.email}.`);
  await hydrateUserPreferencesForSession();
  applyFiltersToControls();
  setActiveView(currentViewId);
  setActiveNav(currentViewId);
  await loadDataForCurrentView();
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
    allowUnauthorized: true,
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
  await loadDataForCurrentView();
});

signOutBtn?.addEventListener("click", () => {
  clearSession();
  setAuthMessage("Signed out.");
});

searchCollectionCreateForm?.addEventListener("submit", async (event) => {
  event.preventDefault();
  await createSearchCollection();
});

searchRefreshCollectionsBtn?.addEventListener("click", async () => {
  await initializeSearchView();
  logActivity("Search collections refreshed.");
});

searchScopeSelect?.addEventListener("change", async () => {
  searchSelectedCollectionId = String(searchScopeSelect.value || "");
  await loadSearchCollectionDocuments(searchSelectedCollectionId);
});

searchUseAllScopeBtn?.addEventListener("click", async () => {
  searchSelectedCollectionId = "";
  renderSearchScopeOptions();
  await loadSearchCollectionDocuments("");
  renderSearchResultsMeta(`Scope set. ${formatSearchScopeSummary()}`);
  logActivity("Search scope set to all documents.");
});

searchScopeTagsInput?.addEventListener("input", () => {
  renderSearchResultsMeta(formatSearchScopeSummary());
});

searchScopeTypesInput?.addEventListener("input", () => {
  renderSearchResultsMeta(formatSearchScopeSummary());
});

searchCollectionDocFilter?.addEventListener("input", () => {
  renderSearchCollectionDocPicker();
});

searchAddDocsBtn?.addEventListener("click", async () => {
  await addDocumentsToSearchCollection();
});

searchKeywordForm?.addEventListener("submit", async (event) => {
  event.preventDefault();
  await runScopedKeywordSearch();
});

searchAskForm?.addEventListener("submit", async (event) => {
  event.preventDefault();
  await runScopedAsk();
});

searchAskDebugToggle?.addEventListener("change", () => {
  const enabled = Boolean(searchAskDebugToggle.checked);
  renderSearchAskDebugOutput(null, enabled);
});

settingsForm?.addEventListener("submit", async (event) => {
  event.preventDefault();
  const nextTheme = normalizeThemeName(settingsThemeSelect?.value || currentTheme);
  const nextPageSize = normalizePageSize(settingsPageSizeSelect?.value || docsPageSize);
  llmSettings = readLlmSettingsFromControls();
  ocrProvider = normalizeOcrProvider(settingsOcrProviderSelect?.value || ocrProvider);
  ocrAutoSwitch = Boolean(settingsOcrAutoSwitchCheckbox?.checked);
  ocrImageDetail = normalizeOcrImageDetail(settingsOcrImageDetailSelect?.value || ocrImageDetail);
  ocrLlmSettings = readOcrLlmSettingsFromControls();
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
  applyLlmProviderDefaultsToControls(
    nextProvider,
    settingsLlmModelInput,
    settingsLlmBaseUrlInput,
    { force: true }
  );
  setSettingsLlmTestStatus("");
});

settingsOcrProviderSelect?.addEventListener("change", () => {
  ocrProvider = normalizeOcrProvider(settingsOcrProviderSelect.value);
  syncOcrSeparateSettingsVisibility();
  refreshLocalOcrStatus().catch(() => {});
});

settingsOcrLlmProviderSelect?.addEventListener("change", () => {
  const nextProvider = normalizeLlmProvider(settingsOcrLlmProviderSelect.value);
  const defaults = getOcrLlmProviderDefaults(nextProvider);
  if (defaults) {
    if (settingsOcrLlmModelInput) {
      settingsOcrLlmModelInput.value = defaults.model;
    }
    if (settingsOcrLlmBaseUrlInput) {
      settingsOcrLlmBaseUrlInput.value = defaults.base_url;
    }
  }
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

settingsChangePasswordBtn?.addEventListener("click", async () => {
  const currentPassword = String(settingsCurrentPasswordInput?.value || "");
  const newPassword = String(settingsNewPasswordInput?.value || "");
  const confirmPassword = String(settingsConfirmPasswordInput?.value || "");

  if (!currentPassword) {
    setSettingsPasswordStatus("Enter your current password.", "error");
    return;
  }
  if (newPassword.length < 8) {
    setSettingsPasswordStatus("New password must be at least 8 characters.", "error");
    return;
  }
  if (newPassword !== confirmPassword) {
    setSettingsPasswordStatus("New password and confirmation do not match.", "error");
    return;
  }

  setSettingsPasswordStatus("Updating password...");
  try {
    const response = await apiFetch("/users/me/password", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        current_password: currentPassword,
        new_password: newPassword,
      }),
    });
    const payload = await response.json();
    if (!response.ok) {
      setSettingsPasswordStatus(payload.detail || response.statusText, "error");
      return;
    }
    if (settingsCurrentPasswordInput) {
      settingsCurrentPasswordInput.value = "";
    }
    if (settingsNewPasswordInput) {
      settingsNewPasswordInput.value = "";
    }
    if (settingsConfirmPasswordInput) {
      settingsConfirmPasswordInput.value = "";
    }
    setSettingsPasswordStatus(payload.message || "Password updated successfully.", "success");
    logActivity("Password updated successfully.");
  } catch (error) {
    setSettingsPasswordStatus(error.message || "Failed to update password.", "error");
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
  if (currentViewId === "section-document") {
    currentDocumentId = new URLSearchParams(window.location.search).get("id") || "";
  }
  await loadDataForCurrentView();
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
  if (currentViewId === "section-document") {
    currentDocumentId = new URLSearchParams(window.location.search).get("id") || "";
  }
  loadDataForCurrentView().catch((error) => {
    logActivity(`Initial ${currentViewId} load failed: ${error.message}`);
  });
}

applyTheme(currentTheme);
setActiveSearchSection(searchActiveSectionId);

initializeApp().catch((error) => {
  setAuthMessage(error.message || "Failed to initialize app.", true);
});
