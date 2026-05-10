const tagsTableBody = document.getElementById("tagsTableBody");
const documentTypesTableBody = document.getElementById("documentTypesTableBody");

let tagStatsSort = { field: "", direction: "" };
let documentTypesSort = { field: "", direction: "" };
let tagStatsRequestSeq = 0;
let documentTypeStatsRequestSeq = 0;

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

async function initializeTagsView() {
  await loadTagStats();
}

async function initializeDocumentTypesView() {
  await loadDocumentTypeStats();
}

for (const header of sortableHeaders) {
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
