let processedActivityRequestSeq = 0;
let initialActivityHydrated = false;

function getActivityElements() {
  return {
    processedDocsTableBody: document.getElementById("processedDocsTableBody"),
    activityTokenTotal: document.getElementById("activityTokenTotal"),
  };
}

function renderActivityTokenTotal(totalTokens) {
  const { activityTokenTotal } = getActivityElements();
  if (!activityTokenTotal) {
    return;
  }
  const value = Number.isFinite(totalTokens) && totalTokens > 0 ? Math.floor(totalTokens) : 0;
  activityTokenTotal.textContent = `LLM tokens processed: ${value.toLocaleString()}`;
}

function renderActivityTokenLoading() {
  const { activityTokenTotal } = getActivityElements();
  if (!activityTokenTotal) {
    return;
  }
  activityTokenTotal.textContent = "LLM tokens processed: loading...";
}

function applyActivityPartial(payload) {
  const { processedDocsTableBody } = getActivityElements();
  applyTableBodyPartial(processedDocsTableBody, payload);
  renderActivityTokenTotal(Number(payload.activity_total_tokens || 0));
}

async function loadProcessedDocumentsActivity() {
  const { processedDocsTableBody } = getActivityElements();
  const requestSeq = ++processedActivityRequestSeq;
  const limit = Math.max(1, normalizePageSize(docsPageSize));
  renderActivityTokenLoading();
  let payload;
  try {
    payload = await loadTablePartial({
      url: `/ui/partials/activity?limit=${encodeURIComponent(String(limit))}`,
      tbody: processedDocsTableBody,
      loadingColspan: 4,
      loadingMessage: "Loading processed documents...",
    });
  } catch (error) {
    logActivity(`Processed documents load failed: ${error.message}`);
    return;
  }
  if (requestSeq !== processedActivityRequestSeq) {
    return;
  }
  applyActivityPartial(payload);
  logActivity(`Loaded ${Number(payload.activity_document_count || 0)} latest processed document(s).`);
}

function hydrateInitialActivityData(initialData) {
  if (initialActivityHydrated) {
    return true;
  }
  if (
    initialData.authenticated !== true ||
    !Array.isArray(initialData.activity_documents)
  ) {
    return false;
  }
  renderActivityTokenTotal(Number(initialData.activity_total_tokens || 0));
  logActivity(`Loaded ${initialData.activity_documents.length} latest processed document(s).`);
  initialActivityHydrated = true;
  return true;
}

window.initializePaperwisePage = async ({ authenticated, initialData }) => {
  if (authenticated !== true) {
    return;
  }
  if (hydrateInitialActivityData(initialData || {})) {
    return;
  }
  await loadProcessedDocumentsActivity();
};
