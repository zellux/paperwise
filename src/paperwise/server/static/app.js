const uploadForm = document.getElementById("uploadForm");
const documentMetaForm = document.getElementById("documentMetaForm");
const backToDocsBtn = document.getElementById("backToDocsBtn");
const reprocessDocumentBtn = document.getElementById("reprocessDocumentBtn");
const deleteDocumentBtn = document.getElementById("deleteDocumentBtn");
const viewDocumentFileBtn = document.getElementById("viewDocumentFileBtn");
const docsFilterForm = document.getElementById("docsFilterForm");
const clearFiltersBtn = document.getElementById("clearFiltersBtn");
const restartPendingBtn = document.getElementById("restartPendingBtn");
const pagePrevBtn = document.getElementById("pagePrevBtn");
const pageNextBtn = document.getElementById("pageNextBtn");
const pageIndicator = document.getElementById("pageIndicator");
const docsTotalLabel = document.getElementById("docsTotalLabel");
const docsProcessingLabel = document.getElementById("docsProcessingLabel");
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
const searchSectionHeading = document.querySelector("#section-search > h2");
const searchResultsMeta = document.getElementById("searchResultsMeta");
const searchResultsTableBody = document.getElementById("searchResultsTableBody");
const searchAskForm = document.getElementById("searchAskForm");
const searchAskQuestion = document.getElementById("searchAskQuestion");
const searchAskNewChatBtn = document.getElementById("searchAskNewChatBtn");
const searchAskThreadSelect = document.getElementById("searchAskThreadSelect");
const searchAskTokenUsage = document.getElementById("searchAskTokenUsage");
const searchAskMessages = document.getElementById("searchAskMessages");
const searchAskAnswer = document.getElementById("searchAskAnswer");
const searchAskCitationsBody = document.getElementById("searchAskCitationsBody");
const searchSubsections = [...document.querySelectorAll(".search-subsection")];
const settingsSubsections = [...document.querySelectorAll(".settings-subsection")];
const settingsSubnavLinks = [...document.querySelectorAll(".settings-subnav-link")];
const settingsThemeSelect = document.getElementById("settingsThemeSelect");
const settingsPageSizeSelect = document.getElementById("settingsPageSizeSelect");
const settingsGroundedQaTopKInput = document.getElementById("settingsGroundedQaTopKInput");
const settingsGroundedQaMaxDocsInput = document.getElementById("settingsGroundedQaMaxDocsInput");
const settingsConnectionsList = document.getElementById("settingsConnectionsList");
const settingsAddConnectionBtn = document.getElementById("settingsAddConnectionBtn");
const settingsModelSummary = document.getElementById("settingsModelSummary");
const settingsMetadataRouteFields = document.getElementById("settingsMetadataRouteFields");
const settingsMetadataConnectionSelect = document.getElementById("settingsMetadataConnectionSelect");
const settingsMetadataModelInput = document.getElementById("settingsMetadataModelInput");
const settingsGroundedQaRouteFields = document.getElementById("settingsGroundedQaRouteFields");
const settingsGroundedQaConnectionSelect = document.getElementById("settingsGroundedQaConnectionSelect");
const settingsGroundedQaModelInput = document.getElementById("settingsGroundedQaModelInput");
const settingsOcrProviderSelect = document.getElementById("settingsOcrProviderSelect");
const settingsOcrStatus = document.getElementById("settingsOcrStatus");
const settingsOcrRouteFields = document.getElementById("settingsOcrRouteFields");
const settingsOcrConnectionSelect = document.getElementById("settingsOcrConnectionSelect");
const settingsOcrModelInput = document.getElementById("settingsOcrModelInput");
const settingsOcrAutoSwitchCheckbox = document.getElementById("settingsOcrAutoSwitchCheckbox");
const settingsOcrImageDetailSelect = document.getElementById("settingsOcrImageDetailSelect");
const settingsCurrentPasswordInput = document.getElementById("settingsCurrentPasswordInput");
const settingsNewPasswordInput = document.getElementById("settingsNewPasswordInput");
const settingsConfirmPasswordInput = document.getElementById("settingsConfirmPasswordInput");
const settingsChangePasswordBtn = document.getElementById("settingsChangePasswordBtn");
const settingsPasswordStatus = document.getElementById("settingsPasswordStatus");
const authGate = document.getElementById("authGate");
const appShell = document.querySelector(".app-shell");
const authTabSignIn = document.getElementById("authTabSignIn");
const authTabSignUp = document.getElementById("authTabSignUp");
const authPanelSignIn = document.getElementById("authPanelSignIn");
const authPanelSignUp = document.getElementById("authPanelSignUp");
const signInForm = document.getElementById("signInForm");
const registerForm = document.getElementById("registerForm");
const authMessage = document.getElementById("authMessage");
const signOutBtn = document.getElementById("signOutBtn");
const sessionUserLabel = document.getElementById("sessionUserLabel");
const brandHomeBtn = document.getElementById("brandHomeBtn");
const fileInput = document.getElementById("fileInput");
const folderInput = document.getElementById("folderInput");
const uploadFolderBtn = document.getElementById("uploadFolderBtn");
const uploadDropzone = document.getElementById("uploadDropzone");
const uploadSelectionLabel = document.getElementById("uploadSelectionLabel");
const uploadSubmitBtn = document.getElementById("uploadSubmitBtn");
const uploadProgressWrap = document.getElementById("uploadProgressWrap");
const uploadProgressBar = document.getElementById("uploadProgressBar");
const uploadProgressStatus = document.getElementById("uploadProgressStatus");

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
const sortableHeaders = [...document.querySelectorAll("th[data-sort-table][data-sort-field]")];
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
  "/ui/settings/account": "section-settings",
  "/ui/settings/display": "section-settings",
  "/ui/settings/models": "section-settings",
};
const VIEW_ID_TO_PATH = {
  "section-docs": "/ui/documents",
  "section-document": "/ui/document",
  "section-search": "/ui/search",
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
const SUPPORTED_THEMES = ["atlas", "ledger", "moss", "ember", "folio", "forge"];
const THEME_STORAGE_KEY = "paperwise.ui.theme";
let currentTheme = "forge";
const SUPPORTED_LLM_PROVIDERS = ["openai", "gemini", "custom"];
const LLM_PROVIDER_DEFAULTS = {
  openai: {
    model: "gpt-4.1-mini",
    base_url: "https://api.openai.com/v1",
  },
  gemini: {
    model: "gemini-2.5-flash",
    base_url: "https://generativelanguage.googleapis.com/v1beta",
  },
};
const OCR_LLM_PROVIDER_DEFAULTS = {
  openai: {
    model: "gpt-4.1-nano",
    base_url: "https://api.openai.com/v1",
  },
  gemini: {
    model: "gemini-2.5-flash",
    base_url: "https://generativelanguage.googleapis.com/v1beta",
  },
};
const SUPPORTED_OCR_PROVIDERS = ["tesseract", "llm"];
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
const DOCS_SORT_FIELDS = new Set(["title", "document_type", "correspondent", "tags", "document_date", "status"]);
let docsSort = { field: "", direction: "" };
let tagStatsSort = { field: "", direction: "" };
let documentTypesSort = { field: "", direction: "" };
let groundedQaTopK = 18;
let groundedQaMaxDocuments = 12;
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
let searchAskMessagesState = [];
let searchAskInFlight = false;
let searchAskMessageSeq = 0;
let searchAskCurrentTokens = 0;
let searchAskTimerId = 0;
let searchAskThreadId = "";
let searchAskThreads = [];
let currentTagStats = [];
let currentDocumentTypeStats = [];
let searchSelectedCollectionId = "";
let searchSelectedCollectionDocumentIds = [];
let searchActiveSectionId = "search-section-keyword";
let settingsActiveSectionId = "settings-section-display";
let uploadInProgress = false;
let uploadSelectionContext = { source: "files", folderName: "" };
const PATH_TO_SEARCH_SECTION_ID = {
  "/ui/collections": "search-section-keyword",
  "/ui/search": "search-section-keyword",
  "/ui/grounded-qa": "search-section-ask",
};
const PATH_TO_SETTINGS_SECTION_ID = {
  "/ui/settings": "settings-section-display",
  "/ui/settings/account": "settings-section-account",
  "/ui/settings/display": "settings-section-display",
  "/ui/settings/models": "settings-section-models",
};
const SETTINGS_SECTION_ID_TO_PATH = {
  "settings-section-account": "/ui/settings/account",
  "settings-section-display": "/ui/settings/display",
  "settings-section-models": "/ui/settings/models",
};

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
  return "forge";
}

function readBootTheme() {
  const bootTheme = normalizeThemeName(document.documentElement?.dataset?.uiTheme || "");
  if (bootTheme !== "forge") {
    return bootTheme;
  }
  try {
    return normalizeThemeName(window.localStorage.getItem(THEME_STORAGE_KEY));
  } catch {
    return "forge";
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
  if (settingsGroundedQaTopKInput && settingsGroundedQaTopKInput.value !== String(groundedQaTopK)) {
    settingsGroundedQaTopKInput.value = String(groundedQaTopK);
  }
  if (
    settingsGroundedQaMaxDocsInput &&
    settingsGroundedQaMaxDocsInput.value !== String(groundedQaMaxDocuments)
  ) {
    settingsGroundedQaMaxDocsInput.value = String(groundedQaMaxDocuments);
  }
  if (settingsOcrProviderSelect && settingsOcrProviderSelect.value !== ocrProvider) {
    settingsOcrProviderSelect.value = ocrProvider;
  }
  if (settingsOcrAutoSwitchCheckbox) {
    settingsOcrAutoSwitchCheckbox.checked = ocrAutoSwitch;
  }
  if (settingsOcrImageDetailSelect && settingsOcrImageDetailSelect.value !== ocrImageDetail) {
    settingsOcrImageDetailSelect.value = ocrImageDetail;
  }
  renderConnectionsList();
  renderTaskRoutingControls();
  renderModelConfigSummary();
  syncTaskRoutingVisibility();
  setActiveSettingsSection(settingsActiveSectionId);
  refreshLocalOcrStatus().catch(() => {});
  setSettingsPasswordStatus("");
  syncUploadAvailability();
}

function formatModelSummaryRow(label, settings, extra = "") {
  if (!settings) {
    return `<tr><td>${escapeHtml(label)}</td><td>-</td><td>Not configured</td></tr>`;
  }
  const detail = `${settings.model}${extra ? `, ${extra}` : ""}`;
  return `<tr><td>${escapeHtml(label)}</td><td>${escapeHtml(settings.connection_name)}</td><td>${escapeHtml(detail)}</td></tr>`;
}

function renderModelConfigSummary() {
  if (!settingsModelSummary) {
    return;
  }
  const metadataSettings = getResolvedTaskSettings("metadata");
  const groundedSettings = getResolvedTaskSettings("grounded_qa");
  const ocrSettings = getResolvedTaskSettings("ocr");

  if (ocrProvider === "tesseract") {
    settingsModelSummary.innerHTML = [
      formatModelSummaryRow("Metadata Extraction", metadataSettings),
      formatModelSummaryRow("Search and Ask Your Docs", groundedSettings),
      "<tr><td>OCR</td><td>Local</td><td>local only</td></tr>",
    ].join("");
    return;
  }

  settingsModelSummary.innerHTML = [
    formatModelSummaryRow("Metadata Extraction", metadataSettings),
    formatModelSummaryRow("Search and Ask Your Docs", groundedSettings),
    formatModelSummaryRow(
      "OCR",
      ocrSettings,
      `auto switch ${ocrAutoSwitch ? "on" : "off"}`
    ),
  ].join("");
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

function migrateLegacyLlmPreferences(preferences) {
  const connections = [];
  const primaryProvider = normalizeLlmProvider(preferences?.llm_provider);
  const primaryBaseUrl = String(preferences?.llm_base_url || "").trim();
  const primaryApiKey = String(preferences?.llm_api_key || "").trim();
  if (primaryProvider || primaryBaseUrl || primaryApiKey) {
    connections.push({
      id: "default-connection",
      name: "Primary Connection",
      provider: primaryProvider,
      base_url: primaryBaseUrl,
      api_key: primaryApiKey,
      default_model: String(preferences?.llm_model || "").trim(),
    });
  }
  const routing = createDefaultLlmRouting();
  routing.metadata.connection_id = connections[0]?.id || "";
  routing.metadata.model = String(preferences?.llm_model || "").trim();
  routing.grounded_qa.connection_id = connections[0]?.id || "";
  routing.grounded_qa.model = String(preferences?.llm_model || "").trim();
  routing.ocr.connection_id = connections[0]?.id || "";
  routing.ocr.model = String(preferences?.llm_model || "").trim();
  const legacyOcrProvider = String(preferences?.ocr_provider || "llm").trim().toLowerCase();
  if (legacyOcrProvider === "tesseract") {
    routing.ocr.engine = "tesseract";
  } else if (legacyOcrProvider === "llm_separate") {
    const ocrProviderName = normalizeLlmProvider(preferences?.ocr_llm_provider);
    const ocrBaseUrl = String(preferences?.ocr_llm_base_url || "").trim();
    const ocrApiKey = String(preferences?.ocr_llm_api_key || "").trim();
    if (ocrProviderName || ocrBaseUrl || ocrApiKey) {
      const sameAsDefault =
        connections[0] &&
        connections[0].provider === ocrProviderName &&
        connections[0].base_url === ocrBaseUrl &&
        connections[0].api_key === ocrApiKey;
      const connectionId = sameAsDefault ? connections[0].id : "ocr-connection";
      if (!sameAsDefault) {
        connections.push({
          id: connectionId,
          name: "OCR Connection",
          provider: ocrProviderName,
          base_url: ocrBaseUrl,
          api_key: ocrApiKey,
          default_model: String(preferences?.ocr_llm_model || "").trim(),
        });
      }
      routing.ocr.connection_id = connectionId;
      routing.ocr.model = String(preferences?.ocr_llm_model || "").trim();
    }
  }
  return { llm_connections: connections, llm_routing: routing };
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
  return migrateLegacyLlmPreferences(preferences || {});
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

function setConnectionTestStatus(connectionId, message, tone = "") {
  connectionTestStatuses.set(connectionId, { message, tone });
  renderConnectionsList();
}

function renderConnectionSelect(selectEl, selectedValue) {
  if (!selectEl) {
    return;
  }
  const options = ["<option value=\"\">Select connection</option>"];
  for (const connection of llmConnections) {
    options.push(
      `<option value="${escapeHtml(connection.id)}"${connection.id === selectedValue ? " selected" : ""}>${escapeHtml(connection.name)}</option>`
    );
  }
  selectEl.innerHTML = options.join("");
}

function syncTaskRoutingVisibility() {
  const ocrLlmMode = normalizeOcrProvider(settingsOcrProviderSelect?.value || ocrProvider) === "llm";
  if (settingsOcrRouteFields) {
    settingsOcrRouteFields.hidden = !ocrLlmMode;
  }
}

function renderTaskRoutingControls() {
  renderConnectionSelect(settingsMetadataConnectionSelect, llmRouting.metadata.connection_id);
  if (settingsMetadataModelInput && settingsMetadataModelInput.value !== llmRouting.metadata.model) {
    settingsMetadataModelInput.value = llmRouting.metadata.model;
  }

  renderConnectionSelect(settingsGroundedQaConnectionSelect, llmRouting.grounded_qa.connection_id);
  if (settingsGroundedQaModelInput && settingsGroundedQaModelInput.value !== llmRouting.grounded_qa.model) {
    settingsGroundedQaModelInput.value = llmRouting.grounded_qa.model;
  }

  renderConnectionSelect(settingsOcrConnectionSelect, llmRouting.ocr.connection_id);
  if (settingsOcrModelInput && settingsOcrModelInput.value !== llmRouting.ocr.model) {
    settingsOcrModelInput.value = llmRouting.ocr.model;
  }
}

function getSuggestedTestModel(connectionId) {
  const connection = getConnectionById(connectionId);
  if (!connection) {
    return "";
  }
  const connectionDefaultModel = String(connection.default_model || "").trim();
  if (connectionDefaultModel) {
    return connectionDefaultModel;
  }
  const metadataSettings = getResolvedTaskSettings("metadata");
  if (metadataSettings?.connection_id === connectionId && metadataSettings.model) {
    return metadataSettings.model;
  }
  const groundedSettings = getResolvedTaskSettings("grounded_qa");
  if (groundedSettings?.connection_id === connectionId && groundedSettings.model) {
    return groundedSettings.model;
  }
  const ocrSettings = getResolvedTaskSettings("ocr");
  if (ocrSettings?.connection_id === connectionId && ocrSettings.model) {
    return ocrSettings.model;
  }
  return getLlmProviderDefaults(connection.provider)?.model || "";
}

async function testConnection(connectionId, buttonEl) {
  const connection = getConnectionById(connectionId);
  if (!connection) {
    return;
  }
  const reason = getConnectionValidationError(connection);
  if (reason) {
    setConnectionTestStatus(connectionId, reason, "error");
    logActivity(`LLM API test blocked: ${reason}`);
    return;
  }
  const previousText = buttonEl?.textContent;
  if (buttonEl) {
    buttonEl.disabled = true;
    buttonEl.textContent = "Testing...";
  }
  setConnectionTestStatus(connectionId, "Testing...", "");
  try {
    const response = await apiFetch("/documents/llm/test", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        connection_name: connection.name,
        provider: connection.provider,
        model: getSuggestedTestModel(connectionId),
        base_url: connection.base_url,
        api_key: connection.api_key,
      }),
    });
    const responseText = await response.text();
    let payload = {};
    try {
      payload = responseText ? JSON.parse(responseText) : {};
    } catch (_error) {
      payload = {};
    }
    if (!response.ok) {
      const errorMessage = formatApiErrorDetail(payload.detail) || responseText || response.statusText;
      setConnectionTestStatus(connectionId, errorMessage, "error");
      logActivity(`LLM API test failed: ${errorMessage}`);
      return;
    }
    setConnectionTestStatus(
      connectionId,
      `Success (${payload.provider} / ${payload.model}). Save settings to keep this connection.`,
      "success"
    );
    logActivity(`LLM API test passed (${payload.provider} / ${payload.model}). Save settings to keep this connection.`);
  } catch (error) {
    setConnectionTestStatus(connectionId, error.message, "error");
    logActivity(`LLM API test failed: ${error.message}`);
  } finally {
    if (buttonEl) {
      buttonEl.disabled = false;
      buttonEl.textContent = previousText || "Test";
    }
  }
}

function renderConnectionsList() {
  if (!settingsConnectionsList) {
    return;
  }
  if (!llmConnections.length) {
    settingsConnectionsList.innerHTML = "<p class=\"settings-group-note\">No model connections yet. Add one to configure LLM-backed tasks.</p>";
    return;
  }
  settingsConnectionsList.innerHTML = llmConnections
    .map((connection, index) => {
      const status = connectionTestStatuses.get(connection.id) || { message: "", tone: "" };
      const showBaseUrlField = providerShowsBaseUrlField(connection.provider);
      const baseUrlHelpText = getConnectionBaseUrlHelpText(connection.provider);
      const apiKeyPlaceholder = getConnectionApiKeyPlaceholder(connection.provider);
      const defaultBaseUrl = getLlmProviderDefaults(connection.provider)?.base_url
        || getOcrLlmProviderDefaults(connection.provider)?.base_url
        || "";
      return `
        <section class="settings-connection-card" data-connection-id="${escapeHtml(connection.id)}">
          <div class="settings-connection-header">
            <h4 class="settings-task-title">${escapeHtml(connection.name || `Connection ${index + 1}`)}</h4>
            <button type="button" class="btn btn-muted settings-remove-connection-btn" data-connection-remove="${escapeHtml(connection.id)}">Remove</button>
          </div>
          <div class="settings-route-grid">
            <label class="label" for="settingsConnectionName-${escapeHtml(connection.id)}">Name</label>
            <input id="settingsConnectionName-${escapeHtml(connection.id)}" data-connection-field="name" data-connection-id="${escapeHtml(connection.id)}" type="text" value="${escapeHtml(connection.name)}" placeholder="e.g. OpenAI main" />
            <label class="label" for="settingsConnectionProvider-${escapeHtml(connection.id)}">Provider</label>
            <select id="settingsConnectionProvider-${escapeHtml(connection.id)}" data-connection-field="provider" data-connection-id="${escapeHtml(connection.id)}">
              <option value="">Select provider</option>
              <option value="openai"${connection.provider === "openai" ? " selected" : ""}>OpenAI</option>
              <option value="gemini"${connection.provider === "gemini" ? " selected" : ""}>Gemini</option>
              <option value="custom"${connection.provider === "custom" ? " selected" : ""}>Custom (OpenAI-Compatible)</option>
            </select>
            ${showBaseUrlField
              ? `
            <label class="label" for="settingsConnectionBaseUrl-${escapeHtml(connection.id)}">Base URL</label>
            <input id="settingsConnectionBaseUrl-${escapeHtml(connection.id)}" data-connection-field="base_url" data-connection-id="${escapeHtml(connection.id)}" type="text" value="${escapeHtml(connection.base_url)}" placeholder="https://api.openai.com/v1" />
            `
              : `
            <span class="label">Base URL</span>
            <div class="settings-group-note">${escapeHtml(baseUrlHelpText || defaultBaseUrl)}</div>
            `}
            <label class="label" for="settingsConnectionApiKey-${escapeHtml(connection.id)}">API Key</label>
            <input id="settingsConnectionApiKey-${escapeHtml(connection.id)}" data-connection-field="api_key" data-connection-id="${escapeHtml(connection.id)}" type="password" value="${escapeHtml(connection.api_key)}" placeholder="${escapeHtml(apiKeyPlaceholder)}" />
            <label class="label" for="settingsConnectionDefaultModel-${escapeHtml(connection.id)}">Default Model</label>
            <input id="settingsConnectionDefaultModel-${escapeHtml(connection.id)}" data-connection-field="default_model" data-connection-id="${escapeHtml(connection.id)}" type="text" value="${escapeHtml(connection.default_model || "")}" placeholder="e.g. gpt-4.1-mini" />
          </div>
          <div class="actions">
            <button type="button" class="btn btn-muted settings-test-connection-btn" data-connection-test="${escapeHtml(connection.id)}">Test</button>
            <span class="settings-inline-status ${status.tone === "success" ? "is-success" : status.tone === "error" ? "is-error" : ""}">${escapeHtml(status.message || "")}</span>
          </div>
        </section>
      `;
    })
    .join("");

  settingsConnectionsList.querySelectorAll("[data-connection-field]").forEach((element) => {
    const eventName = element.tagName === "SELECT" ? "change" : "input";
    element.addEventListener(eventName, () => {
      const connectionId = element.getAttribute("data-connection-id");
      const field = element.getAttribute("data-connection-field");
      const connection = getConnectionById(connectionId);
      if (!connection || !field) {
        return;
      }
      connection[field] = String(element.value || "");
      if (field === "provider") {
        connection.provider = normalizeLlmProvider(connection.provider);
        const defaults = getLlmProviderDefaults(connection.provider) || getOcrLlmProviderDefaults(connection.provider);
        if (providerUsesManagedBaseUrl(connection.provider)) {
          connection.base_url = "";
        } else if (!connection.base_url && defaults?.base_url && !providerUsesManagedBaseUrl(connection.provider)) {
          connection.base_url = defaults.base_url;
        }
        if (!connection.default_model && defaults?.model) {
          connection.default_model = defaults.model;
        }
        if (!connection.name || /^Connection \d+$/.test(connection.name)) {
          connection.name =
            connection.provider ? `${connection.provider[0].toUpperCase()}${connection.provider.slice(1)} Connection` : connection.name;
        }
        renderConnectionsList();
        renderTaskRoutingControls();
        syncTaskRoutingVisibility();
      }
    });
  });

  settingsConnectionsList.querySelectorAll("[data-connection-remove]").forEach((buttonEl) => {
    buttonEl.addEventListener("click", () => {
      const connectionId = buttonEl.getAttribute("data-connection-remove");
      llmConnections = llmConnections.filter((connection) => connection.id !== connectionId);
      connectionTestStatuses.delete(connectionId);
      llmRouting = sanitizeLlmRouting(llmConnections, llmRouting);
      renderSettingsForm();
    });
  });

  settingsConnectionsList.querySelectorAll("[data-connection-test]").forEach((buttonEl) => {
    buttonEl.addEventListener("click", async () => {
      const connectionId = buttonEl.getAttribute("data-connection-test");
      await testConnection(connectionId, buttonEl);
    });
  });
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
  if (folderInput) {
    folderInput.disabled = blocked;
  }
  if (uploadFolderBtn) {
    uploadFolderBtn.disabled = blocked;
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
      docs_sort: normalizeSortState(docsSort, DOCS_SORT_FIELDS),
      last_view: currentViewId,
      ui_theme: currentTheme,
      docs_page_size: docsPageSize,
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
  docsSort = normalizeSortState(preferences.docs_sort, DOCS_SORT_FIELDS);
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
  readFiltersFromUrl();
  setActiveSearchSection(searchActiveSectionId);
  setActiveSettingsSection(settingsActiveSectionId);
  setActiveView(currentViewId);
  setActiveNav(currentViewId);
  renderSortHeaders();
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

function renderStatusBadge(value) {
  if (!value) return '<span class="status-badge">—</span>';
  const cls = `status-badge status-${String(value).toLowerCase()}`;
  return `<span class="${cls}">${escapeHtml(formatStatus(value))}</span>`;
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
  if (event.event_type === "processing_failed") {
    const before = stringifyHistoryValue(changes.status?.before);
    const after = stringifyHistoryValue(changes.status?.after);
    const lines = [`Status: ${before} -> ${after}`];
    const error = changes.error || {};
    if (error.type) {
      lines.push(`Error type: ${stringifyHistoryValue(error.type)}`);
    }
    if (error.message) {
      lines.push(`Error: ${stringifyHistoryValue(error.message)}`);
    }
    return lines;
  }
  if (event.event_type === "processing_completed") {
    const before = stringifyHistoryValue(changes.status?.before);
    const after = stringifyHistoryValue(changes.status?.after);
    const lines = [`Status: ${before} -> ${after}`];
    const parse = changes.parse || {};
    if (parse.parser) {
      lines.push(`OCR parser: ${parse.parser}`);
    }
    const ocrProcess = parse.ocr_process || parse.ocr?.process || null;
    if (ocrProcess && typeof ocrProcess === "object") {
      const location = stringifyHistoryValue(ocrProcess.location);
      const engine = stringifyHistoryValue(ocrProcess.engine);
      const method = stringifyHistoryValue(ocrProcess.method);
      lines.push(`OCR path: ${location} | ${engine} | ${method}`);
      if (ocrProcess.provider) {
        lines.push(`OCR provider: ${ocrProcess.provider}`);
      }
      if (ocrProcess.model) {
        lines.push(`OCR model: ${ocrProcess.model}`);
      }
      if (Number.isFinite(ocrProcess.result_size_bytes)) {
        lines.push(`OCR result size: ${Number(ocrProcess.result_size_bytes).toLocaleString()} bytes`);
      }
    }
    const metadataParse = changes.metadata_parse || null;
    if (metadataParse && typeof metadataParse === "object") {
      if (metadataParse.provider) {
        lines.push(`Metadata provider: ${metadataParse.provider}`);
      }
      if (metadataParse.model) {
        lines.push(`Metadata model: ${metadataParse.model}`);
      }
      if (Number.isFinite(metadataParse.total_tokens) && Number(metadataParse.total_tokens) > 0) {
        lines.push(`Metadata tokens: ${Number(metadataParse.total_tokens).toLocaleString()}`);
      }
    }
    return lines;
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

const SUPPORTED_UPLOAD_LABEL = "Supports: PDF, TXT, MD, DOCX, DOC, PNG, JPG, WEBP, GIF";
const SUPPORTED_UPLOAD_EXTENSIONS = new Set([
  ".pdf",
  ".txt",
  ".md",
  ".markdown",
  ".doc",
  ".docx",
  ".png",
  ".jpg",
  ".jpeg",
  ".webp",
  ".gif",
]);
const SUPPORTED_UPLOAD_MIME_TYPES = new Set([
  "application/msword",
  "application/octet-stream",
  "application/pdf",
  "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
  "image/gif",
  "image/jpeg",
  "image/png",
  "image/webp",
  "text/markdown",
  "text/plain",
]);

function isSupportedUploadFile(file) {
  const name = (file?.name || "").toLowerCase();
  const ext = name.includes(".") ? `.${name.split(".").pop()}` : "";
  const type = String(file?.type || "").split(";")[0].trim().toLowerCase();
  return SUPPORTED_UPLOAD_EXTENSIONS.has(ext) || SUPPORTED_UPLOAD_MIME_TYPES.has(type);
}

function collectSupportedFiles(fileList) {
  return [...(fileList || [])].filter((file) => isSupportedUploadFile(file));
}

function getFolderNameFromFiles(files) {
  for (const file of files || []) {
    const relativePath = String(file?.webkitRelativePath || "").trim();
    if (!relativePath) {
      continue;
    }
    const folderName = relativePath.split("/")[0]?.trim();
    if (folderName) {
      return folderName;
    }
  }
  return "";
}

async function collectFilesFromDirectoryHandle(directoryHandle) {
  const files = [];

  async function visit(handle) {
    for await (const entry of handle.values()) {
      if (entry.kind === "file") {
        files.push(await entry.getFile());
        continue;
      }
      if (entry.kind === "directory") {
        await visit(entry);
      }
    }
  }

  await visit(directoryHandle);
  return files;
}

function applyFolderSelection(selectedFiles, folderName = "") {
  const supportedFiles = collectSupportedFiles(selectedFiles);
  const ignoredCount = selectedFiles.length - supportedFiles.length;

  if (!supportedFiles.length) {
    setSelectedFiles([], { source: "folder", folderName });
    if (selectedFiles.length) {
      logActivity("Folder selection ignored: no supported files were found.");
    }
    return;
  }

  setSelectedFiles(supportedFiles, { source: "folder", folderName });
  if (ignoredCount > 0) {
    logActivity(`Folder selection skipped ${ignoredCount} unsupported file(s).`);
  }
  logActivity(`Ready to upload ${supportedFiles.length} file(s) from folder selection.`);
}

function updateSelectedFilesLabel() {
  if (!uploadSelectionLabel || !fileInput) {
    return;
  }
  const files = fileInput.files ? [...fileInput.files] : [];
  if (!files.length) {
    uploadSelectionLabel.textContent = SUPPORTED_UPLOAD_LABEL;
    return;
  }
  if (files.length === 1) {
    uploadSelectionLabel.textContent = `Selected: ${files[0].name}`;
    return;
  }
  if (uploadSelectionContext.source === "folder" && uploadSelectionContext.folderName) {
    uploadSelectionLabel.textContent = `Selected ${files.length} files from ${uploadSelectionContext.folderName}`;
    return;
  }
  uploadSelectionLabel.textContent = `Selected ${files.length} files`;
}

function hideUploadProgress() {
  if (uploadProgressWrap) {
    uploadProgressWrap.hidden = true;
  }
  if (uploadProgressBar) {
    uploadProgressBar.max = 1;
    uploadProgressBar.value = 0;
  }
  if (uploadProgressStatus) {
    uploadProgressStatus.textContent = "Ready.";
  }
}

function showUploadProgress(processed, total, message) {
  if (!uploadProgressWrap || !uploadProgressBar || !uploadProgressStatus) {
    return;
  }
  uploadProgressWrap.hidden = false;
  uploadProgressBar.max = Math.max(total, 1);
  uploadProgressBar.value = Math.max(0, Math.min(processed, total));
  uploadProgressStatus.textContent = message;
}

function syncUploadProgressFromSelection() {
  if (!fileInput || uploadInProgress) {
    return;
  }
  const files = fileInput.files ? [...fileInput.files] : [];
  if (files.length <= 1) {
    hideUploadProgress();
    return;
  }
  showUploadProgress(0, files.length, `Ready to upload ${files.length} files.`);
}

function setSelectedFiles(files, options = {}) {
  if (!fileInput) {
    return;
  }
  const data = new DataTransfer();
  for (const file of files) {
    data.items.add(file);
  }
  fileInput.files = data.files;
  uploadSelectionContext = {
    source: options.source === "folder" ? "folder" : "files",
    folderName: String(options.folderName || "").trim(),
  };
  updateSelectedFilesLabel();
  syncUploadProgressFromSelection();
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

function setActiveAuthTab(tab) {
  const isSignUp = tab === "signup";
  authTabSignIn?.classList.toggle("is-active", !isSignUp);
  authTabSignIn?.setAttribute("aria-selected", String(!isSignUp));
  authTabSignUp?.classList.toggle("is-active", isSignUp);
  authTabSignUp?.setAttribute("aria-selected", String(isSignUp));
  authPanelSignIn?.classList.toggle("view-hidden", isSignUp);
  authPanelSignUp?.classList.toggle("view-hidden", !isSignUp);
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
  applyTheme("forge");
  llmConnections = [];
  llmRouting = createDefaultLlmRouting();
  ocrProvider = "llm";
  ocrAutoSwitch = false;
  ocrImageDetail = "auto";
  connectionTestStatuses.clear();
  docsPage = 1;
  docsPageSize = 20;
  docsSort = { field: "", direction: "" };
  tagStatsSort = { field: "", direction: "" };
  documentTypesSort = { field: "", direction: "" };
  currentTagStats = [];
  currentDocumentTypeStats = [];
  docsFilters = sanitizeDocsFilters({
    tag: [],
    correspondent: [],
    document_type: [],
    status: ["ready"],
  });
  searchCollections = [];
  searchDocsCatalog = [];
  searchAskMessagesState = [];
  searchAskCurrentTokens = 0;
  searchAskThreadId = "";
  searchAskThreads = [];
  searchSelectedCollectionId = "";
  searchSelectedCollectionDocumentIds = [];
  searchActiveSectionId = "search-section-keyword";
  currentViewId = "section-docs";
  setActiveSearchSection(searchActiveSectionId);
  renderSearchScopeOptions();
  renderSearchAskTokenUsage();
  renderSearchAskThreadSelect();
  renderCollectionsTable();
  renderSearchCollectionDocumentsTable();
  renderSearchResultsTable({ hits: [] });
  renderSearchResultsMeta("No search run yet.");
  renderSearchAskMessages();
  renderSearchAskAnswer(null);
  renderSettingsForm();
  renderSortHeaders();
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
  const defaultSectionId = "search-section-keyword";
  const nextSectionId = searchSubsections.some((section) => section.id === sectionId)
    ? sectionId
    : defaultSectionId;
  searchActiveSectionId = nextSectionId;
  for (const section of searchSubsections) {
    section.classList.toggle("view-hidden", section.id !== nextSectionId);
  }
  const showSharedHeader = nextSectionId === "search-section-collections";
  searchSectionHeading?.classList.toggle("view-hidden", !showSharedHeader);
  searchResultsMeta?.classList.toggle("view-hidden", !showSharedHeader);
}

function setActiveSettingsSection(sectionId) {
  const defaultSectionId = "settings-section-display";
  const nextSectionId = settingsSubsections.some((section) => section.id === sectionId)
    ? sectionId
    : defaultSectionId;
  settingsActiveSectionId = nextSectionId;
  for (const section of settingsSubsections) {
    section.classList.toggle("view-hidden", section.id !== nextSectionId);
  }
  for (const link of settingsSubnavLinks) {
    link.classList.toggle("active", link.dataset.settingsSection === nextSectionId);
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

function compareSortValues(left, right) {
  const leftNumber = Number(left);
  const rightNumber = Number(right);
  const leftIsNumber = Number.isFinite(leftNumber) && String(left).trim() !== "";
  const rightIsNumber = Number.isFinite(rightNumber) && String(right).trim() !== "";
  if (leftIsNumber && rightIsNumber) {
    return leftNumber - rightNumber;
  }
  return String(left || "").localeCompare(String(right || ""), undefined, {
    sensitivity: "base",
    numeric: true,
  });
}

function sortCollection(items, sortState, valueGetters) {
  const sorted = [...items];
  if (!sortState.field || !sortState.direction) {
    return sorted;
  }
  const getValue = valueGetters[sortState.field];
  if (typeof getValue !== "function") {
    return sorted;
  }
  sorted.sort((left, right) => {
    const comparison = compareSortValues(getValue(left), getValue(right));
    return sortState.direction === "desc" ? -comparison : comparison;
  });
  return sorted;
}

function getSortStateForTable(tableName) {
  if (tableName === "docs") {
    return docsSort;
  }
  if (tableName === "tags") {
    return tagStatsSort;
  }
  if (tableName === "document-types") {
    return documentTypesSort;
  }
  return { field: "", direction: "" };
}

function renderSortHeaders() {
  for (const header of sortableHeaders) {
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
  setSelectOptions(filterStatus, ["received", "processing", "failed", "ready", ...statuses]);
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
  url.searchParams.delete("sort_by");
  url.searchParams.delete("sort_dir");

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
  if (docsSort.field && docsSort.direction) {
    url.searchParams.set("sort_by", docsSort.field);
    url.searchParams.set("sort_dir", docsSort.direction);
  }
  let viewPath = VIEW_ID_TO_PATH[currentViewId];
  if (currentViewId === "section-settings") {
    viewPath = SETTINGS_SECTION_ID_TO_PATH[settingsActiveSectionId] || "/ui/settings/account";
  }
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
  docsSort = normalizeSortState(
    {
      field: params.get("sort_by") || "",
      direction: params.get("sort_dir") || "",
    },
    DOCS_SORT_FIELDS
  );
  const viewFromUrl = params.get("view");
  const mappedViewId = viewFromUrl ? (VIEW_PARAM_TO_ID[viewFromUrl] || viewFromUrl) : "";
  const pathViewId = getCurrentPathViewId();
  const pathSearchSectionId = PATH_TO_SEARCH_SECTION_ID[path];
  const pathSettingsSectionId = PATH_TO_SETTINGS_SECTION_ID[path];
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
  if (pathSettingsSectionId) {
    settingsActiveSectionId = pathSettingsSectionId;
  }
}

async function applyFiltersFromControls() {
  readFiltersFromControls();
  docsPage = 1;
  syncUrlFromFilters();
  await loadDocumentsList();
}

async function openDocumentsWithFilters(nextFilters, activityMessage = "") {
  if (Object.prototype.hasOwnProperty.call(nextFilters, "q")) {
    docsFilters.q = String(nextFilters.q || "").trim();
  }
  if (Object.prototype.hasOwnProperty.call(nextFilters, "tag")) {
    docsFilters.tag = unique(nextFilters.tag || []);
  }
  if (Object.prototype.hasOwnProperty.call(nextFilters, "correspondent")) {
    docsFilters.correspondent = unique(nextFilters.correspondent || []);
  }
  if (Object.prototype.hasOwnProperty.call(nextFilters, "document_type")) {
    docsFilters.document_type = unique(nextFilters.document_type || []);
  }
  if (Object.prototype.hasOwnProperty.call(nextFilters, "status")) {
    docsFilters.status = unique(nextFilters.status || []);
  }
  docsPage = 1;
  applyFiltersToControls();
  setActiveView("section-docs");
  setActiveNav("section-docs");
  syncUrlFromFilters();
  await loadDocumentsList();
  if (activityMessage) {
    logActivity(activityMessage);
  }
}

function navigateToDocument(documentId) {
  const url = new URL("/ui/document", window.location.origin);
  url.searchParams.set("id", documentId);
  window.location.href = `${url.pathname}?${url.searchParams.toString()}`;
}

function createTagFilterButton(tag) {
  const button = document.createElement("button");
  button.type = "button";
  button.className = "tag-pill tag-pill-button";
  button.textContent = tag;
  button.title = `Show documents tagged ${tag}`;
  button.addEventListener("click", async () => {
    await openDocumentsWithFilters(
      {
        q: "",
        tag: [tag],
        correspondent: [],
        document_type: [],
        status: [],
      },
      `Filtered documents by tag: ${tag}`
    );
  });
  return button;
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

async function deleteDocumentById(documentId, options = {}) {
  const documentLabel = String(options.documentLabel || documentId || "").trim() || "this document";
  const confirmMessage = `Delete "${documentLabel}"? This permanently removes the file and its metadata.`;
  if (!window.confirm(confirmMessage)) {
    return false;
  }

  const visibleDocRows = docsTableBody?.querySelectorAll("tr[data-doc-id]").length || 0;
  const shouldStepBackPage =
    currentViewId === "section-docs" && docsPage > 1 && visibleDocRows <= 1;

  const response = await apiFetch(`/documents/${documentId}`, {
    method: "DELETE",
  });
  if (!response.ok) {
    const payload = await response.json().catch(() => ({}));
    logActivity(`Document delete failed: ${payload.detail || response.statusText}`);
    return false;
  }

  if (shouldStepBackPage) {
    docsPage -= 1;
  }
  if (currentDocumentId === documentId) {
    currentDocumentId = "";
    setActiveView("section-docs");
    setActiveNav("section-docs");
    syncUrlFromFilters();
  }

  await loadDocumentsList();
  await loadPendingDocuments();

  if (currentViewId === "section-activity") {
    await loadProcessedDocumentsActivity();
  }
  if (currentViewId === "section-tags") {
    await loadTagStats();
  }
  if (currentViewId === "section-document-types") {
    await loadDocumentTypeStats();
  }

  logActivity(`Deleted document ${documentId}.`);
  return true;
}

function renderDocsList(documents) {
  renderSortHeaders();
  if (!documents.length) {
    docsTableBody.innerHTML = '<tr><td colspan="7">No documents found.</td></tr>';
    return;
  }
  docsTableBody.innerHTML = "";
  for (const doc of documents) {
    const row = document.createElement("tr");
    row.setAttribute("data-doc-id", doc.id);

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
        pills.appendChild(createTagFilterButton(tag));
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
    statusCell.innerHTML = renderStatusBadge(doc.status);
    if (doc.status === "failed") {
      const note = document.createElement("div");
      note.className = "pending-error-note";
      note.textContent = "Open document history for failure details.";
      statusCell.appendChild(note);
    }

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
    actionsWrap.appendChild(
      createIconActionButton({
        icon: "trash",
        label: "Delete document",
        onClick: async () => {
          await deleteDocumentById(doc.id, {
            documentLabel: getSuggestedTitle(doc),
          });
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
  const sortedTagStats = sortCollection(tagStats, tagStatsSort, {
    tag: (item) => item.tag,
    document_count: (item) => item.document_count,
  });
  renderSortHeaders();
  if (!sortedTagStats.length) {
    tagsTableBody.innerHTML = '<tr><td colspan="3">No tags found.</td></tr>';
    return;
  }
  tagsTableBody.innerHTML = "";
  for (const stat of sortedTagStats) {
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
          await openDocumentsWithFilters(
            {
              q: "",
              tag: [stat.tag],
              correspondent: [],
              document_type: [],
              status: [],
            },
            `Filtered documents by tag: ${stat.tag}`
          );
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
  const sortedTypeStats = sortCollection(typeStats, documentTypesSort, {
    document_type: (item) => item.document_type,
    document_count: (item) => item.document_count,
  });
  renderSortHeaders();
  if (!sortedTypeStats.length) {
    documentTypesTableBody.innerHTML = '<tr><td colspan="3">No document types found.</td></tr>';
    return;
  }
  documentTypesTableBody.innerHTML = "";
  for (const stat of sortedTypeStats) {
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
          await openDocumentsWithFilters(
            {
              q: "",
              tag: [],
              correspondent: [],
              document_type: [stat.document_type],
              status: [],
            },
            `Filtered documents by type: ${stat.document_type}`
          );
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
    statusCell.innerHTML = renderStatusBadge(doc.status);
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
    statusCell.innerHTML = renderStatusBadge(doc.status);

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
  return "All Documents";
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
  return {};
}

function formatSearchScopeSummary() {
  return "All Documents";
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
  if (!searchAskAnswer && !searchAskCitationsBody) {
    return;
  }
  if (!payload) {
    if (searchAskAnswer) {
      searchAskAnswer.innerHTML = "<p>No answer yet.</p>";
    }
    if (searchAskCitationsBody) {
      searchAskCitationsBody.innerHTML = '<tr><td colspan="2">No citations.</td></tr>';
    }
    return;
  }
  const answer = String(payload.answer || "").trim();
  const note = payload.insufficient_evidence ? "\n\n_Insufficient evidence in selected scope._" : "";
  const markdown = answer ? `${answer}${note}` : "No answer returned.";
  if (searchAskAnswer) {
    searchAskAnswer.innerHTML = renderMarkdown(markdown);
  }
  if (!searchAskCitationsBody) {
    return;
  }
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

function appendSearchAskMessage(role, content, options = {}) {
  const normalizedRole = role === "user" || role === "status" ? role : "assistant";
  const message = {
    id: `chat-message-${++searchAskMessageSeq}`,
    role: normalizedRole,
    content: String(content || "").trim(),
    pending: Boolean(options.pending),
    toolCalls: Array.isArray(options.toolCalls) ? options.toolCalls : [],
    citations: Array.isArray(options.citations) ? options.citations : [],
    statusKind: String(options.statusKind || "").trim(),
    statusSummary: String(options.statusSummary || "").trim(),
    statusDetail: String(options.statusDetail || "").trim(),
    expanded: Boolean(options.expanded),
    activity: Boolean(options.activity),
    activityRounds: Array.isArray(options.activityRounds) ? options.activityRounds : [],
  };
  if (!message.content && !message.pending) {
    return null;
  }
  searchAskMessagesState.push(message);
  renderSearchAskMessages();
  return message;
}

function updatePendingSearchAskMessage(message, content, options = {}) {
  if (!message) {
    return;
  }
  message.content = String(content || "").trim();
  message.pending = false;
  message.toolCalls = Array.isArray(options.toolCalls) ? options.toolCalls : [];
  message.citations = Array.isArray(options.citations) ? options.citations : [];
  renderSearchAskMessages();
}

function appendSearchAskStatus(label, detail = "", options = {}) {
  const summary = String(options.summary || label || "Working").trim();
  const fullDetail = String(options.detail || detail || "").trim();
  const compactDetail = String(detail || "").trim();
  const parts = [summary, compactDetail].filter(Boolean);
  return appendSearchAskMessage("status", parts.join(": "), {
    statusKind: options.statusKind || "",
    statusSummary: parts.join(": "),
    statusDetail: fullDetail,
  });
}

function appendSearchAskActivity() {
  return appendSearchAskMessage("status", "Working through document tools.", {
    statusKind: "activity",
    statusSummary: "Working through document tools.",
    activity: true,
    activityRounds: [],
  });
}

function hasActiveSearchAskRound() {
  return searchAskMessagesState.some(
    (message) =>
      message.activity &&
      Array.isArray(message.activityRounds) &&
      message.activityRounds.some((round) => round.startedAt && !round.endedAt),
  );
}

function syncSearchAskTimer() {
  if (hasActiveSearchAskRound()) {
    if (!searchAskTimerId) {
      searchAskTimerId = window.setInterval(() => {
        if (!hasActiveSearchAskRound()) {
          syncSearchAskTimer();
          return;
        }
        renderSearchAskMessages();
      }, 1000);
    }
    return;
  }
  if (searchAskTimerId) {
    window.clearInterval(searchAskTimerId);
    searchAskTimerId = 0;
  }
}

function finishActiveSearchAskRound(activityMessage) {
  if (!activityMessage || !Array.isArray(activityMessage.activityRounds)) {
    return;
  }
  const round = activityMessage.activityRounds.at(-1);
  if (round?.startedAt && !round.endedAt) {
    round.endedAt = Date.now();
  }
  syncSearchAskTimer();
}

function finishAllSearchAskRounds(activityMessage) {
  if (!activityMessage || !Array.isArray(activityMessage.activityRounds)) {
    syncSearchAskTimer();
    return;
  }
  const now = Date.now();
  for (const round of activityMessage.activityRounds) {
    if (round.startedAt && !round.endedAt) {
      round.endedAt = now;
    }
  }
  syncSearchAskTimer();
}

function formatElapsedTime(ms) {
  const totalSeconds = Math.max(0, Math.floor(Number(ms || 0) / 1000));
  const minutes = Math.floor(totalSeconds / 60);
  const seconds = totalSeconds % 60;
  if (minutes > 0) {
    return `${minutes}m ${seconds}s`;
  }
  return `${seconds}s`;
}

function getRoundElapsedLabel(round) {
  if (!round?.startedAt) {
    return "";
  }
  const end = round.endedAt || Date.now();
  return formatElapsedTime(end - round.startedAt);
}

function formatTokenCount(value) {
  const count = Number(value || 0);
  if (!Number.isFinite(count) || count <= 0) {
    return "0";
  }
  return Math.round(count).toLocaleString();
}

function renderSearchAskTokenUsage() {
  if (!searchAskTokenUsage) {
    return;
  }
  searchAskTokenUsage.textContent = `Tokens: ${formatTokenCount(searchAskCurrentTokens)}`;
}

function updateSearchAskTokenUsage(tokenUsage) {
  const nextTotal = Number(tokenUsage?.total_tokens || 0);
  if (!Number.isFinite(nextTotal) || nextTotal < 0) {
    return;
  }
  searchAskCurrentTokens = nextTotal;
  renderSearchAskTokenUsage();
}

function renderSearchAskThreadSelect() {
  if (!searchAskThreadSelect) {
    return;
  }
  const currentValue = searchAskThreadId;
  searchAskThreadSelect.innerHTML = "";
  const placeholder = document.createElement("option");
  placeholder.value = "";
  placeholder.textContent = "Recent chats";
  searchAskThreadSelect.appendChild(placeholder);
  for (const thread of searchAskThreads) {
    const option = document.createElement("option");
    option.value = thread.id;
    option.textContent = thread.title || "Untitled chat";
    searchAskThreadSelect.appendChild(option);
  }
  searchAskThreadSelect.value = currentValue || "";
}

async function loadSearchAskThreads() {
  if (!searchAskThreadSelect) {
    return;
  }
  const response = await apiFetch("/query/chat/threads");
  const payload = await response.json();
  if (!response.ok) {
    logActivity(`Chat history failed: ${payload.detail || response.statusText}`);
    return;
  }
  searchAskThreads = Array.isArray(payload) ? payload : [];
  renderSearchAskThreadSelect();
}

function hydrateSearchAskMessages(messages) {
  searchAskMessagesState = [];
  searchAskMessageSeq = 0;
  for (const item of Array.isArray(messages) ? messages : []) {
    const role = String(item?.role || "").trim().toLowerCase();
    const content = String(item?.content || "").trim();
    if (!content || !["user", "assistant"].includes(role)) {
      continue;
    }
    searchAskMessagesState.push({
      id: `chat-message-${++searchAskMessageSeq}`,
      role,
      content,
      pending: false,
      toolCalls: [],
      citations: Array.isArray(item?.citations) ? item.citations : [],
      statusKind: "",
      statusSummary: "",
      statusDetail: "",
      expanded: false,
      activity: false,
      activityRounds: [],
    });
  }
  renderSearchAskMessages();
}

async function loadSearchAskThread(threadId) {
  const id = String(threadId || "").trim();
  if (!id || searchAskInFlight) {
    return;
  }
  const response = await apiFetch(`/query/chat/threads/${encodeURIComponent(id)}`);
  const payload = await response.json();
  if (!response.ok) {
    logActivity(`Load chat failed: ${payload.detail || response.statusText}`);
    renderSearchAskThreadSelect();
    return;
  }
  searchAskThreadId = payload.id || "";
  updateSearchAskTokenUsage(payload.token_usage);
  hydrateSearchAskMessages(payload.messages || []);
  renderSearchAskThreadSelect();
  logActivity(`Loaded chat: ${payload.title || "Untitled chat"}`);
}

function formatSearchAskJsonDetail(value) {
  try {
    return JSON.stringify(value || {}, null, 2);
  } catch {
    return String(value || "");
  }
}

function renderSearchAskStatusMessage(message, item) {
  const summaryButton = document.createElement("button");
  summaryButton.type = "button";
  summaryButton.className = "chat-status-summary";
  summaryButton.setAttribute("aria-expanded", message.expanded ? "true" : "false");
  summaryButton.dataset.messageId = message.id;

  const marker = document.createElement("span");
  marker.className = "chat-status-marker";
  marker.setAttribute("aria-hidden", "true");
  marker.textContent = message.expanded ? "v" : ">";

  const text = document.createElement("span");
  text.className = "chat-status-summary-text";
  text.textContent = message.statusSummary || message.content || "Working...";

  summaryButton.appendChild(marker);
  summaryButton.appendChild(text);
  item.appendChild(summaryButton);

  if (message.expanded && message.statusDetail) {
    const detail = document.createElement("pre");
    detail.className = "chat-status-detail";
    detail.textContent = message.statusDetail;
    item.appendChild(detail);
  }
}

function formatSearchAskRoundSummary(round) {
  const toolCount = Number(round.toolCallCount || 0);
  const resultCount = Number(round.resultCount || 0);
  const elapsed = getRoundElapsedLabel(round);
  const elapsedText = elapsed ? ` · ${elapsed}` : "";
  if (round.finalReady) {
    return `Round ${round.index}: answer ready${elapsedText}`;
  }
  if (toolCount > 0) {
    const resultText = resultCount > 0 ? `, ${resultCount} result(s)` : "";
    return `Round ${round.index}: ${toolCount} tool call(s)${resultText}${elapsedText}`;
  }
  return `Round ${round.index}: ${round.summary || "LLM request"}${elapsedText}`;
}

function renderSearchAskActivityMessage(message, item) {
  const rounds = message.activityRounds.length
    ? message.activityRounds
    : [{ index: 1, summary: message.statusSummary || message.content || "Working", details: [] }];
  for (const round of rounds) {
    const summaryButton = document.createElement("button");
    summaryButton.type = "button";
    summaryButton.className = "chat-status-summary";
    summaryButton.setAttribute("aria-expanded", round.expanded ? "true" : "false");
    summaryButton.dataset.messageId = message.id;
    summaryButton.dataset.roundIndex = String(round.index);

    const marker = document.createElement("span");
    marker.className = "chat-status-marker";
    marker.setAttribute("aria-hidden", "true");
    marker.textContent = round.expanded ? "v" : ">";

    const text = document.createElement("span");
    text.className = "chat-status-summary-text";
    text.textContent = formatSearchAskRoundSummary(round);

    summaryButton.appendChild(marker);
    summaryButton.appendChild(text);
    if (round.startedAt && !round.endedAt) {
      const live = document.createElement("span");
      live.className = "chat-status-live";
      live.setAttribute("aria-hidden", "true");
      summaryButton.appendChild(live);
    }
    item.appendChild(summaryButton);

    if (round.expanded && round.details?.length) {
      const detail = document.createElement("pre");
      detail.className = "chat-status-detail";
      detail.textContent = round.details.join("\n\n");
      item.appendChild(detail);
    }
  }
}

function renderChatCitations(message, item) {
  if (!Array.isArray(message.citations) || !message.citations.length) {
    return;
  }
  const details = document.createElement("details");
  details.className = "chat-citations";
  const summary = document.createElement("summary");
  summary.textContent = `Sources (${message.citations.length})`;
  details.appendChild(summary);

  const list = document.createElement("div");
  list.className = "chat-citation-list";
  for (const citation of message.citations) {
    const source = document.createElement("button");
    source.type = "button";
    source.className = "chat-citation-source";
    source.textContent = citation.title || citation.document_id || "Source";
    source.addEventListener("click", () => navigateToDocument(citation.document_id));
    list.appendChild(source);
  }
  details.appendChild(list);
  item.appendChild(details);
}

function renderSearchAskMessages() {
  if (!searchAskMessages) {
    return;
  }
  const shouldStickToBottom =
    searchAskMessages.scrollHeight - searchAskMessages.scrollTop - searchAskMessages.clientHeight < 24;
  if (!searchAskMessagesState.length) {
    searchAskMessages.innerHTML = `
      <div class="chat-message chat-message-assistant">
        <div class="chat-message-role">Paperwise</div>
        <div class="chat-message-body markdown-output">Ask a question to begin.</div>
      </div>
    `;
    return;
  }
  searchAskMessages.innerHTML = "";
  for (const message of searchAskMessagesState) {
    const item = document.createElement("div");
    item.className = `chat-message chat-message-${message.role}`;
    if (message.statusKind) {
      item.classList.add(`chat-message-status-${message.statusKind}`);
    }
    if (message.role === "status") {
      if (message.activity) {
        renderSearchAskActivityMessage(message, item);
      } else {
        renderSearchAskStatusMessage(message, item);
      }
      searchAskMessages.appendChild(item);
      continue;
    }
    const role = document.createElement("div");
    role.className = "chat-message-role";
    role.textContent = message.role === "user" ? "You" : message.role === "status" ? "Status" : "Paperwise";
    const body = document.createElement("div");
    body.className = "chat-message-body markdown-output";
    body.innerHTML = renderMarkdown(message.pending ? "Working..." : message.content || "No response.");
    item.appendChild(role);
    item.appendChild(body);
    renderChatCitations(message, item);
    searchAskMessages.appendChild(item);
  }
  if (shouldStickToBottom) {
    searchAskMessages.scrollTop = searchAskMessages.scrollHeight;
  }
}

function resetSearchAskChat() {
  if (searchAskInFlight) {
    return;
  }
  searchAskMessagesState = [];
  searchAskMessageSeq = 0;
  searchAskCurrentTokens = 0;
  searchAskThreadId = "";
  syncSearchAskTimer();
  renderSearchAskTokenUsage();
  renderSearchAskThreadSelect();
  renderSearchAskMessages();
  renderSearchAskAnswer(null);
  if (searchAskQuestion) {
    searchAskQuestion.value = "";
    autoResizeChatTextarea(searchAskQuestion);
    searchAskQuestion.focus();
  }
}

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}

function renderInlineMarkdown(text) {
  let rendered = escapeHtml(text);
  rendered = rendered.replace(/`([^`]+)`/g, "<code>$1</code>");
  rendered = rendered.replace(/\*\*([^*]+)\*\*/g, "<strong>$1</strong>");
  rendered = rendered.replace(/(^|[\s(])\*([^*]+)\*(?=$|[\s).,!?;:])/g, "$1<em>$2</em>");
  return rendered;
}

function flushMarkdownParagraph(buffer, html) {
  if (!buffer.length) {
    return;
  }
  html.push(`<p>${buffer.map((line) => renderInlineMarkdown(line)).join("<br>")}</p>`);
  buffer.length = 0;
}

function splitMarkdownTableRow(line) {
  const trimmed = String(line || "").trim();
  const normalized = trimmed.replace(/^\|/, "").replace(/\|$/, "");
  return normalized.split("|").map((cell) => cell.trim());
}

function isMarkdownTableSeparator(line) {
  const cells = splitMarkdownTableRow(line);
  if (!cells.length) {
    return false;
  }
  return cells.every((cell) => /^:?-{3,}:?$/.test(cell));
}

function renderMarkdownTable(headerLine, bodyLines) {
  const headers = splitMarkdownTableRow(headerLine);
  const bodyRows = bodyLines.map((line) => splitMarkdownTableRow(line));
  const thead = `<thead><tr>${headers.map((cell) => `<th>${renderInlineMarkdown(cell)}</th>`).join("")}</tr></thead>`;
  const tbody = `<tbody>${bodyRows
    .map((cells) => `<tr>${cells.map((cell) => `<td>${renderInlineMarkdown(cell)}</td>`).join("")}</tr>`)
    .join("")}</tbody>`;
  return `<table>${thead}${tbody}</table>`;
}

function getMarkdownListKind(line) {
  if (/^\s*[-*]\s+/.test(line)) {
    return "ul";
  }
  if (/^\s*\d+\.\s+/.test(line)) {
    return "ol";
  }
  return "";
}

function findNextNonEmptyMarkdownLine(lines, startIndex) {
  for (let index = startIndex; index < lines.length; index += 1) {
    const line = String(lines[index] || "").trim();
    if (line) {
      return line;
    }
  }
  return "";
}

function renderMarkdown(markdown) {
  const lines = String(markdown || "").replace(/\r\n/g, "\n").split("\n");
  const html = [];
  const paragraph = [];
  let listKind = "";

  const closeList = () => {
    if (listKind) {
      html.push(listKind === "ol" ? "</ol>" : "</ul>");
      listKind = "";
    }
  };

  for (let index = 0; index < lines.length; index += 1) {
    const rawLine = lines[index];
    const line = rawLine.trimEnd();
    const nextLine = index + 1 < lines.length ? lines[index + 1].trim() : "";
    const headingMatch = line.match(/^(#{1,3})\s+(.+)$/);
    const ulMatch = line.match(/^[-*]\s+(.+)$/);
    const olMatch = line.match(/^(\d+)\.\s+(.+)$/);
    const quoteMatch = line.match(/^>\s+(.+)$/);
    const looksLikeTable = line.includes("|") && nextLine.includes("|") && isMarkdownTableSeparator(nextLine);

    if (!line.trim()) {
      flushMarkdownParagraph(paragraph, html);
      const nextListKind = getMarkdownListKind(findNextNonEmptyMarkdownLine(lines, index + 1));
      if (listKind && nextListKind === listKind) {
        continue;
      }
      closeList();
      continue;
    }

    if (headingMatch) {
      closeList();
      flushMarkdownParagraph(paragraph, html);
      const level = headingMatch[1].length;
      html.push(`<h${level}>${renderInlineMarkdown(headingMatch[2])}</h${level}>`);
      continue;
    }

    if (quoteMatch) {
      closeList();
      flushMarkdownParagraph(paragraph, html);
      html.push(`<blockquote>${renderInlineMarkdown(quoteMatch[1])}</blockquote>`);
      continue;
    }

    if (looksLikeTable) {
      closeList();
      flushMarkdownParagraph(paragraph, html);
      const bodyLines = [];
      index += 2;
      while (index < lines.length) {
        const row = lines[index].trim();
        if (!row || !row.includes("|")) {
          index -= 1;
          break;
        }
        bodyLines.push(row);
        index += 1;
      }
      html.push(renderMarkdownTable(line, bodyLines));
      continue;
    }

    if (ulMatch) {
      flushMarkdownParagraph(paragraph, html);
      if (listKind !== "ul") {
        closeList();
        html.push("<ul>");
        listKind = "ul";
      }
      html.push(`<li>${renderInlineMarkdown(ulMatch[1])}</li>`);
      continue;
    }

    if (olMatch) {
      flushMarkdownParagraph(paragraph, html);
      if (listKind !== "ol") {
        closeList();
        const start = Number(olMatch[1] || 1);
        html.push(start > 1 ? `<ol start="${start}">` : "<ol>");
        listKind = "ol";
      }
      html.push(`<li>${renderInlineMarkdown(olMatch[2])}</li>`);
      continue;
    }

    closeList();
    paragraph.push(line);
  }

  closeList();
  flushMarkdownParagraph(paragraph, html);
  if (!html.length) {
    return "<p>No answer returned.</p>";
  }
  return html.join("");
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
  renderTableLoading(searchResultsTableBody, 6, "Searching...");
  renderSearchResultsMeta("Searching...");
  setButtonBusy(searchKeywordForm?.querySelector("button[type='submit']"), true, "Searching...");
  try {
    const response = await apiFetch("/collections/search", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ query, limit }),
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
    renderSearchResultsMeta(`Found ${totalHits} result(s).`);
    logActivity(`Search completed: ${totalHits} result(s).`);
  } finally {
    setButtonBusy(searchKeywordForm?.querySelector("button[type='submit']"), false);
  }
}

function parseSearchAskStreamEvent(rawEvent) {
  const lines = String(rawEvent || "").split(/\r?\n/);
  let eventType = "message";
  const dataLines = [];
  for (const line of lines) {
    if (line.startsWith("event:")) {
      eventType = line.slice("event:".length).trim() || "message";
      continue;
    }
    if (line.startsWith("data:")) {
      dataLines.push(line.slice("data:".length).trimStart());
    }
  }
  const dataText = dataLines.join("\n");
  let data = {};
  if (dataText) {
    try {
      data = JSON.parse(dataText);
    } catch {
      data = { detail: dataText };
    }
  }
  return { eventType, data };
}

function getSearchAskActivityRound(activityMessage) {
  if (!activityMessage) {
    return null;
  }
  if (!Array.isArray(activityMessage.activityRounds)) {
    activityMessage.activityRounds = [];
  }
  let round = activityMessage.activityRounds.at(-1);
  if (!round) {
    round = {
      index: 1,
      summary: "LLM request",
      details: [],
      toolCallCount: 0,
      resultCount: 0,
      startedAt: Date.now(),
      expanded: false,
    };
    activityMessage.activityRounds.push(round);
  }
  if (!Array.isArray(round.details)) {
    round.details = [];
  }
  return round;
}

function appendSearchAskActivityRound(activityMessage, data) {
  if (!activityMessage) {
    appendSearchAskStatus(data.label || "Working", data.detail || "", {
      statusKind: "request",
      detail: data.detail || "",
    });
    return;
  }
  finishActiveSearchAskRound(activityMessage);
  const round = {
    index: activityMessage.activityRounds.length + 1,
    summary: data.detail || data.label || "LLM request",
    details: [data.detail || data.label || "LLM request"],
    toolCallCount: 0,
    resultCount: 0,
    startedAt: Date.now(),
    expanded: false,
  };
  activityMessage.activityRounds.push(round);
  syncSearchAskTimer();
  renderSearchAskMessages();
}

function appendSearchAskRoundDetail(round, label, detail) {
  if (!round) {
    return;
  }
  const parts = [String(label || "").trim(), String(detail || "").trim()].filter(Boolean);
  if (parts.length) {
    round.details.push(parts.join("\n"));
  }
}

function handleSearchAskStreamEvent(eventType, data, pendingMessage, activityMessage = null) {
  if (eventType === "status") {
    appendSearchAskActivityRound(activityMessage, data);
    return null;
  }
  if (eventType === "llm_response") {
    const toolCallCount = Number(data.tool_call_count || 0);
    updateSearchAskTokenUsage(data.token_usage);
    const round = getSearchAskActivityRound(activityMessage);
    if (round) {
      round.toolCallCount = toolCallCount;
      round.finalReady = toolCallCount === 0;
      round.summary = toolCallCount ? `${toolCallCount} tool call(s) requested` : "answer ready";
      if (toolCallCount === 0 && !round.endedAt) {
        round.endedAt = Date.now();
        syncSearchAskTimer();
      }
      appendSearchAskRoundDetail(round, "LLM response", formatSearchAskJsonDetail(data));
      renderSearchAskMessages();
    }
    return null;
  }
  if (eventType === "token_usage") {
    updateSearchAskTokenUsage(data);
    return null;
  }
  if (eventType === "tool_call") {
    const round = getSearchAskActivityRound(activityMessage);
    if (round) {
      round.toolCallCount = Math.max(Number(round.toolCallCount || 0), Number(round.toolCalls?.length || 0) + 1);
      round.toolCalls = [...(round.toolCalls || []), data.name || "tool"];
      appendSearchAskRoundDetail(round, `Tool call: ${data.name || "tool"}`, formatSearchAskJsonDetail(data.arguments || {}));
      renderSearchAskMessages();
    }
    return null;
  }
  if (eventType === "tool_result") {
    const resultCount = Number(data.result_count || 0);
    const round = getSearchAskActivityRound(activityMessage);
    if (round) {
      round.resultCount = Number(round.resultCount || 0) + resultCount;
      appendSearchAskRoundDetail(round, `Tool result: ${data.name || "tool"}`, formatSearchAskJsonDetail(data));
      renderSearchAskMessages();
    }
    return null;
  }
  if (eventType === "error") {
    finishAllSearchAskRounds(activityMessage);
    const detail = data.detail || "Chat failed.";
    updatePendingSearchAskMessage(pendingMessage, detail);
    renderSearchAskAnswer({ answer: detail, insufficient_evidence: true, citations: [] });
    return { error: detail };
  }
  if (eventType === "final") {
    finishAllSearchAskRounds(activityMessage);
    updateSearchAskTokenUsage(data?.token_usage);
    updatePendingSearchAskMessage(
      pendingMessage,
      data?.message?.content || "No answer returned.",
      { citations: data?.citations || [], toolCalls: data?.tool_calls || [] },
    );
    renderSearchAskAnswer({
      answer: data?.message?.content || "",
      insufficient_evidence: !Array.isArray(data?.citations) || !data.citations.length,
      citations: data?.citations || [],
    });
    return { final: data };
  }
  return null;
}

async function runSearchAskStream(requestBody, pendingMessage, activityMessage) {
  const response = await apiFetch("/query/chat/stream", {
    method: "POST",
    headers: { "Content-Type": "application/json", Accept: "text/event-stream" },
    body: JSON.stringify(requestBody),
  });
  if (!response.ok || !response.body) {
    return null;
  }
  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  let finalPayload = null;
  while (true) {
    const { value, done } = await reader.read();
    buffer += decoder.decode(value || new Uint8Array(), { stream: !done });
    const events = buffer.split(/\n\n/);
    buffer = events.pop() || "";
    for (const rawEvent of events) {
      if (!rawEvent.trim()) {
        continue;
      }
      const { eventType, data } = parseSearchAskStreamEvent(rawEvent);
      const handled = handleSearchAskStreamEvent(eventType, data, pendingMessage, activityMessage);
      if (handled?.error) {
        throw new Error(handled.error);
      }
      if (handled?.final) {
        finalPayload = handled.final;
      }
    }
    if (done) {
      break;
    }
  }
  if (buffer.trim()) {
    const { eventType, data } = parseSearchAskStreamEvent(buffer);
    const handled = handleSearchAskStreamEvent(eventType, data, pendingMessage, activityMessage);
    if (handled?.error) {
      throw new Error(handled.error);
    }
    if (handled?.final) {
      finalPayload = handled.final;
    }
  }
  return finalPayload;
}

async function runScopedAsk() {
  const question = String(searchAskQuestion?.value || "").trim();
  if (searchAskInFlight) {
    appendSearchAskStatus("Still working", "Wait for the current request to finish.");
    return;
  }
  if (!question) {
    appendSearchAskMessage("assistant", "Enter a question.");
    return;
  }
  const topK = normalizeGroundedQaTopK(groundedQaTopK);
  const maxDocuments = normalizeGroundedQaMaxDocuments(groundedQaMaxDocuments);
  appendSearchAskMessage("user", question);
  const activityMessage = appendSearchAskActivity();
  const pendingMessage = appendSearchAskMessage("assistant", "", { pending: true });
  if (searchAskQuestion) {
    searchAskQuestion.value = "";
    autoResizeChatTextarea(searchAskQuestion);
  }
  setButtonBusy(searchAskForm?.querySelector("button[type='submit']"), true, "Asking...");
  searchAskInFlight = true;
  const requestBody = {
    thread_id: searchAskThreadId || null,
    messages: searchAskMessagesState
      .filter((message) => !message.pending && ["user", "assistant"].includes(message.role))
      .map((message) => ({ role: message.role, content: message.content })),
    scope: {
      tag: [],
      document_type: [],
      correspondent: [],
    },
    top_k_chunks: topK,
    max_documents: maxDocuments,
    debug: false,
  };
  try {
    const streamedPayload = await runSearchAskStream(requestBody, pendingMessage, activityMessage);
    if (streamedPayload) {
      searchAskThreadId = streamedPayload.thread_id || searchAskThreadId;
      await loadSearchAskThreads();
      logActivity("Ask Your Docs chat completed.");
      return;
    }
    const response = await apiFetch("/query/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(requestBody),
    });
    const payload = await response.json();
    if (!response.ok) {
      updatePendingSearchAskMessage(pendingMessage, payload.detail || response.statusText);
      renderSearchAskAnswer({ answer: payload.detail || response.statusText, insufficient_evidence: true, citations: [] });
      logActivity(`Ask failed: ${payload.detail || response.statusText}`);
      return;
    }
    updateSearchAskTokenUsage(payload?.token_usage);
    searchAskThreadId = payload?.thread_id || searchAskThreadId;
    updatePendingSearchAskMessage(
      pendingMessage,
      payload?.message?.content || "No answer returned.",
      { citations: payload?.citations || [], toolCalls: payload?.tool_calls || [] },
    );
    renderSearchAskAnswer({
      answer: payload?.message?.content || "",
      insufficient_evidence: !Array.isArray(payload?.citations) || !payload.citations.length,
      citations: payload?.citations || [],
    });
    await loadSearchAskThreads();
    logActivity("Ask Your Docs chat completed.");
  } catch (error) {
    finishAllSearchAskRounds(activityMessage);
    const message = error instanceof Error ? error.message : String(error || "Chat failed.");
    updatePendingSearchAskMessage(pendingMessage, message);
    renderSearchAskAnswer({ answer: message, insufficient_evidence: true, citations: [] });
    logActivity(`Ask failed: ${message}`);
  } finally {
    searchAskInFlight = false;
    syncSearchAskTimer();
    setButtonBusy(searchAskForm?.querySelector("button[type='submit']"), false);
  }
}

async function initializeSearchView() {
  searchCollections = [];
  searchSelectedCollectionId = "";
  searchSelectedCollectionDocumentIds = [];
  await Promise.all([loadSearchDocumentsCatalog(), loadSearchAskThreads()]);
  setActiveSearchSection(searchActiveSectionId);
  renderSearchCollectionDocumentsTable();
  renderSearchResultsMeta("Ready.");
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
  renderSortHeaders();
  renderPaginationControls(0, { hasExactTotal: false });
  const query = new URLSearchParams({
    limit: String(docsPageSize),
    offset: String((docsPage - 1) * docsPageSize),
  });
  if (docsSort.field && docsSort.direction) {
    query.set("sort_by", docsSort.field);
    query.set("sort_dir", docsSort.direction);
  }
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
    pageNextBtn.disabled = docsPage >= totalPages;
  }
}

function renderDocsProcessingCount(count, options = {}) {
  if (!docsProcessingLabel) {
    return;
  }
  if (options.loading) {
    docsProcessingLabel.textContent = "Processing: loading...";
    return;
  }
  if (options.unavailable) {
    docsProcessingLabel.textContent = "Processing: unavailable";
    return;
  }
  docsProcessingLabel.textContent = `Processing: ${Math.max(0, Number(count) || 0).toLocaleString()}`;
}

async function loadPendingDocuments() {
  const requestSeq = ++pendingDocsRequestSeq;
  renderDocsProcessingCount(0, { loading: true });
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
    renderDocsProcessingCount(0, { unavailable: true });
    logActivity(`Pending list failed: ${payload.detail || response.statusText}`);
    return;
  }
  renderPendingList(payload);
  renderDocsProcessingCount(payload.length);
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
  renderSortHeaders();
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
  currentTagStats = [...payload];
  renderTagsList(payload);
  logActivity(`Loaded ${payload.length} tag(s)`);
}

async function loadDocumentTypeStats() {
  const requestSeq = ++documentTypeStatsRequestSeq;
  renderTableLoading(documentTypesTableBody, 3, "Loading document types...");
  renderSortHeaders();
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
  currentDocumentTypeStats = [...payload];
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
  await Promise.all([loadDocumentsList(), loadPendingDocuments()]);
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
  detailStatus.innerHTML = renderStatusBadge(doc.status);
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
    persistSession(payload.access_token, payload.user);
    renderSessionState();
    setAuthMessage(`Signed in as ${payload.user.email}.`);
    await hydrateUserPreferencesForSession();
    applyFiltersToControls();
    setActiveView(currentViewId);
    setActiveNav(currentViewId);
    await loadDataForCurrentView();
  } catch (error) {
    setAuthMessage(error.message || "Failed to sign in.", true);
  }
});

registerForm?.addEventListener("submit", async (event) => {
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
    persistSession(loginPayload.access_token, loginPayload.user);
    renderSessionState();
    setAuthMessage(`Registered ${registerPayload.email}.`);
    await hydrateUserPreferencesForSession();
    applyFiltersToControls();
    setActiveView(currentViewId);
    setActiveNav(currentViewId);
    await loadDataForCurrentView();
  } catch (error) {
    setAuthMessage(error.message || "Failed to create account.", true);
  }
});

authTabSignIn?.addEventListener("click", () => {
  setActiveAuthTab("signin");
});

authTabSignUp?.addEventListener("click", () => {
  setActiveAuthTab("signup");
});

signOutBtn?.addEventListener("click", () => {
  clearSession();
  setAuthMessage("Signed out.");
});

brandHomeBtn?.addEventListener("click", async () => {
  currentDocumentId = "";
  currentViewId = "section-docs";
  setActiveView("section-docs");
  setActiveNav("section-docs");
  syncUrlFromFilters();
  await loadDataForCurrentView();
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

searchAskNewChatBtn?.addEventListener("click", () => {
  resetSearchAskChat();
  logActivity("Ask Your Docs chat reset.");
});

searchAskThreadSelect?.addEventListener("change", async () => {
  await loadSearchAskThread(searchAskThreadSelect.value);
});

searchAskQuestion?.addEventListener("keydown", async (event) => {
  if (event.key !== "Enter" || event.shiftKey || event.metaKey || event.ctrlKey || event.altKey) {
    return;
  }
  event.preventDefault();
  await runScopedAsk();
});

function autoResizeChatTextarea(el) {
  el.style.height = "auto";
  el.style.height = Math.min(el.scrollHeight, 200) + "px";
}

if (searchAskQuestion) {
  searchAskQuestion.addEventListener("input", () => autoResizeChatTextarea(searchAskQuestion));
}

searchAskMessages?.addEventListener("click", (event) => {
  const button = event.target instanceof Element ? event.target.closest(".chat-status-summary") : null;
  if (!(button instanceof HTMLElement)) {
    return;
  }
  const message = searchAskMessagesState.find((item) => item.id === button.dataset.messageId);
  if (!message) {
    return;
  }
  if (message.activity) {
    const roundIndex = Number(button.dataset.roundIndex || 0);
    const round = message.activityRounds.find((item) => Number(item.index) === roundIndex);
    if (!round || !round.details?.length) {
      return;
    }
    round.expanded = !round.expanded;
    renderSearchAskMessages();
    return;
  }
  if (!message.statusDetail) {
    return;
  }
  message.expanded = !message.expanded;
  renderSearchAskMessages();
});

settingsForm?.addEventListener("submit", async (event) => {
  event.preventDefault();
  const nextTheme = normalizeThemeName(settingsThemeSelect?.value || currentTheme);
  const nextPageSize = normalizePageSize(settingsPageSizeSelect?.value || docsPageSize);
  groundedQaTopK = normalizeGroundedQaTopK(settingsGroundedQaTopKInput?.value || groundedQaTopK);
  groundedQaMaxDocuments = normalizeGroundedQaMaxDocuments(
    settingsGroundedQaMaxDocsInput?.value || groundedQaMaxDocuments
  );
  llmConnections = llmConnections
    .map((connection, index) => normalizeConnection(connection, index))
    .filter(Boolean);
  llmRouting = sanitizeLlmRouting(llmConnections, {
    metadata: {
      connection_id: String(settingsMetadataConnectionSelect?.value || "").trim(),
      model: String(settingsMetadataModelInput?.value || "").trim(),
    },
    grounded_qa: {
      connection_id: String(settingsGroundedQaConnectionSelect?.value || "").trim(),
      model: String(settingsGroundedQaModelInput?.value || "").trim(),
    },
    ocr: {
      engine: normalizeOcrProvider(settingsOcrProviderSelect?.value || ocrProvider),
      connection_id: String(settingsOcrConnectionSelect?.value || "").trim(),
      model: String(settingsOcrModelInput?.value || "").trim(),
    },
  });
  ocrProvider = normalizeOcrProvider(settingsOcrProviderSelect?.value || ocrProvider);
  ocrAutoSwitch = Boolean(settingsOcrAutoSwitchCheckbox?.checked);
  ocrImageDetail = normalizeOcrImageDetail(settingsOcrImageDetailSelect?.value || ocrImageDetail);
  renderTaskRoutingControls();
  syncTaskRoutingVisibility();
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
  window.location.reload();
});

settingsOcrProviderSelect?.addEventListener("change", () => {
  ocrProvider = normalizeOcrProvider(settingsOcrProviderSelect.value);
  llmRouting.ocr.engine = ocrProvider;
  syncTaskRoutingVisibility();
  refreshLocalOcrStatus().catch(() => {});
});

settingsAddConnectionBtn?.addEventListener("click", () => {
  llmConnections.push(createEmptyConnection());
  llmRouting = sanitizeLlmRouting(llmConnections, llmRouting);
  renderSettingsForm();
});

settingsMetadataConnectionSelect?.addEventListener("change", () => {
  llmRouting.metadata.connection_id = String(settingsMetadataConnectionSelect.value || "").trim();
});

settingsMetadataModelInput?.addEventListener("input", () => {
  llmRouting.metadata.model = String(settingsMetadataModelInput.value || "").trim();
});

settingsGroundedQaConnectionSelect?.addEventListener("change", () => {
  llmRouting.grounded_qa.connection_id = String(settingsGroundedQaConnectionSelect.value || "").trim();
});

settingsGroundedQaModelInput?.addEventListener("input", () => {
  llmRouting.grounded_qa.model = String(settingsGroundedQaModelInput.value || "").trim();
});

settingsOcrConnectionSelect?.addEventListener("change", () => {
  llmRouting.ocr.connection_id = String(settingsOcrConnectionSelect.value || "").trim();
});

settingsOcrModelInput?.addEventListener("input", () => {
  llmRouting.ocr.model = String(settingsOcrModelInput.value || "").trim();
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
    logActivity("Upload blocked: select at least one supported document or image file.");
    return;
  }

  const uploadedIds = [];
  let failedUploads = 0;
  uploadInProgress = true;
  if (uploadSubmitBtn) {
    uploadSubmitBtn.disabled = true;
  }
  if (fileInput) {
    fileInput.disabled = true;
  }
  if (folderInput) {
    folderInput.disabled = true;
  }
  if (uploadFolderBtn) {
    uploadFolderBtn.disabled = true;
  }
  if (uploadDropzone) {
    uploadDropzone.classList.add("is-disabled");
    uploadDropzone.setAttribute("aria-disabled", "true");
    uploadDropzone.tabIndex = -1;
  }
  if (files.length > 1) {
    showUploadProgress(0, files.length, `Uploading 0 of ${files.length} files...`);
  }
  try {
    for (const [index, file] of files.entries()) {
      logActivity(`Uploading ${file.name}...`);
      try {
        const payload = await uploadDocumentFile(file);
        uploadedIds.push(payload.id);
        logActivity(`Uploaded ${file.name} => document ${payload.id}`);
      } catch (error) {
        failedUploads += 1;
        logActivity(`Upload failed for ${file.name}: ${error.message}`);
      }
      if (files.length > 1) {
        const processed = index + 1;
        const message =
          failedUploads > 0
            ? `Uploading ${processed} of ${files.length} files... ${failedUploads} failed so far.`
            : `Uploading ${processed} of ${files.length} files...`;
        showUploadProgress(processed, files.length, message);
      }
    }
  } finally {
    uploadInProgress = false;
    syncUploadAvailability();
  }

  updateSelectedFilesLabel();
  if (files.length > 1) {
    const successCount = uploadedIds.length;
    const summary =
      failedUploads > 0
        ? `Finished ${successCount} of ${files.length} files. ${failedUploads} failed.`
        : `Finished uploading ${files.length} files.`;
    showUploadProgress(files.length, files.length, summary);
  }
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
  uploadSelectionContext = { source: "files", folderName: "" };
  updateSelectedFilesLabel();
  syncUploadProgressFromSelection();
});

folderInput?.addEventListener("change", () => {
  const selectedFiles = [...(folderInput.files || [])];
  const folderName = getFolderNameFromFiles(selectedFiles);
  applyFolderSelection(selectedFiles, folderName);
  folderInput.value = "";
});

uploadFolderBtn?.addEventListener("click", async () => {
  if (!syncUploadAvailability({ announce: true, navigateToSettings: true })) {
    return;
  }
  if (typeof window.showDirectoryPicker === "function") {
    try {
      const directoryHandle = await window.showDirectoryPicker();
      const selectedFiles = await collectFilesFromDirectoryHandle(directoryHandle);
      applyFolderSelection(selectedFiles, directoryHandle.name || "");
      return;
    } catch (error) {
      if (error?.name === "AbortError") {
        return;
      }
      logActivity("Directory picker unavailable in this browser context. Falling back to file input.");
    }
  }
  folderInput?.click();
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
    logActivity("Drop ignored: only supported document and image types are accepted.");
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

deleteDocumentBtn?.addEventListener("click", async () => {
  if (!currentDocumentId) {
    logActivity("No document selected.");
    return;
  }
  await deleteDocumentById(currentDocumentId, {
    documentLabel: metaTitleInput?.value?.trim() || detailFilename?.textContent || currentDocumentId,
  });
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

for (const header of sortableHeaders) {
  const button = header.querySelector(".table-sort-button");
  button?.addEventListener("click", async () => {
    const tableName = header.dataset.sortTable || "";
    const field = header.dataset.sortField || "";
    if (tableName === "docs") {
      docsSort = getNextSortState(docsSort, field);
      docsPage = 1;
      syncUrlFromFilters();
      renderSortHeaders();
      await loadDocumentsList();
      return;
    }
    if (tableName === "tags") {
      tagStatsSort = getNextSortState(tagStatsSort, field);
      renderTagsList(currentTagStats);
      return;
    }
    if (tableName === "document-types") {
      documentTypesSort = getNextSortState(documentTypesSort, field);
      renderDocumentTypesList(currentDocumentTypeStats);
    }
  });
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
  renderSortHeaders();
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
    renderSortHeaders();
    return;
  }

  await hydrateUserPreferencesForSession();
  applyFiltersToControls();
  renderSettingsForm();
  renderSortHeaders();
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
