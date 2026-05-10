const restartPendingBtn = document.getElementById("restartPendingBtn");
const pendingTableBody = document.getElementById("pendingTableBody");

let pendingDocsRequestSeq = 0;

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

function applyPendingPartial(payload) {
  const documents = Array.isArray(payload.pending_documents) ? payload.pending_documents : [];
  replaceElementHtml(pendingTableBody, payload.table_body_html);
  renderDocsProcessingCount(documents.length);
  setRestartPendingButtonEnabled(documents.some((doc) => isRestartablePendingDocument(doc)));
}

async function loadPendingDocuments() {
  const requestSeq = ++pendingDocsRequestSeq;
  renderDocsProcessingCount(0, { loading: true });
  renderTableLoading(pendingTableBody, 4, "Loading pending documents...");
  let payload;
  try {
    payload = await fetchUiPartial("/ui/partials/pending");
  } catch (error) {
    // Keep restart enabled if the UI still has visible pending rows.
    setRestartPendingButtonEnabled(getVisiblePendingRowCount() > 0);
    renderDocsProcessingCount(0, { unavailable: true });
    logActivity(`Pending list failed: ${error.message}`);
    return;
  }
  if (requestSeq !== pendingDocsRequestSeq) {
    return;
  }
  applyPendingPartial(payload);
  logActivity(`Loaded ${payload.pending_documents.length} pending document(s)`);
}

async function initializePendingView() {
  await loadPendingDocuments();
}

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
});
