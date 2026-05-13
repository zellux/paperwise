import {
  apiFetch,
} from "paperwise/shared";
import {
  appState,
  applyTheme,
  formatApiErrorDetail,
  hydrateSettingsFormFromInitialPreferences,
  logActivity,
  normalizeThemeName,
  refreshUploadAvailability,
  saveUserPreferences,
} from "paperwise/app";
import {
  LLM_TASK_LABELS,
  createEmptyConnection,
  getConnectionApiKeyPlaceholder,
  getConnectionBaseUrlHelpText,
  getConnectionById,
  getConnectionValidationError,
  getLlmProviderDefaults,
  getOcrLlmProviderDefaults,
  getResolvedTaskSettings,
  normalizeConnection,
  normalizeLlmProvider,
  normalizeOcrProvider,
  providerShowsBaseUrlField,
  providerUsesManagedBaseUrl,
  sanitizeLlmRouting,
} from "./state/llm.js";
import {
  normalizeGroundedQaMaxDocuments,
  normalizeGroundedQaTopK,
  normalizeOcrImageDetail,
  normalizePageSize,
} from "./state/preferences.js";
import { escapeHtml } from "./ui/escape.js";

let settingsForm = null;
let settingsFormActions = null;
let settingsThemeSelect = null;
let settingsPageSizeSelect = null;
let settingsGroundedQaTopKInput = null;
let settingsGroundedQaMaxDocsInput = null;
let settingsConnectionsList = null;
let settingsAddConnectionBtn = null;
let settingsModelSummary = null;
let settingsMetadataRouteFields = null;
let settingsMetadataConnectionSelect = null;
let settingsMetadataModelInput = null;
let settingsGroundedQaRouteFields = null;
let settingsGroundedQaConnectionSelect = null;
let settingsGroundedQaModelInput = null;
let settingsOcrProviderSelect = null;
let settingsOcrStatus = null;
let settingsOcrRouteFields = [];
let settingsOcrConnectionSelect = null;
let settingsOcrModelInput = null;
let settingsOcrAutoSwitchCheckbox = null;
let settingsOcrImageDetailSelect = null;
let settingsCurrentPasswordInput = null;
let settingsNewPasswordInput = null;
let settingsConfirmPasswordInput = null;
let settingsChangePasswordBtn = null;
let settingsPasswordStatus = null;
let settingsEventsBound = false;

export const requiresServerSessionRender = true;

function syncThemeChoiceCards() {
  const selectedTheme = normalizeThemeName(settingsThemeSelect?.value || appState.currentTheme);
  document.querySelectorAll("[data-theme-choice]").forEach((buttonEl) => {
    const theme = normalizeThemeName(buttonEl.getAttribute("data-theme-choice") || "");
    const active = theme === selectedTheme;
    buttonEl.classList.toggle("active", active);
    buttonEl.setAttribute("aria-pressed", active ? "true" : "false");
  });
}

function bindSettingsElements() {
  settingsForm = document.getElementById("settingsForm");
  settingsFormActions = document.querySelector(".settings-form-actions");
  settingsThemeSelect = document.getElementById("settingsThemeSelect");
  settingsPageSizeSelect = document.getElementById("settingsPageSizeSelect");
  settingsGroundedQaTopKInput = document.getElementById("settingsGroundedQaTopKInput");
  settingsGroundedQaMaxDocsInput = document.getElementById("settingsGroundedQaMaxDocsInput");
  settingsConnectionsList = document.getElementById("settingsConnectionsList");
  settingsAddConnectionBtn = document.getElementById("settingsAddConnectionBtn");
  settingsModelSummary = document.getElementById("settingsModelSummary");
  settingsMetadataRouteFields = document.getElementById("settingsMetadataRouteFields");
  settingsMetadataConnectionSelect = document.getElementById("settingsMetadataConnectionSelect");
  settingsMetadataModelInput = document.getElementById("settingsMetadataModelInput");
  settingsGroundedQaRouteFields = document.getElementById("settingsGroundedQaRouteFields");
  settingsGroundedQaConnectionSelect = document.getElementById("settingsGroundedQaConnectionSelect");
  settingsGroundedQaModelInput = document.getElementById("settingsGroundedQaModelInput");
  settingsOcrProviderSelect = document.getElementById("settingsOcrProviderSelect");
  settingsOcrStatus = document.getElementById("settingsOcrStatus");
  settingsOcrRouteFields = Array.from(document.querySelectorAll("[data-ocr-route-field]"));
  settingsOcrConnectionSelect = document.getElementById("settingsOcrConnectionSelect");
  settingsOcrModelInput = document.getElementById("settingsOcrModelInput");
  settingsOcrAutoSwitchCheckbox = document.getElementById("settingsOcrAutoSwitchCheckbox");
  settingsOcrImageDetailSelect = document.getElementById("settingsOcrImageDetailSelect");
  settingsCurrentPasswordInput = document.getElementById("settingsCurrentPasswordInput");
  settingsNewPasswordInput = document.getElementById("settingsNewPasswordInput");
  settingsConfirmPasswordInput = document.getElementById("settingsConfirmPasswordInput");
  settingsChangePasswordBtn = document.getElementById("settingsChangePasswordBtn");
  settingsPasswordStatus = document.getElementById("settingsPasswordStatus");
}

function markSettingsDirty() {
  settingsFormActions?.classList.remove("view-hidden");
}

export function renderSettingsForm() {
  if (settingsThemeSelect && settingsThemeSelect.value !== appState.currentTheme) {
    settingsThemeSelect.value = appState.currentTheme;
  }
  syncThemeChoiceCards();
  if (settingsPageSizeSelect && settingsPageSizeSelect.value !== String(appState.docsPageSize)) {
    settingsPageSizeSelect.value = String(appState.docsPageSize);
  }
  if (settingsGroundedQaTopKInput && settingsGroundedQaTopKInput.value !== String(appState.groundedQaTopK)) {
    settingsGroundedQaTopKInput.value = String(appState.groundedQaTopK);
  }
  if (
    settingsGroundedQaMaxDocsInput &&
    settingsGroundedQaMaxDocsInput.value !== String(appState.groundedQaMaxDocuments)
  ) {
    settingsGroundedQaMaxDocsInput.value = String(appState.groundedQaMaxDocuments);
  }
  if (settingsOcrProviderSelect && settingsOcrProviderSelect.value !== appState.ocrProvider) {
    settingsOcrProviderSelect.value = appState.ocrProvider;
  }
  if (settingsOcrAutoSwitchCheckbox) {
    settingsOcrAutoSwitchCheckbox.checked = appState.ocrAutoSwitch;
  }
  if (settingsOcrImageDetailSelect && settingsOcrImageDetailSelect.value !== appState.ocrImageDetail) {
    settingsOcrImageDetailSelect.value = appState.ocrImageDetail;
  }
  renderConnectionsList();
  renderTaskRoutingControls();
  renderModelConfigSummary();
  syncTaskRoutingVisibility();
  bindModelConfigSummaryActions();
  refreshLocalOcrStatus().catch(() => {});
  setSettingsPasswordStatus("");
  refreshUploadAvailability();
}

function updateModelSummaryTestCell(rowEl, task) {
  const status = appState.taskTestStatuses.get(task) || { message: "", tone: "" };
  const isTesting = appState.taskTestsInFlight.has(task);
  const buttonEl = rowEl.querySelector("[data-task-test]");
  if (buttonEl) {
    buttonEl.disabled = isTesting;
    buttonEl.textContent = isTesting ? "Testing..." : "Test";
  }
  const statusEl = rowEl.querySelector("[data-summary-status]");
  if (statusEl) {
    statusEl.textContent = status.message || "";
    statusEl.classList.remove("is-success", "is-error");
    if (status.tone === "success") {
      statusEl.classList.add("is-success");
    } else if (status.tone === "error") {
      statusEl.classList.add("is-error");
    }
  }
}

function renderModelConfigSummary() {
  if (!settingsModelSummary) {
    return;
  }
  settingsModelSummary.querySelectorAll("[data-summary-task]").forEach((rowEl) => {
    const task = rowEl.getAttribute("data-summary-task") || "";
    let settings = getResolvedTaskSettings(task);
    let connectionText = "-";
    let configurationText = "Not configured";
    if (task === "ocr" && appState.ocrProvider === "tesseract") {
      settings = null;
      connectionText = "Local";
      configurationText = "local only";
    } else if (settings) {
      connectionText = settings.connection_name;
      configurationText = settings.model;
      if (task === "ocr") {
        configurationText += `, auto switch ${appState.ocrAutoSwitch ? "on" : "off"}`;
      }
    }
    const connectionEl = rowEl.querySelector("[data-summary-connection]");
    if (connectionEl) {
      connectionEl.textContent = connectionText;
    }
    const configurationEl = rowEl.querySelector("[data-summary-configuration]");
    if (configurationEl) {
      configurationEl.textContent = configurationText;
    }
    updateModelSummaryTestCell(rowEl, task);
  });
}

function bindModelConfigSummaryActions() {
  if (!settingsModelSummary || settingsModelSummary.dataset.actionsBound === "true") {
    return;
  }
  settingsModelSummary.dataset.actionsBound = "true";
  settingsModelSummary.querySelectorAll("[data-task-test]").forEach((buttonEl) => {
    buttonEl.addEventListener("click", async () => {
      const task = buttonEl.getAttribute("data-task-test") || "";
      await testTaskConfig(task, buttonEl);
    });
  });
}

async function testAllTaskConfigs(buttonEl) {
  const tasks = ["metadata", "grounded_qa", "ocr"];
  const labelEl = buttonEl?.querySelector("[data-task-test-all-label]");
  const previousLabel = labelEl?.textContent || "Re-test all";
  if (buttonEl) {
    buttonEl.disabled = true;
  }
  if (labelEl) {
    labelEl.textContent = "Testing...";
  }
  try {
    await Promise.all(tasks.map((task) => {
      const taskButton = settingsModelSummary?.querySelector(`[data-task-test="${task}"]`);
      return testTaskConfig(task, taskButton instanceof HTMLButtonElement ? taskButton : null);
    }));
  } finally {
    if (buttonEl) {
      buttonEl.disabled = false;
    }
    if (labelEl) {
      labelEl.textContent = previousLabel;
    }
  }
}

function setConnectionTestStatus(connectionId, message, tone = "") {
  appState.connectionTestStatuses.set(connectionId, { message, tone });
  renderConnectionsList();
}

function setTaskTestStatus(task, message, tone = "") {
  appState.taskTestStatuses.set(task, { message, tone });
  renderModelConfigSummary();
}

function renderConnectionSelect(selectEl, selectedValue) {
  if (!selectEl) {
    return;
  }
  const options = ["<option value=\"\">Select connection</option>"];
  for (const connection of appState.llmConnections) {
    options.push(
      `<option value="${escapeHtml(connection.id)}"${connection.id === selectedValue ? " selected" : ""}>${escapeHtml(connection.name)}</option>`
    );
  }
  selectEl.innerHTML = options.join("");
}

function syncTaskRoutingVisibility() {
  const ocrLlmMode = normalizeOcrProvider(settingsOcrProviderSelect?.value || appState.ocrProvider) === "llm";
  settingsOcrRouteFields.forEach((fieldEl) => {
    fieldEl.hidden = !ocrLlmMode;
  });
}

function renderTaskRoutingControls() {
  renderConnectionSelect(settingsMetadataConnectionSelect, appState.llmRouting.metadata.connection_id);
  if (settingsMetadataModelInput && settingsMetadataModelInput.value !== appState.llmRouting.metadata.model) {
    settingsMetadataModelInput.value = appState.llmRouting.metadata.model;
  }

  renderConnectionSelect(settingsGroundedQaConnectionSelect, appState.llmRouting.grounded_qa.connection_id);
  if (settingsGroundedQaModelInput && settingsGroundedQaModelInput.value !== appState.llmRouting.grounded_qa.model) {
    settingsGroundedQaModelInput.value = appState.llmRouting.grounded_qa.model;
  }

  renderConnectionSelect(settingsOcrConnectionSelect, appState.llmRouting.ocr.connection_id);
  if (settingsOcrModelInput && settingsOcrModelInput.value !== appState.llmRouting.ocr.model) {
    settingsOcrModelInput.value = appState.llmRouting.ocr.model;
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

async function testLocalOcrTask(buttonEl) {
  const previousText = buttonEl?.textContent;
  appState.taskTestsInFlight.add("ocr");
  if (buttonEl) {
    buttonEl.disabled = true;
    buttonEl.textContent = "Testing...";
  }
  setTaskTestStatus("ocr", "Testing local OCR tools...", "");
  try {
    const response = await apiFetch("/documents/ocr/local-status");
    const payload = await response.json().catch(() => ({}));
    if (!response.ok || !payload.available) {
      const errorMessage = payload.detail || response.statusText || "Local OCR tools are not available.";
      setTaskTestStatus("ocr", errorMessage, "error");
      logActivity(`OCR config test failed: ${errorMessage}`);
      return;
    }
    setTaskTestStatus("ocr", payload.detail || "Local OCR tools available.", "success");
    logActivity("OCR config test passed for Local Tesseract.");
  } catch (error) {
    setTaskTestStatus("ocr", error.message || "Failed to test local OCR tools.", "error");
    logActivity(`OCR config test failed: ${error.message}`);
  } finally {
    appState.taskTestsInFlight.delete("ocr");
    renderModelConfigSummary();
    if (buttonEl) {
      buttonEl.disabled = false;
      buttonEl.textContent = previousText || "Test";
    }
  }
}

async function testTaskConfig(task, buttonEl) {
  if (!["metadata", "grounded_qa", "ocr"].includes(task)) {
    return;
  }
  if (task === "ocr" && normalizeOcrProvider(settingsOcrProviderSelect?.value || appState.ocrProvider) === "tesseract") {
    await testLocalOcrTask(buttonEl);
    return;
  }
  const taskSettings = getResolvedTaskSettings(task);
  const taskLabel = LLM_TASK_LABELS[task] || "Model config";
  if (!taskSettings) {
    const reason = `${taskLabel} is not configured.`;
    setTaskTestStatus(task, reason, "error");
    logActivity(`${taskLabel} config test blocked: ${reason}`);
    return;
  }
  const reason = getConnectionValidationError(taskSettings);
  if (reason) {
    setTaskTestStatus(task, reason, "error");
    logActivity(`${taskLabel} config test blocked: ${reason}`);
    return;
  }

  const previousText = buttonEl?.textContent;
  appState.taskTestsInFlight.add(task);
  if (buttonEl) {
    buttonEl.disabled = true;
    buttonEl.textContent = "Testing...";
  }
  setTaskTestStatus(task, "Testing...", "");
  try {
    const response = await apiFetch("/documents/llm/test", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        task,
        connection_name: taskSettings.connection_name,
        provider: taskSettings.provider,
        model: taskSettings.model,
        base_url: taskSettings.base_url,
        api_key: taskSettings.api_key,
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
      setTaskTestStatus(task, errorMessage, "error");
      logActivity(`${taskLabel} config test failed: ${errorMessage}`);
      return;
    }
    setTaskTestStatus(task, `Success (${payload.provider} / ${payload.model}).`, "success");
    logActivity(`${taskLabel} config test passed (${payload.provider} / ${payload.model}).`);
  } catch (error) {
    setTaskTestStatus(task, error.message, "error");
    logActivity(`${taskLabel} config test failed: ${error.message}`);
  } finally {
    appState.taskTestsInFlight.delete(task);
    renderModelConfigSummary();
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
  if (!appState.llmConnections.length) {
    settingsConnectionsList.innerHTML = "<p class=\"settings-empty-note\">No model connections yet. Add one to configure LLM-backed tasks.</p>";
    return;
  }
  settingsConnectionsList.innerHTML = appState.llmConnections
    .map((connection, index) => {
      const status = appState.connectionTestStatuses.get(connection.id) || { message: "", tone: "" };
      const showBaseUrlField = providerShowsBaseUrlField(connection.provider);
      const baseUrlHelpText = getConnectionBaseUrlHelpText(connection.provider);
      const apiKeyPlaceholder = getConnectionApiKeyPlaceholder(connection.provider);
      const defaultBaseUrl = getLlmProviderDefaults(connection.provider)?.base_url
        || getOcrLlmProviderDefaults(connection.provider)?.base_url
        || "";
      const providerLabel = {
        custom: "Custom (OpenAI-Compatible)",
        openai: "OpenAI",
        gemini: "Gemini",
      }[connection.provider] || (connection.provider ? connection.provider : "No provider selected");
      const providerInitial = (connection.name || connection.provider || "LL").slice(0, 2);
      const providerKindClass = String(connection.name || "").toLowerCase().includes("lm studio")
        ? " kind-lm"
        : String(connection.name || "").toLowerCase().includes("anthropic")
          ? " kind-anthropic"
          : "";
      const validationError = getConnectionValidationError(connection);
      const statusLabel = status.tone === "error" ? "Error" : validationError ? "Untested" : "Connected";
      const statusClass = status.tone === "error" ? "err" : validationError ? "warn" : "";
      return `
        <section class="settings-connection-card" data-connection-id="${escapeHtml(connection.id)}">
          <div class="settings-connection-header">
            <div class="settings-connection-title">
              <span class="settings-connection-logo${providerKindClass}" aria-hidden="true">${escapeHtml(providerInitial)}</span>
              <div class="settings-connection-name-stack">
                <h4 class="settings-connection-name">${escapeHtml(connection.name || `Connection ${index + 1}`)}</h4>
                <span class="settings-connection-provider">${escapeHtml(providerLabel)}</span>
              </div>
              <span class="settings-status-pill ${statusClass}"><span class="settings-status-dot" aria-hidden="true"></span>${escapeHtml(statusLabel)}</span>
            </div>
            <div class="settings-connection-actions">
              <button type="button" class="btn btn-sm settings-test-connection-btn" data-connection-test="${escapeHtml(connection.id)}">Test</button>
              <button type="button" class="btn btn-ghost btn-icon-xs settings-connection-more-btn" aria-label="Connection settings">
                <svg class="icon-sm" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1-2.83 2.83l-.06-.06A1.65 1.65 0 0 0 15 21.4V22a2 2 0 0 1-6 0v-.6a1.65 1.65 0 0 0-1.82-.33l-.06.06a2 2 0 1 1-2.83-2.83l.06-.06A1.65 1.65 0 0 0 2.6 15H2a2 2 0 0 1 0-6h.6a1.65 1.65 0 0 0 .33-1.82l-.06-.06a2 2 0 1 1 2.83-2.83l.06.06A1.65 1.65 0 0 0 9 2.6V2a2 2 0 0 1 6 0v.6a1.65 1.65 0 0 0 1.82.33l.06-.06a2 2 0 1 1 2.83 2.83l-.06.06A1.65 1.65 0 0 0 21.4 9h.6a2 2 0 0 1 0 6h-.6a1.65 1.65 0 0 0-2 0z"/></svg>
              </button>
              <button type="button" class="btn btn-danger-ghost btn-sm settings-remove-connection-btn" data-connection-remove="${escapeHtml(connection.id)}">Remove</button>
            </div>
          </div>
          <div class="settings-connection-body">
            <div class="settings-form-grid">
              <div class="settings-field">
                <label class="settings-field-label" for="settingsConnectionName-${escapeHtml(connection.id)}">Name</label>
                <input id="settingsConnectionName-${escapeHtml(connection.id)}" data-connection-field="name" data-connection-id="${escapeHtml(connection.id)}" type="text" value="${escapeHtml(connection.name)}" placeholder="e.g. OpenAI main" />
              </div>
              <div class="settings-field">
                <label class="settings-field-label" for="settingsConnectionProvider-${escapeHtml(connection.id)}">Provider</label>
                <select id="settingsConnectionProvider-${escapeHtml(connection.id)}" data-connection-field="provider" data-connection-id="${escapeHtml(connection.id)}">
                  <option value="">Select provider</option>
                  <option value="openai"${connection.provider === "openai" ? " selected" : ""}>OpenAI</option>
                  <option value="gemini"${connection.provider === "gemini" ? " selected" : ""}>Gemini</option>
                  <option value="custom"${connection.provider === "custom" ? " selected" : ""}>Custom (OpenAI-Compatible)</option>
                </select>
              </div>
            ${showBaseUrlField
              ? `
              <div class="settings-field">
                <label class="settings-field-label" for="settingsConnectionBaseUrl-${escapeHtml(connection.id)}">Base URL</label>
                <div class="settings-input-adorned">
                  <span class="settings-input-prefix" aria-hidden="true">
                    <svg class="icon-sm" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><line x1="2" y1="12" x2="22" y2="12"/><path d="M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z"/></svg>
                  </span>
                  <input id="settingsConnectionBaseUrl-${escapeHtml(connection.id)}" class="settings-input-with-prefix" data-connection-field="base_url" data-connection-id="${escapeHtml(connection.id)}" type="text" value="${escapeHtml(connection.base_url)}" placeholder="https://api.openai.com/v1" />
                </div>
              </div>
            `
              : `
              <div class="settings-field">
                <span class="settings-field-label">Base URL</span>
                <div class="settings-field-hint">${escapeHtml(baseUrlHelpText || defaultBaseUrl || "Managed by provider")}</div>
              </div>
            `}
              <div class="settings-field">
                <label class="settings-field-label" for="settingsConnectionApiKey-${escapeHtml(connection.id)}">API Key</label>
                <div class="settings-input-adorned">
                  <input id="settingsConnectionApiKey-${escapeHtml(connection.id)}" class="settings-input-with-suffix" data-connection-field="api_key" data-connection-id="${escapeHtml(connection.id)}" type="password" value="${escapeHtml(connection.api_key)}" placeholder="${escapeHtml(apiKeyPlaceholder)}" />
                  <span class="settings-input-suffix" aria-hidden="true">
                    <svg class="icon-sm" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/><circle cx="12" cy="12" r="3"/></svg>
                    <svg class="icon-sm" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="9" y="9" width="13" height="13" rx="2"/><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/></svg>
                  </span>
                </div>
              </div>
              <div class="settings-field settings-field-full">
                <label class="settings-field-label" for="settingsConnectionDefaultModel-${escapeHtml(connection.id)}">Default model</label>
                <input id="settingsConnectionDefaultModel-${escapeHtml(connection.id)}" data-connection-field="default_model" data-connection-id="${escapeHtml(connection.id)}" type="text" value="${escapeHtml(connection.default_model || "")}" placeholder="e.g. gpt-4.1-mini" />
                <span class="settings-field-hint">Used as a fallback when a task doesn't specify an override.</span>
              </div>
            </div>
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
      appState.llmConnections = appState.llmConnections.filter((connection) => connection.id !== connectionId);
      appState.connectionTestStatuses.delete(connectionId);
      appState.llmRouting = sanitizeLlmRouting(appState.llmConnections, appState.llmRouting);
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
  const selectedProvider = normalizeOcrProvider(settingsOcrProviderSelect?.value || appState.ocrProvider);
  if (selectedProvider !== "tesseract") {
    setSettingsOcrStatus("");
    return;
  }

  const requestId = ++appState.ocrStatusRequestSeq;
  setSettingsOcrStatus("Checking local OCR tools...");
  try {
    const response = await apiFetch("/documents/ocr/local-status");
    const payload = await response.json();
    if (requestId !== appState.ocrStatusRequestSeq) {
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
    if (requestId !== appState.ocrStatusRequestSeq) {
      return;
    }
    setSettingsOcrStatus(error.message || "Failed to check local OCR tools.", "error");
  }
}

function bindSettingsEvents() {
  if (settingsEventsBound) {
    return;
  }

  settingsForm?.addEventListener("submit", async (event) => {
    event.preventDefault();
    const nextTheme = normalizeThemeName(settingsThemeSelect?.value || appState.currentTheme);
    const nextPageSize = normalizePageSize(settingsPageSizeSelect?.value || appState.docsPageSize);
    appState.groundedQaTopK = normalizeGroundedQaTopK(settingsGroundedQaTopKInput?.value || appState.groundedQaTopK);
    appState.groundedQaMaxDocuments = normalizeGroundedQaMaxDocuments(
      settingsGroundedQaMaxDocsInput?.value || appState.groundedQaMaxDocuments
    );
    appState.llmConnections = appState.llmConnections
      .map((connection, index) => normalizeConnection(connection, index))
      .filter(Boolean);
    appState.llmRouting = sanitizeLlmRouting(appState.llmConnections, {
      metadata: {
        connection_id: String(settingsMetadataConnectionSelect?.value || "").trim(),
        model: String(settingsMetadataModelInput?.value || "").trim(),
      },
      grounded_qa: {
        connection_id: String(settingsGroundedQaConnectionSelect?.value || "").trim(),
        model: String(settingsGroundedQaModelInput?.value || "").trim(),
      },
      ocr: {
        engine: normalizeOcrProvider(settingsOcrProviderSelect?.value || appState.ocrProvider),
        connection_id: String(settingsOcrConnectionSelect?.value || "").trim(),
        model: String(settingsOcrModelInput?.value || "").trim(),
      },
    });
    appState.ocrProvider = normalizeOcrProvider(settingsOcrProviderSelect?.value || appState.ocrProvider);
    appState.ocrAutoSwitch = Boolean(settingsOcrAutoSwitchCheckbox?.checked);
    appState.ocrImageDetail = normalizeOcrImageDetail(settingsOcrImageDetailSelect?.value || appState.ocrImageDetail);
    renderTaskRoutingControls();
    syncTaskRoutingVisibility();
    refreshUploadAvailability();
    applyTheme(nextTheme);
    appState.docsPageSize = nextPageSize;
    await saveUserPreferences();
    logActivity("Saved settings.");
    window.location.reload();
  });

  settingsForm?.addEventListener("input", (event) => {
    if (event.target instanceof HTMLElement && event.target.closest("[data-skip-dirty]")) {
      return;
    }
    markSettingsDirty();
  });

  settingsForm?.addEventListener("change", (event) => {
    if (event.target instanceof HTMLElement && event.target.closest("[data-skip-dirty]")) {
      return;
    }
    markSettingsDirty();
  });

  document.querySelectorAll("[data-theme-choice]").forEach((buttonEl) => {
    buttonEl.addEventListener("click", () => {
      const nextTheme = normalizeThemeName(buttonEl.getAttribute("data-theme-choice") || appState.currentTheme);
      if (settingsThemeSelect) {
        settingsThemeSelect.value = nextTheme;
      }
      syncThemeChoiceCards();
      applyTheme(nextTheme);
      markSettingsDirty();
    });
  });

  settingsOcrProviderSelect?.addEventListener("change", () => {
    appState.ocrProvider = normalizeOcrProvider(settingsOcrProviderSelect.value);
    appState.llmRouting.ocr.engine = appState.ocrProvider;
    syncTaskRoutingVisibility();
    refreshLocalOcrStatus().catch(() => {});
    markSettingsDirty();
  });

  settingsAddConnectionBtn?.addEventListener("click", () => {
    appState.llmConnections.push(createEmptyConnection());
    appState.llmRouting = sanitizeLlmRouting(appState.llmConnections, appState.llmRouting);
    renderSettingsForm();
    markSettingsDirty();
  });

  document.querySelector("[data-task-test-all]")?.addEventListener("click", async (event) => {
    const buttonEl = event.currentTarget;
    if (!(buttonEl instanceof HTMLButtonElement)) {
      return;
    }
    await testAllTaskConfigs(buttonEl);
  });

  settingsMetadataConnectionSelect?.addEventListener("change", () => {
    appState.llmRouting.metadata.connection_id = String(settingsMetadataConnectionSelect.value || "").trim();
  });

  settingsMetadataModelInput?.addEventListener("input", () => {
    appState.llmRouting.metadata.model = String(settingsMetadataModelInput.value || "").trim();
  });

  settingsGroundedQaConnectionSelect?.addEventListener("change", () => {
    appState.llmRouting.grounded_qa.connection_id = String(settingsGroundedQaConnectionSelect.value || "").trim();
  });

  settingsGroundedQaModelInput?.addEventListener("input", () => {
    appState.llmRouting.grounded_qa.model = String(settingsGroundedQaModelInput.value || "").trim();
  });

  settingsOcrConnectionSelect?.addEventListener("change", () => {
    appState.llmRouting.ocr.connection_id = String(settingsOcrConnectionSelect.value || "").trim();
  });

  settingsOcrModelInput?.addEventListener("input", () => {
    appState.llmRouting.ocr.model = String(settingsOcrModelInput.value || "").trim();
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

  settingsEventsBound = true;
}

export async function initializePage({ authenticated }) {
  if (authenticated !== true) {
    return;
  }
  bindSettingsElements();
  bindSettingsEvents();
  if (!hydrateSettingsFormFromInitialPreferences()) {
    renderSettingsForm();
  }
}
