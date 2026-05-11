import {
  apiFetch,
} from "paperwise/shared";
import {
  appState,
  deleteDocumentById,
  logActivity,
  openDocumentFile,
  openDocumentView,
  waitForDocumentReady,
} from "paperwise/app";
import { splitTags } from "./ui/values.js";

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
  void options;
}

function hydrateInitialDocumentData(initialData) {
  const detail = initialData.document_detail;
  const documentId = String(detail?.document?.id || "").trim();
  if (initialData.authenticated !== true || !documentId) {
    return false;
  }
  appState.currentDocumentId = documentId;
  logActivity(`Opened document ${appState.currentDocumentId}`);
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
    if (!appState.currentDocumentId) {
      logActivity("No document selected.");
      return;
    }

    const response = await apiFetch(`/documents/${appState.currentDocumentId}/metadata`, {
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

    logActivity(`Saved metadata for ${appState.currentDocumentId}`);
    await openDocumentView(appState.currentDocumentId);
    await refreshDocumentRelatedLists({ catalog: true });
  });

  reprocessDocumentBtn?.addEventListener("click", async () => {
    if (!appState.currentDocumentId) {
      logActivity("No document selected.");
      return;
    }

    const response = await apiFetch(`/documents/${appState.currentDocumentId}/reprocess`, {
      method: "POST",
    });
    const payload = await response.json();
    if (!response.ok) {
      logActivity(`Reprocess failed: ${payload.detail || response.statusText}`);
      return;
    }

    logActivity(
      `Reprocessing queued for ${appState.currentDocumentId} (job ${payload.job_id}).`
    );
    await openDocumentView(appState.currentDocumentId);
    await refreshDocumentRelatedLists();
    const completed = await waitForDocumentReady(appState.currentDocumentId);
    if (completed) {
      logActivity(`Reprocessing completed for ${appState.currentDocumentId}.`);
      await openDocumentView(appState.currentDocumentId);
      await refreshDocumentRelatedLists({ catalog: true });
    } else {
      logActivity(`Reprocessing still running for ${appState.currentDocumentId}. Refresh to check later.`);
    }
  });

  deleteDocumentBtn?.addEventListener("click", async () => {
    if (!appState.currentDocumentId) {
      logActivity("No document selected.");
      return;
    }
    await deleteDocumentById(appState.currentDocumentId, {
      documentLabel: metaTitleInput?.value?.trim() || detailFilename?.textContent || appState.currentDocumentId,
    });
  });

  viewDocumentFileBtn?.addEventListener("click", async () => {
    if (!appState.currentDocumentId) {
      logActivity("No document selected.");
      return;
    }
    try {
      await openDocumentFile(appState.currentDocumentId);
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

export async function initializePage({ authenticated, initialData }) {
  if (authenticated !== true) {
    return;
  }
  bindSingleDocumentEvents();
  if (hydrateInitialDocumentData(initialData || {})) {
    return;
  }
  appState.currentDocumentId = new URLSearchParams(window.location.search).get("id") || "";
  if (appState.currentDocumentId) {
    await openDocumentView(appState.currentDocumentId);
  }
}
