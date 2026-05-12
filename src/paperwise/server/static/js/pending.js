import {
  apiFetch,
  applyHtmlPartialTarget,
  applyTableBodyPartial,
  fetchHtmlPartial,
  loadTablePartial,
} from "paperwise/shared";
import {
  logActivity,
} from "paperwise/app";

let pendingDocsRequestSeq = 0;
let initialPendingHydrated = false;
let pendingEventsBound = false;
let pendingPollTimer = 0;

function getPendingElements() {
  return {
    restartPendingBtn: document.getElementById("restartPendingBtn"),
    pendingTableBody: document.getElementById("pendingTableBody"),
    pendingSummaryToolbar: document.getElementById("pendingSummaryToolbar"),
    pendingProcessingSideCount: document.getElementById("pendingProcessingSideCount"),
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
  const { pendingTableBody, pendingSummaryToolbar } = getPendingElements();
  applyTableBodyPartial(pendingTableBody, payload);
  applyHtmlPartialTarget(pendingSummaryToolbar, payload);
  setPendingProcessingCount(Number(payload.dataset.processingCount || 0));
  setRestartPendingButtonEnabled(payload.dataset.hasRestartablePendingDocuments === "true");
}

function setPendingProcessingCount(count) {
  const normalizedCount = Math.max(0, Number(count || 0));
  const { pendingProcessingSideCount } = getPendingElements();
  if (pendingProcessingSideCount) {
    pendingProcessingSideCount.textContent = normalizedCount.toLocaleString();
    pendingProcessingSideCount.classList.toggle("accent", normalizedCount > 0);
  }
  syncPendingPolling(normalizedCount);
}

function syncPendingPolling(processingCount) {
  const shouldPoll = processingCount > 0 && document.getElementById("pendingTableBody");
  if (!shouldPoll) {
    if (pendingPollTimer) {
      window.clearInterval(pendingPollTimer);
      pendingPollTimer = 0;
    }
    return;
  }
  if (pendingPollTimer) {
    return;
  }
  pendingPollTimer = window.setInterval(() => {
    void loadPendingDocuments({ showLoading: false, logResult: false });
  }, 2000);
}

async function loadPendingDocuments({ showLoading = true, logResult = true } = {}) {
  const { pendingTableBody } = getPendingElements();
  const requestSeq = ++pendingDocsRequestSeq;
  let payload;
  try {
    if (showLoading) {
      payload = await loadTablePartial({
        url: "/ui/partials/pending",
        tbody: pendingTableBody,
        loadingColspan: 5,
        loadingMessage: "Loading pending documents...",
      });
    } else {
      payload = await fetchHtmlPartial("/ui/partials/pending");
    }
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
  if (logResult) {
    logActivity(`Loaded ${Number(payload.dataset.pendingCount || 0)} pending document(s)`);
  }
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
  setPendingProcessingCount(Number(initialData.documents_processing_count || 0));
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
