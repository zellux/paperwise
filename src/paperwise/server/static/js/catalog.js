import {
  applyTableBodyPartial,
  loadTablePartial,
} from "paperwise/shared";
import {
  getNextSortState,
  getSortableHeaders,
  logActivity,
  renderSortHeaders,
} from "paperwise/app";

let tagStatsSort = { field: "", direction: "" };
let documentTypesSort = { field: "", direction: "" };
let tagStatsRequestSeq = 0;
let documentTypeStatsRequestSeq = 0;
let initialTagStatsHydrated = false;
let initialDocumentTypesHydrated = false;

function getCatalogElements() {
  return {
    tagsTableBody: document.getElementById("tagsTableBody"),
    documentTypesTableBody: document.getElementById("documentTypesTableBody"),
  };
}

export function clearSessionState() {
  tagStatsSort = { field: "", direction: "" };
  documentTypesSort = { field: "", direction: "" };
}

export function getSortStateForTable(tableName) {
  if (tableName === "tags") {
    return tagStatsSort;
  }
  if (tableName === "document-types") {
    return documentTypesSort;
  }
  return { field: "", direction: "" };
}

function applyTagsPartial(payload) {
  const { tagsTableBody } = getCatalogElements();
  applyTableBodyPartial(tagsTableBody, payload);
  renderSortHeaders();
}

function applyDocumentTypesPartial(payload) {
  const { documentTypesTableBody } = getCatalogElements();
  applyTableBodyPartial(documentTypesTableBody, payload);
  renderSortHeaders();
}

async function loadTagStats() {
  const { tagsTableBody } = getCatalogElements();
  const requestSeq = ++tagStatsRequestSeq;
  renderSortHeaders();
  const query = new URLSearchParams();
  if (tagStatsSort.field && tagStatsSort.direction) {
    query.set("sort_by", tagStatsSort.field);
    query.set("sort_dir", tagStatsSort.direction);
  }
  const suffix = query.toString() ? `?${query.toString()}` : "";
  let payload;
  try {
    payload = await loadTablePartial({
      url: `/ui/partials/tags${suffix}`,
      tbody: tagsTableBody,
      loadingColspan: 3,
      loadingMessage: "Loading tags...",
    });
  } catch (error) {
    logActivity(`Tag stats load failed: ${error.message}`);
    return;
  }
  if (requestSeq !== tagStatsRequestSeq) {
    return;
  }
  applyTagsPartial(payload);
  logActivity(`Loaded ${Number(payload.dataset.tagCount || 0)} tag(s)`);
}

async function loadDocumentTypeStats() {
  const { documentTypesTableBody } = getCatalogElements();
  const requestSeq = ++documentTypeStatsRequestSeq;
  renderSortHeaders();
  const query = new URLSearchParams();
  if (documentTypesSort.field && documentTypesSort.direction) {
    query.set("sort_by", documentTypesSort.field);
    query.set("sort_dir", documentTypesSort.direction);
  }
  const suffix = query.toString() ? `?${query.toString()}` : "";
  let payload;
  try {
    payload = await loadTablePartial({
      url: `/ui/partials/document-types${suffix}`,
      tbody: documentTypesTableBody,
      loadingColspan: 3,
      loadingMessage: "Loading document types...",
    });
  } catch (error) {
    logActivity(`Document type stats load failed: ${error.message}`);
    return;
  }
  if (requestSeq !== documentTypeStatsRequestSeq) {
    return;
  }
  applyDocumentTypesPartial(payload);
  logActivity(`Loaded ${Number(payload.dataset.documentTypeCount || 0)} document type(s)`);
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

function bindCatalogSortHeaders() {
  for (const header of getSortableHeaders()) {
    if (header.dataset.catalogSortBound === "true") {
      continue;
    }
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
    header.dataset.catalogSortBound = "true";
  }
}

export async function initializePage({ authenticated, initialData }) {
  if (authenticated !== true) {
    return;
  }
  bindCatalogSortHeaders();
  const { tagsTableBody, documentTypesTableBody } = getCatalogElements();
  if (tagsTableBody) {
    if (!hydrateInitialTagStats(initialData || {})) {
      await loadTagStats();
    }
    return;
  }
  if (documentTypesTableBody && !hydrateInitialDocumentTypes(initialData || {})) {
    await loadDocumentTypeStats();
  }
}
