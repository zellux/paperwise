import {
  apiFetch,
  applyTableBodyPartial,
  loadTablePartial,
} from "paperwise/shared";
import {
  logActivity,
} from "paperwise/app";

let pendingDocsRequestSeq = 0;
let initialPendingHydrated = false;
let pendingEventsBound = false;

function getPendingElements() {
  return {
    restartPendingBtn: document.getElementById("restartPendingBtn"),
    pendingTableBody: document.getElementById("pendingTableBody"),
  };
}

function setRestartPendingButtonEnabled(enabled) {
  const { restartPendingBtn } = getPendingElements();
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
  const { pendingTableBody } = getPendingElements();
  if (!pendingTableBody) {
    return 0;
  }
  return pendingTableBody.querySelectorAll("tr[data-pending-doc-id]").length;
}

function applyPendingPartial(payload) {
  const { pendingTableBody } = getPendingElements();
  applyTableBodyPartial(pendingTableBody, payload);
  setRestartPendingButtonEnabled(payload.dataset.hasRestartablePendingDocuments === "true");
}

async function loadPendingDocuments() {
  const { pendingTableBody } = getPendingElements();
  const requestSeq = ++pendingDocsRequestSeq;
  let payload;
  try {
    payload = await loadTablePartial({
      url: "/ui/partials/pending",
      tbody: pendingTableBody,
      loadingColspan: 4,
      loadingMessage: "Loading pending documents...",
    });
  } catch (error) {
    // Keep restart enabled if the UI still has visible pending rows.
    setRestartPendingButtonEnabled(getVisiblePendingRowCount() > 0);
    logActivity(`Pending list failed: ${error.message}`);
    return;
  }
  if (requestSeq !== pendingDocsRequestSeq) {
    return;
  }
  applyPendingPartial(payload);
  logActivity(`Loaded ${Number(payload.dataset.pendingCount || 0)} pending document(s)`);
}

function hydrateInitialPendingData(initialData) {
  if (initialPendingHydrated) {
    return true;
  }
  if (
    initialData.authenticated !== true ||
    !Array.isArray(initialData.pending_documents)
  ) {
    return false;
  }
  setRestartPendingButtonEnabled(
    initialData.pending_documents.some((doc) => isRestartablePendingDocument(doc))
  );
  logActivity(`Loaded ${initialData.pending_documents.length} pending document(s)`);
  initialPendingHydrated = true;
  return true;
}

function bindPendingEvents() {
  if (pendingEventsBound) {
    return;
  }
  const { restartPendingBtn } = getPendingElements();
  if (!restartPendingBtn) {
    return;
  }
  restartPendingBtn.addEventListener("click", async () => {
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
  });
  pendingEventsBound = true;
}

export async function initializePage({ authenticated, initialData }) {
  if (authenticated !== true) {
    return;
  }
  bindPendingEvents();
  if (hydrateInitialPendingData(initialData || {})) {
    return;
  }
  await loadPendingDocuments();
}
