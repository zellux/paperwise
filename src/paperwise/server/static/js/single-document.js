let singleDocumentEventsBound = false;

function getSingleDocumentElements() {
  return {
    documentMetaForm: document.getElementById("documentMetaForm"),
    backToDocsBtn: document.getElementById("backToDocsBtn"),
    reprocessDocumentBtn: document.getElementById("reprocessDocumentBtn"),
    deleteDocumentBtn: document.getElementById("deleteDocumentBtn"),
    viewDocumentFileBtn: document.getElementById("viewDocumentFileBtn"),
    metaTitleInput: document.getElementById("metaTitle"),
    metaDateInput: document.getElementById("metaDate"),
    metaCorrespondentInput: document.getElementById("metaCorrespondent"),
    metaTypeInput: document.getElementById("metaType"),
    metaTagsInput: document.getElementById("metaTags"),
    detailFilename: document.getElementById("detailFilename"),
  };
}

async function refreshDocumentRelatedLists(options = {}) {
  await loadDocumentsList();
  if (typeof loadPendingDocuments === "function") {
    await loadPendingDocuments();
  }
  if (options.catalog === true && typeof loadTagStats === "function") {
    await loadTagStats();
  }
  if (options.catalog === true && typeof loadDocumentTypeStats === "function") {
    await loadDocumentTypeStats();
  }
}

function hydrateInitialDocumentData(initialData) {
  const detail = initialData.document_detail;
  const documentId = String(detail?.document?.id || "").trim();
  if (initialData.authenticated !== true || !documentId) {
    return false;
  }
  currentDocumentId = documentId;
  logActivity(`Opened document ${currentDocumentId}`);
  return true;
}

function bindSingleDocumentEvents() {
  if (singleDocumentEventsBound) {
    return;
  }
  const {
    documentMetaForm,
    backToDocsBtn,
    reprocessDocumentBtn,
    deleteDocumentBtn,
    viewDocumentFileBtn,
    metaTitleInput,
    metaDateInput,
    metaCorrespondentInput,
    metaTypeInput,
    metaTagsInput,
    detailFilename,
  } = getSingleDocumentElements();

  documentMetaForm?.addEventListener("submit", async (event) => {
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
    await refreshDocumentRelatedLists({ catalog: true });
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
    await refreshDocumentRelatedLists();
    const completed = await waitForDocumentReady(currentDocumentId);
    if (completed) {
      logActivity(`Reprocessing completed for ${currentDocumentId}.`);
      await openDocumentView(currentDocumentId);
      await refreshDocumentRelatedLists({ catalog: true });
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

  backToDocsBtn?.addEventListener("click", () => {
    const url = new URL("/ui/documents", window.location.origin);
    window.location.href = url.pathname;
  });

  singleDocumentEventsBound = true;
}

window.initializePaperwisePage = async ({ authenticated, initialData }) => {
  if (authenticated !== true) {
    return;
  }
  bindSingleDocumentEvents();
  if (hydrateInitialDocumentData(initialData || {})) {
    return;
  }
  currentDocumentId = new URLSearchParams(window.location.search).get("id") || "";
  if (currentDocumentId) {
    await openDocumentView(currentDocumentId);
  }
};
