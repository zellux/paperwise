import { readInitialData } from "./initialData.js";
import {
  normalizeOcrAutoSwitch,
  normalizeOcrImageDetail,
} from "./preferences.js";

let ocrProvider = "llm";
let ocrImageDetail = "auto";
let ocrAutoSwitch = false;
let llmConnections = [];
let llmRouting = createDefaultLlmRouting();
let supportedLlmProvidersCache;
let supportedOcrProvidersCache;
let llmProviderDefaultsCache;
let ocrLlmProviderDefaultsCache;

export const LLM_TASK_LABELS = {
  metadata: "Metadata Extraction",
  grounded_qa: "Search and Ask Your Docs",
  ocr: "OCR",
};

export const connectionTestStatuses = new Map();
export const taskTestStatuses = new Map();
export const taskTestsInFlight = new Set();

export const llmState = {
  get ocrProvider() {
    return ocrProvider;
  },
  set ocrProvider(value) {
    ocrProvider = normalizeOcrProvider(value);
  },
  get ocrAutoSwitch() {
    return ocrAutoSwitch;
  },
  set ocrAutoSwitch(value) {
    ocrAutoSwitch = Boolean(value);
  },
  get ocrImageDetail() {
    return ocrImageDetail;
  },
  set ocrImageDetail(value) {
    ocrImageDetail = normalizeOcrImageDetail(value);
  },
  get llmConnections() {
    return llmConnections;
  },
  set llmConnections(value) {
    llmConnections = Array.isArray(value) ? value : [];
  },
  get llmRouting() {
    return llmRouting;
  },
  set llmRouting(value) {
    llmRouting = value && typeof value === "object" ? value : createDefaultLlmRouting();
  },
  connectionTestStatuses,
  taskTestStatuses,
  taskTestsInFlight,
};

export function getSupportedLlmProviders() {
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

export function getSupportedOcrProviders() {
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

export function normalizeLlmProvider(value) {
  const normalized = String(value || "").trim().toLowerCase();
  if (getSupportedLlmProviders().includes(normalized)) {
    return normalized;
  }
  return "";
}

export function normalizeOcrProvider(value) {
  const normalized = String(value || "").trim().toLowerCase();
  if (getSupportedOcrProviders().includes(normalized)) {
    return normalized;
  }
  return "llm";
}

export function getLlmProviderDefaults(provider) {
  const normalized = normalizeLlmProvider(provider);
  if (!normalized) {
    return null;
  }
  return getInitialLlmProviderDefaults()[normalized] || null;
}

export function getOcrLlmProviderDefaults(provider) {
  const normalized = normalizeLlmProvider(provider);
  if (!normalized) {
    return null;
  }
  return getInitialOcrLlmProviderDefaults()[normalized] || null;
}

export function normalizeProviderDefaults(rawDefaults) {
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

export function getInitialLlmProviderDefaults() {
  if (llmProviderDefaultsCache !== undefined) {
    return llmProviderDefaultsCache;
  }
  llmProviderDefaultsCache = normalizeProviderDefaults(readInitialData().llm_provider_defaults);
  return llmProviderDefaultsCache;
}

export function getInitialOcrLlmProviderDefaults() {
  if (ocrLlmProviderDefaultsCache !== undefined) {
    return ocrLlmProviderDefaultsCache;
  }
  ocrLlmProviderDefaultsCache = normalizeProviderDefaults(readInitialData().ocr_llm_provider_defaults);
  return ocrLlmProviderDefaultsCache;
}

export function providerUsesManagedBaseUrl(provider) {
  const normalized = normalizeLlmProvider(provider);
  return normalized === "openai" || normalized === "gemini";
}

export function providerShowsBaseUrlField(provider) {
  return !providerUsesManagedBaseUrl(provider);
}

export function getConnectionBaseUrlHelpText(provider) {
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

export function getConnectionApiKeyPlaceholder(provider) {
  const normalized = normalizeLlmProvider(provider);
  if (normalized === "gemini") {
    return "AIza...";
  }
  return "sk-...";
}

export function getConnectionApiKeyValidationError(provider, apiKey) {
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

export function createEmptyConnection(index = llmConnections.length + 1) {
  return {
    id: `connection-${Date.now()}-${index}`,
    name: `Connection ${index}`,
    provider: "",
    base_url: "",
    api_key: "",
  };
}

export function createDefaultLlmRouting() {
  return {
    metadata: { connection_id: "", model: "" },
    grounded_qa: { connection_id: "", model: "" },
    ocr: { engine: "llm", connection_id: "", model: "" },
  };
}

export function normalizeConnection(connection, index = 0) {
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

export function normalizeLlmPreferences(preferences) {
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

export function sanitizeLlmRouting(connections, routing) {
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

export function getConnectionById(connectionId) {
  return llmConnections.find((connection) => connection.id === connectionId) || null;
}

export function getResolvedTaskSettings(task) {
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

export function getConnectionValidationError(connection) {
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

export function getLlmUploadBlockReason() {
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

export function applyLlmPreferences(preferences) {
  const normalizedLlmPreferences = normalizeLlmPreferences(preferences);
  llmConnections = normalizedLlmPreferences.llm_connections;
  llmRouting = sanitizeLlmRouting(llmConnections, normalizedLlmPreferences.llm_routing);
  ocrProvider = llmRouting.ocr.engine === "tesseract" ? "tesseract" : "llm";
  ocrAutoSwitch = normalizeOcrAutoSwitch(preferences?.ocr_auto_switch);
  ocrImageDetail = normalizeOcrImageDetail(preferences?.ocr_image_detail);
}

export function resetLlmState() {
  llmConnections = [];
  llmRouting = createDefaultLlmRouting();
  ocrProvider = "llm";
  ocrAutoSwitch = false;
  ocrImageDetail = "auto";
  connectionTestStatuses.clear();
  taskTestStatuses.clear();
  taskTestsInFlight.clear();
}
