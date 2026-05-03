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
  await saveUserPreferences();
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
