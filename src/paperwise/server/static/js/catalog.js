const tagsTableBody = document.getElementById("tagsTableBody");
const documentTypesTableBody = document.getElementById("documentTypesTableBody");

let tagStatsSort = { field: "", direction: "" };
let documentTypesSort = { field: "", direction: "" };
let tagStatsRequestSeq = 0;
let documentTypeStatsRequestSeq = 0;
let initialTagStatsHydrated = false;
let initialDocumentTypesHydrated = false;

function clearCatalogStateForSession() {
  tagStatsSort = { field: "", direction: "" };
  documentTypesSort = { field: "", direction: "" };
}

function applyTagsPartial(payload) {
  replaceElementHtml(tagsTableBody, payload.table_body_html);
  renderSortHeaders();
}

function applyDocumentTypesPartial(payload) {
  replaceElementHtml(documentTypesTableBody, payload.table_body_html);
  renderSortHeaders();
}

async function loadTagStats() {
  const requestSeq = ++tagStatsRequestSeq;
  renderTableLoading(tagsTableBody, 3, "Loading tags...");
  renderSortHeaders();
  const query = new URLSearchParams();
  if (tagStatsSort.field && tagStatsSort.direction) {
    query.set("sort_by", tagStatsSort.field);
    query.set("sort_dir", tagStatsSort.direction);
  }
  const suffix = query.toString() ? `?${query.toString()}` : "";
  let payload;
  try {
    payload = await fetchUiPartial(`/ui/partials/tags${suffix}`);
  } catch (error) {
    logActivity(`Tag stats load failed: ${error.message}`);
    return;
  }
  if (requestSeq !== tagStatsRequestSeq) {
    return;
  }
  applyTagsPartial(payload);
  logActivity(`Loaded ${payload.tag_stats.length} tag(s)`);
}

async function loadDocumentTypeStats() {
  const requestSeq = ++documentTypeStatsRequestSeq;
  renderTableLoading(documentTypesTableBody, 3, "Loading document types...");
  renderSortHeaders();
  const query = new URLSearchParams();
  if (documentTypesSort.field && documentTypesSort.direction) {
    query.set("sort_by", documentTypesSort.field);
    query.set("sort_dir", documentTypesSort.direction);
  }
  const suffix = query.toString() ? `?${query.toString()}` : "";
  let payload;
  try {
    payload = await fetchUiPartial(`/ui/partials/document-types${suffix}`);
  } catch (error) {
    logActivity(`Document type stats load failed: ${error.message}`);
    return;
  }
  if (requestSeq !== documentTypeStatsRequestSeq) {
    return;
  }
  applyDocumentTypesPartial(payload);
  logActivity(`Loaded ${payload.document_type_stats.length} document type(s)`);
}

function hydrateInitialTagStats(initialData) {
  if (initialTagStatsHydrated) {
    return true;
  }
  if (
    initialData.authenticated !== true ||
    !Array.isArray(initialData.tag_stats)
  ) {
    return false;
  }
  renderSortHeaders();
  logActivity(`Loaded ${initialData.tag_stats.length} tag(s)`);
  initialTagStatsHydrated = true;
  return true;
}

function hydrateInitialDocumentTypes(initialData) {
  if (initialDocumentTypesHydrated) {
    return true;
  }
  if (
    initialData.authenticated !== true ||
    !Array.isArray(initialData.document_type_stats)
  ) {
    return false;
  }
  renderSortHeaders();
  logActivity(`Loaded ${initialData.document_type_stats.length} document type(s)`);
  initialDocumentTypesHydrated = true;
  return true;
}

window.initializePaperwisePage = async ({ authenticated, initialData }) => {
  if (authenticated !== true) {
    return;
  }
  if (tagsTableBody) {
    if (!hydrateInitialTagStats(initialData || {})) {
      await loadTagStats();
    }
    return;
  }
  if (documentTypesTableBody && !hydrateInitialDocumentTypes(initialData || {})) {
    await loadDocumentTypeStats();
  }
};

for (const header of getSortableHeaders()) {
  const button = header.querySelector(".table-sort-button");
  button?.addEventListener("click", () => {
    const tableName = header.dataset.sortTable || "";
    const field = header.dataset.sortField || "";
    if (tableName === "tags") {
      tagStatsSort = getNextSortState(tagStatsSort, field);
      loadTagStats().catch((error) => {
        logActivity(`Tag stats load failed: ${error.message}`);
      });
      return;
    }
    if (tableName === "document-types") {
      documentTypesSort = getNextSortState(documentTypesSort, field);
      loadDocumentTypeStats().catch((error) => {
        logActivity(`Document type stats load failed: ${error.message}`);
      });
    }
  });
}
