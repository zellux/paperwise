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
const searchKeywordForm = document.getElementById("searchKeywordForm");
const searchKeywordInput = document.getElementById("searchKeywordInput");
const searchKeywordLimitSelect = document.getElementById("searchKeywordLimitSelect");
const searchSectionHeading = document.querySelector("#section-search > h2");
const searchResultsMeta = document.getElementById("searchResultsMeta");
const searchResultsTableBody = document.getElementById("searchResultsTableBody");
const searchAskForm = document.getElementById("searchAskForm");
const searchAskQuestion = document.getElementById("searchAskQuestion");
const searchAskNewChatBtn = document.getElementById("searchAskNewChatBtn");
const searchAskThreadSearch = document.getElementById("searchAskThreadSearch");
const searchAskThreadList = document.getElementById("searchAskThreadList");
const searchAskTokenUsage = document.getElementById("searchAskTokenUsage");
const searchAskMessages = document.getElementById("searchAskMessages");
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
const sortableHeaders = [...document.querySelectorAll("th[data-sort-table][data-sort-field]")];
const filterDropdownState = new Map();
let activeFilterDropdown = null;
let currentViewId = "section-docs";
const PATH_TO_VIEW_ID = {
  "/ui/documents": "section-docs",
  "/ui/document": "section-document",
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
let currentDocumentId = "";
let currentUser = null;
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
let docsFilterNavigateTimer = 0;
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
let searchAskMessagesState = [];
let searchAskInFlight = false;
let searchAskMessageSeq = 0;
let searchAskCurrentTokens = 0;
let searchAskTimerId = 0;
let searchAskThreadId = "";
let searchAskThreads = [];
let initialDataCache;
const initialPageDataConsumed = new Set();
let initialChatThreadsConsumed = false;
let initialUserPreferencesConsumed = false;
let currentTagStats = [];
let currentDocumentTypeStats = [];
let settingsActiveSectionId = "settings-section-display";
let uploadInProgress = false;
let uploadSelectionContext = { source: "files", folderName: "" };
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
      window.location.href = "/ui/settings/models";
    }
    return false;
  }

  updateSelectedFilesLabel();
  return true;
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
  if (searchAskThreadList) {
    await loadSearchAskThreads();
  }
  readFiltersFromUrl();
}

// Avoid auth-gate flash on page load when the server rendered an authenticated shell.
if (document.documentElement.classList.contains("has-session") && authGate && appShell) {
  readFiltersFromUrl();
  setActiveSettingsSection(settingsActiveSectionId);
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

function normalizeChatThreadSummary(thread) {
  return {
    id: String(thread?.id || ""),
    title: String(thread?.title || "Untitled chat"),
    message_count: Number(thread?.message_count || 0),
    created_at: String(thread?.created_at || ""),
    updated_at: String(thread?.updated_at || ""),
  };
}

function persistSession(user) {
  currentUser = user || null;
}

function renderSessionState() {
  const signedIn = Boolean(currentUser);
  document.documentElement.classList.toggle("has-session", signedIn);
  authGate.classList.toggle("view-hidden", signedIn);
  appShell.classList.toggle("view-hidden", !signedIn);
  if (sessionUserLabel) {
    sessionUserLabel.textContent = signedIn
      ? `${currentUser.full_name} (${currentUser.email})`
      : "Not signed in";
  }
}

function clearSession() {
  persistSession(null);
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
  searchAskMessagesState = [];
  searchAskCurrentTokens = 0;
  searchAskThreadId = "";
  searchAskThreads = [];
  currentViewId = "section-docs";
  renderSearchAskTokenUsage();
  renderSearchAskThreadSelect();
  renderSearchResultsTable({ hits: [] });
  renderSearchResultsMeta("No search run yet.");
  renderSearchAskMessages();
  renderSettingsForm();
  renderSortHeaders();
  renderActivityTokenTotal(0);
  renderSessionState();
  syncUploadAvailability();
}

async function apiFetch(url, options = {}) {
  const headers = new Headers(options.headers || {});
  const allowUnauthorized = options.allowUnauthorized === true;
  const { allowUnauthorized: _allowUnauthorized, ...fetchOptions } = options;
  const response = await window.fetch(url, { credentials: "same-origin", ...fetchOptions, headers });
  if (response.status === 401 && !allowUnauthorized) {
    clearSession();
    throw new Error("Authentication required");
  }
  return response;
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

function sortRows(items, sortState, valueGetters) {
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
  if (!selectEl) {
    return [];
  }
  return [...selectEl.selectedOptions].map((option) => option.value).filter((value) => value);
}

function setSelectedValues(selectEl, values) {
  if (!selectEl) {
    return;
  }
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
  if (!selectEl) {
    return;
  }
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

function applyDocsStateToUrl(url) {
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
}

function buildDocumentsUrl() {
  const url = new URL("/ui/documents", window.location.origin);
  applyDocsStateToUrl(url);
  const qs = url.searchParams.toString();
  return qs ? `${url.pathname}?${qs}` : url.pathname;
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
  const pathViewId = getCurrentPathViewId();
  const pathSettingsSectionId = PATH_TO_SETTINGS_SECTION_ID[path];
  currentViewId = pathViewId || "section-docs";
  if (pathSettingsSectionId) {
    settingsActiveSectionId = pathSettingsSectionId;
  }
}

function navigateToDocumentsPageFromState() {
  window.location.href = buildDocumentsUrl();
}

function applyFiltersFromControls() {
  readFiltersFromControls();
  docsPage = 1;
  navigateToDocumentsPageFromState();
}

function openDocumentsWithFilters(nextFilters, activityMessage = "") {
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
  if (activityMessage) {
    logActivity(activityMessage);
  }
  navigateToDocumentsPageFromState();
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
    window.location.href = buildDocumentsUrl();
    return true;
  }

  await loadDataForCurrentView();

  logActivity(`Deleted document ${documentId}.`);
  return true;
}

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
  renderSettingsForm();
  syncUploadAvailability();
  return true;
}

function renderDocsList(documents) {
  if (!docsTableBody) {
    return;
  }
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
  const sortedTagStats = sortRows(tagStats, tagStatsSort, {
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
  const sortedTypeStats = sortRows(typeStats, documentTypesSort, {
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
  if (!pendingTableBody) {
    return;
  }
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

function formatSearchAskThreadTime(value) {
  const date = new Date(value || "");
  if (Number.isNaN(date.getTime())) {
    return "";
  }
  const now = new Date();
  const elapsedMs = now.getTime() - date.getTime();
  const elapsedDays = Math.floor(elapsedMs / 86400000);
  if (elapsedDays <= 0 && date.toDateString() === now.toDateString()) {
    const elapsedMinutes = Math.max(1, Math.floor(elapsedMs / 60000));
    if (elapsedMinutes < 60) {
      return `${elapsedMinutes} min ago`;
    }
    return `${Math.floor(elapsedMinutes / 60)} hr ago`;
  }
  const yesterday = new Date(now);
  yesterday.setDate(now.getDate() - 1);
  if (date.toDateString() === yesterday.toDateString()) {
    return "Yesterday";
  }
  return date.toLocaleDateString(undefined, { month: "short", day: "numeric" });
}

function getSearchAskThreadBucket(thread) {
  const date = new Date(thread?.updated_at || thread?.created_at || "");
  if (Number.isNaN(date.getTime())) {
    return "earlier";
  }
  const now = new Date();
  if (date.toDateString() === now.toDateString()) {
    return "today";
  }
  const yesterday = new Date(now);
  yesterday.setDate(now.getDate() - 1);
  if (date.toDateString() === yesterday.toDateString()) {
    return "yesterday";
  }
  return "earlier";
}

function renderSearchAskThreadSelect() {
  const currentValue = searchAskThreadId;
  if (searchAskThreadList) {
    searchAskThreadList.innerHTML = "";
    const query = String(searchAskThreadSearch?.value || "").trim().toLowerCase();
    const filteredThreads = searchAskThreads.filter((thread) =>
      !query || String(thread.title || "").toLowerCase().includes(query)
    );
    if (!filteredThreads.length) {
      const empty = document.createElement("p");
      empty.className = "thread-empty";
      empty.textContent = query ? "No chats match that search." : "No recent chats yet.";
      searchAskThreadList.appendChild(empty);
    } else {
      const groups = [
        ["today", "Today"],
        ["yesterday", "Yesterday"],
        ["earlier", "Earlier"],
      ];
      for (const [bucket, label] of groups) {
        const items = filteredThreads.filter((thread) => getSearchAskThreadBucket(thread) === bucket);
        if (!items.length) {
          continue;
        }
        const group = document.createElement("section");
        group.className = "thread-group";
        const heading = document.createElement("h4");
        heading.className = "thread-group-label";
        heading.textContent = label;
        const list = document.createElement("ul");
        list.className = "thread-list";
        for (const thread of items) {
          const item = document.createElement("li");
          item.className = `thread-item${thread.id === currentValue ? " active" : ""}`;
          const button = document.createElement("button");
          button.type = "button";
          button.className = "thread-button";
          button.dataset.threadId = thread.id;
          const title = document.createElement("span");
          title.className = "thread-title";
          title.textContent = thread.title || "Untitled chat";
          const meta = document.createElement("span");
          meta.className = "thread-meta";
          const updated = formatSearchAskThreadTime(thread.updated_at || thread.created_at);
          const count = Number(thread.message_count || 0);
          meta.textContent = [updated, `${count} msg${count === 1 ? "" : "s"}`].filter(Boolean).join(" · ");
          button.appendChild(title);
          button.appendChild(meta);
          const deleteButton = document.createElement("button");
          deleteButton.type = "button";
          deleteButton.className = "thread-action";
          deleteButton.dataset.deleteThreadId = thread.id;
          deleteButton.title = "Delete chat";
          deleteButton.setAttribute("aria-label", `Delete ${thread.title || "chat"}`);
          deleteButton.disabled = searchAskInFlight;
          deleteButton.textContent = "×";
          item.appendChild(button);
          item.appendChild(deleteButton);
          list.appendChild(item);
        }
        group.appendChild(heading);
        group.appendChild(list);
        searchAskThreadList.appendChild(group);
      }
    }
  }
}

async function loadSearchAskThreads() {
  if (!searchAskThreadList) {
    return;
  }
  const initialData = readInitialData();
  if (
    !initialChatThreadsConsumed &&
    initialData.authenticated === true &&
    Array.isArray(initialData.chat_threads)
  ) {
    initialChatThreadsConsumed = true;
    searchAskThreads = initialData.chat_threads
      .map(normalizeChatThreadSummary)
      .filter((thread) => thread.id);
    renderSearchAskThreadSelect();
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

async function deleteSearchAskThread(threadId) {
  const id = String(threadId || "").trim();
  if (!id || searchAskInFlight) {
    return;
  }
  const thread = searchAskThreads.find((item) => item.id === id);
  const title = thread?.title || "this chat";
  const confirmed = window.confirm(`Delete "${title}" from chat history?`);
  if (!confirmed) {
    return;
  }
  const response = await apiFetch(`/query/chat/threads/${encodeURIComponent(id)}`, {
    method: "DELETE",
  });
  if (!response.ok) {
    const payload = await response.json().catch(() => ({}));
    logActivity(`Delete chat failed: ${payload.detail || response.statusText}`);
    renderSearchAskThreadSelect();
    return;
  }
  searchAskThreads = searchAskThreads.filter((item) => item.id !== id);
  if (searchAskThreadId === id) {
    resetSearchAskChat();
  } else {
    renderSearchAskThreadSelect();
  }
  await loadSearchAskThreads();
  logActivity(`Deleted chat: ${title}`);
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

function getCurrentUserInitials() {
  const source = String(currentUser?.full_name || currentUser?.email || "You").trim();
  const parts = source
    .replace(/@.*/, "")
    .split(/[\s._-]+/)
    .filter(Boolean);
  const initials = parts.slice(0, 2).map((part) => part.charAt(0).toUpperCase()).join("");
  return initials || "Y";
}

function appendSearchAskRoleMeta(item, message) {
  const role = document.createElement("div");
  role.className = "chat-message-role";
  const dot = document.createElement("span");
  dot.className = "chat-role-dot";
  dot.textContent = message.role === "user" ? getCurrentUserInitials() : "P";
  const label = document.createElement("span");
  label.textContent = message.role === "user" ? "You" : "Paperwise";
  role.appendChild(dot);
  role.appendChild(label);
  item.appendChild(role);
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
        <div class="chat-message-role"><span class="chat-role-dot">P</span><span>Paperwise</span></div>
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
    const body = document.createElement("div");
    body.className = "chat-message-body markdown-output";
    body.innerHTML = renderMarkdown(message.pending ? "Working..." : message.content || "No response.");
    appendSearchAskRoleMeta(item, message);
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

async function runKeywordSearch() {
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

async function runAsk() {
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
  renderSearchAskThreadSelect();
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
    await loadSearchAskThreads();
    logActivity("Ask Your Docs chat completed.");
  } catch (error) {
    finishAllSearchAskRounds(activityMessage);
    const message = error instanceof Error ? error.message : String(error || "Chat failed.");
    updatePendingSearchAskMessage(pendingMessage, message);
    logActivity(`Ask failed: ${message}`);
  } finally {
    searchAskInFlight = false;
    syncSearchAskTimer();
    renderSearchAskThreadSelect();
    setButtonBusy(searchAskForm?.querySelector("button[type='submit']"), false);
  }
}

async function initializeSearchView() {
  await loadSearchAskThreads();
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

function hydrateInitialPageDataForCurrentView() {
  if (initialPageDataConsumed.has(currentViewId)) {
    return true;
  }
  const initialData = readInitialData();
  if (initialData.authenticated !== true) {
    return false;
  }

  if (currentViewId === "section-docs" && Array.isArray(initialData.documents)) {
    docsTotalCount = Number(initialData.documents_total || initialData.documents.length || 0);
    docsPage = Math.max(1, Number(initialData.documents_page || docsPage || 1));
    docsPageSize = normalizePageSize(initialData.documents_page_size || docsPageSize);
    refreshFilterOptionsFromDocuments(initialData.documents);
    renderPaginationControls(initialData.documents.length, { hasExactTotal: true });
    renderDocsProcessingCount(Number(initialData.documents_processing_count || 0));
    logActivity(`Loaded ${initialData.documents.length} document(s) of ${docsTotalCount} total`);
    initialPageDataConsumed.add(currentViewId);
    return true;
  }

  if (currentViewId === "section-tags" && Array.isArray(initialData.tag_stats)) {
    currentTagStats = [...initialData.tag_stats];
    renderSortHeaders();
    logActivity(`Loaded ${currentTagStats.length} tag(s)`);
    initialPageDataConsumed.add(currentViewId);
    return true;
  }

  if (currentViewId === "section-document-types" && Array.isArray(initialData.document_type_stats)) {
    currentDocumentTypeStats = [...initialData.document_type_stats];
    renderSortHeaders();
    logActivity(`Loaded ${currentDocumentTypeStats.length} document type(s)`);
    initialPageDataConsumed.add(currentViewId);
    return true;
  }

  if (currentViewId === "section-activity" && Array.isArray(initialData.activity_documents)) {
    renderActivityTokenTotal(Number(initialData.activity_total_tokens || 0));
    logActivity(`Loaded ${initialData.activity_documents.length} latest processed document(s).`);
    initialPageDataConsumed.add(currentViewId);
    return true;
  }

  if (currentViewId === "section-pending" && Array.isArray(initialData.pending_documents)) {
    const hasRestartable = initialData.pending_documents.some((doc) => isRestartablePendingDocument(doc));
    renderDocsProcessingCount(initialData.pending_documents.length);
    setRestartPendingButtonEnabled(hasRestartable);
    logActivity(`Loaded ${initialData.pending_documents.length} pending document(s)`);
    initialPageDataConsumed.add(currentViewId);
    return true;
  }

  if (currentViewId === "section-document" && initialData.document_detail?.document?.id) {
    currentDocumentId = String(initialData.document_detail.document.id || "");
    logActivity(`Opened document ${currentDocumentId}`);
    initialPageDataConsumed.add(currentViewId);
    return true;
  }

  return false;
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
  if (hydrateInitialPageDataForCurrentView()) {
    return;
  }
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
    if (!hydrateSettingsFormFromInitialPreferences()) {
      renderSettingsForm();
    }
    return;
  }
  if (currentViewId === "section-upload") {
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
    persistSession(payload.user);
    renderSessionState();
    setAuthMessage(`Signed in as ${payload.user.email}.`);
    await hydrateUserPreferencesForSession();
    applyFiltersToControls();
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
    persistSession(loginPayload.user);
    renderSessionState();
    setAuthMessage(`Registered ${registerPayload.email}.`);
    await hydrateUserPreferencesForSession();
    applyFiltersToControls();
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

signOutBtn?.addEventListener("click", async () => {
  await apiFetch("/users/logout", { method: "POST", allowUnauthorized: true }).catch(() => {});
  clearSession();
  setAuthMessage("Signed out.");
});

brandHomeBtn?.addEventListener("click", () => {
  window.location.href = "/ui/documents";
});

async function initializeApp() {
  restoreSession();
  if (!currentUser) {
    renderSortHeaders();
    return;
  }

  await hydrateUserPreferencesForSession();
  applyFiltersToControls();
  renderSettingsForm();
  renderSortHeaders();
  syncUploadAvailability();
  if (currentViewId === "section-document") {
    currentDocumentId = new URLSearchParams(window.location.search).get("id") || "";
  }
  loadDataForCurrentView().catch((error) => {
    logActivity(`Initial ${currentViewId} load failed: ${error.message}`);
  });
}

applyTheme(currentTheme);

initializeApp().catch((error) => {
  setAuthMessage(error.message || "Failed to initialize app.", true);
});
