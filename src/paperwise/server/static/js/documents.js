const filterDropdownState = new Map();
const DOCS_SORT_FIELDS = new Set([
  "title",
  "document_type",
  "correspondent",
  "tags",
  "document_date",
  "status",
]);
let activeFilterDropdown = null;
let docsFilters = {
  q: "",
  tag: [],
  correspondent: [],
  document_type: [],
  status: ["ready"],
};
let docsPage = 1;
let docsSort = { field: "", direction: "" };
let docsFilterNavigateTimer = 0;
let docsTotalCount = 0;
let docsListRequestSeq = 0;
let initialDocumentsHydrated = false;
let documentsEventsBound = false;

function cloneDocsFilters(filters) {
  return {
    q: String(filters?.q || "").trim(),
    tag: [...(filters?.tag || [])],
    correspondent: [...(filters?.correspondent || [])],
    document_type: [...(filters?.document_type || [])],
    status: [...(filters?.status || ["ready"])],
  };
}

function sanitizeDocsFilters(filters) {
  const normalized = cloneDocsFilters(filters);
  normalized.tag = unique(normalized.tag);
  normalized.correspondent = unique(normalized.correspondent);
  normalized.document_type = unique(normalized.document_type);
  normalized.status = unique(normalized.status);
  if (!normalized.status.length) {
    normalized.status = ["ready"];
  }
  return normalized;
}

function clearDocumentListStateForSession() {
  docsFilters = sanitizeDocsFilters({
    tag: [],
    correspondent: [],
    document_type: [],
    status: ["ready"],
  });
  docsPage = 1;
  docsSort = { field: "", direction: "" };
  docsTotalCount = 0;
  docsListRequestSeq = 0;
  docsFilterNavigateTimer = 0;
}

function resetDocumentListPage() {
  docsPage = 1;
}

function getDocumentListSortState() {
  return docsSort;
}

function getDocumentsPageElements() {
  const filterControls = getDocumentFilterControls();
  return {
    docsFilterForm: document.getElementById("docsFilterForm"),
    clearFiltersBtn: document.getElementById("clearFiltersBtn"),
    ...filterControls,
  };
}

function getDocumentFilterControls() {
  const filterTag = document.getElementById("filterTag");
  const filterCorrespondent = document.getElementById("filterCorrespondent");
  const filterType = document.getElementById("filterType");
  const filterStatus = document.getElementById("filterStatus");
  return {
    filterTag,
    filterCorrespondent,
    filterType,
    filterStatus,
    filterQuery: document.getElementById("filterQuery"),
    filterSelects: [filterTag, filterCorrespondent, filterType, filterStatus],
  };
}

function getFilterKey(selectEl) {
  const { filterTag, filterCorrespondent, filterType } = getDocumentFilterControls();
  if (selectEl === filterTag) {
    return "tag";
  }
  if (selectEl === filterCorrespondent) {
    return "correspondent";
  }
  if (selectEl === filterType) {
    return "document_type";
  }
  return "status";
}

function getSelectedValues(selectEl) {
  if (!selectEl) {
    return [];
  }
  return [...selectEl.selectedOptions].map((option) => option.value).filter((value) => value);
}

function setSelectedValues(selectEl, values) {
  if (!selectEl) {
    return;
  }
  const selected = new Set(values || []);
  for (const option of selectEl.options) {
    option.selected = selected.has(option.value);
  }
}

function summarizeSelectedValues(selectedValues, selectEl) {
  if (!selectedValues.length) {
    return "Any";
  }
  const displayValues = selectedValues.map((value) =>
    selectEl === getDocumentFilterControls().filterStatus ? formatStatus(value) : value
  );
  if (selectedValues.length === 1) {
    return displayValues[0];
  }
  return `${selectedValues.length} selected`;
}

function closeFilterDropdown(selectEl) {
  const state = filterDropdownState.get(selectEl);
  if (!state) {
    return;
  }
  state.panel.hidden = true;
  state.trigger.setAttribute("aria-expanded", "false");
  state.chip.classList.remove("is-open");
  if (activeFilterDropdown === selectEl) {
    activeFilterDropdown = null;
  }
}

function openFilterDropdown(selectEl) {
  if (activeFilterDropdown && activeFilterDropdown !== selectEl) {
    closeFilterDropdown(activeFilterDropdown);
  }
  const state = filterDropdownState.get(selectEl);
  if (!state) {
    return;
  }
  state.panel.hidden = false;
  state.trigger.setAttribute("aria-expanded", "true");
  state.chip.classList.add("is-open");
  activeFilterDropdown = selectEl;
  state.search.focus();
}

async function toggleFilterOption(selectEl, value) {
  for (const option of selectEl.options) {
    if (option.value === value) {
      option.selected = !option.selected;
      break;
    }
  }
  await applyFiltersFromControls();
}

function renderFilterDropdownOptions(selectEl) {
  const state = filterDropdownState.get(selectEl);
  if (!state) {
    return;
  }

  const query = state.search.value.trim().toLowerCase();
  const options = [...selectEl.options].filter((option) => {
    if (!query) {
      return true;
    }
    return option.textContent.toLowerCase().includes(query);
  });

  state.options.innerHTML = "";

  if (!options.length) {
    const empty = document.createElement("div");
    empty.className = "filter-dropdown-empty";
    empty.textContent = "No matches.";
    state.options.appendChild(empty);
    return;
  }

  for (const option of options) {
    const row = document.createElement("button");
    row.type = "button";
    row.className = "filter-dropdown-option";
    row.dataset.value = option.value;
    row.setAttribute("aria-pressed", option.selected ? "true" : "false");
    if (option.selected) {
      row.classList.add("is-selected");
    }

    const check = document.createElement("span");
    check.className = "filter-dropdown-check";
    check.textContent = option.selected ? "x" : "";

    const label = document.createElement("span");
    label.className = "filter-dropdown-option-label";
    label.textContent = option.textContent;

    row.appendChild(check);
    row.appendChild(label);
    state.options.appendChild(row);
  }
}

function renderFilterDropdown(selectEl) {
  const state = filterDropdownState.get(selectEl);
  if (!state) {
    return;
  }
  const selectedValues = getSelectedValues(selectEl);
  state.value.textContent = summarizeSelectedValues(selectedValues, selectEl);
  renderFilterDropdownOptions(selectEl);
}

function setupFilterDropdown(selectEl) {
  if (!selectEl || filterDropdownState.has(selectEl)) {
    return;
  }

  const chip = selectEl.closest(".filter-chip");
  if (!chip) {
    return;
  }

  const labelText = chip.querySelector(".chip-prefix")?.textContent?.trim() || "Filter";
  selectEl.classList.add("filter-select-native");

  const dropdown = document.createElement("div");
  dropdown.className = "filter-dropdown";

  const trigger = document.createElement("button");
  trigger.type = "button";
  trigger.className = "filter-dropdown-trigger";
  trigger.setAttribute("aria-expanded", "false");

  const triggerValue = document.createElement("span");
  triggerValue.className = "filter-dropdown-value";
  triggerValue.textContent = "Any";

  const triggerCaret = document.createElement("span");
  triggerCaret.className = "filter-dropdown-caret";
  triggerCaret.textContent = "▾";

  trigger.appendChild(triggerValue);
  trigger.appendChild(triggerCaret);

  const panel = document.createElement("div");
  panel.className = "filter-dropdown-panel";
  panel.hidden = true;

  const search = document.createElement("input");
  search.type = "search";
  search.className = "filter-dropdown-search";
  search.placeholder = `Filter ${labelText.toLowerCase()}`;

  const options = document.createElement("div");
  options.className = "filter-dropdown-options";

  panel.appendChild(search);
  panel.appendChild(options);
  dropdown.appendChild(trigger);
  dropdown.appendChild(panel);
  chip.appendChild(dropdown);

  filterDropdownState.set(selectEl, {
    chip,
    trigger,
    panel,
    search,
    options,
    value: triggerValue,
  });

  trigger.addEventListener("click", () => {
    if (panel.hidden) {
      openFilterDropdown(selectEl);
      renderFilterDropdownOptions(selectEl);
      return;
    }
    closeFilterDropdown(selectEl);
  });

  search.addEventListener("input", () => {
    renderFilterDropdownOptions(selectEl);
  });

  options.addEventListener("click", async (event) => {
    const button = event.target.closest(".filter-dropdown-option");
    if (!button) {
      return;
    }
    const value = button.dataset.value;
    if (!value) {
      return;
    }
    await toggleFilterOption(selectEl, value);
    renderFilterDropdown(selectEl);
  });
}

function applyDocumentListFiltersToControls() {
  const { filterTag, filterCorrespondent, filterType, filterStatus, filterQuery, filterSelects } =
    getDocumentFilterControls();
  if (filterQuery) {
    filterQuery.value = docsFilters.q || "";
  }
  setSelectedValues(filterTag, docsFilters.tag);
  setSelectedValues(filterCorrespondent, docsFilters.correspondent);
  setSelectedValues(filterType, docsFilters.document_type);
  setSelectedValues(filterStatus, docsFilters.status);
  for (const selectEl of filterSelects) {
    renderFilterDropdown(selectEl);
  }
}

function setSelectOptions(selectEl, values) {
  if (!selectEl) {
    return;
  }
  const key = getFilterKey(selectEl);
  const selectedValues = docsFilters[key] || [];
  const mergedValues = sortValues(unique([...values, ...selectedValues]));
  selectEl.innerHTML = "";

  for (const value of mergedValues) {
    const option = document.createElement("option");
    option.value = value;
    option.textContent = key === "status" ? formatStatus(value) : value;
    selectEl.appendChild(option);
  }
  setSelectedValues(selectEl, selectedValues);
  renderFilterDropdown(selectEl);
}

function readFiltersFromControls() {
  const { filterTag, filterCorrespondent, filterType, filterStatus, filterQuery } =
    getDocumentFilterControls();
  docsFilters.q = String(filterQuery?.value || "").trim();
  docsFilters.tag = getSelectedValues(filterTag);
  docsFilters.correspondent = getSelectedValues(filterCorrespondent);
  docsFilters.document_type = getSelectedValues(filterType);
  docsFilters.status = getSelectedValues(filterStatus);
}

function refreshFilterOptions(options) {
  const { filterTag, filterCorrespondent, filterType, filterStatus } = getDocumentFilterControls();
  const source = options && typeof options === "object" ? options : {};
  setSelectOptions(filterTag, Array.isArray(source.tags) ? source.tags : []);
  setSelectOptions(filterCorrespondent, Array.isArray(source.correspondents) ? source.correspondents : []);
  setSelectOptions(filterType, Array.isArray(source.document_types) ? source.document_types : []);
  setSelectOptions(
    filterStatus,
    Array.isArray(source.statuses) ? source.statuses : ["received", "processing", "failed", "ready"]
  );
}

function refreshFilterOptionsFromDocuments(documents) {
  const tags = new Set();
  const correspondents = new Set();
  const documentTypes = new Set();
  const statuses = new Set();

  for (const doc of documents) {
    if (doc.status) {
      statuses.add(doc.status);
    }
    const metadata = doc.llm_metadata;
    if (!metadata) {
      continue;
    }
    if (metadata.correspondent) {
      correspondents.add(metadata.correspondent);
    }
    if (metadata.document_type) {
      documentTypes.add(metadata.document_type);
    }
    for (const tag of metadata.tags || []) {
      if (tag) {
        tags.add(tag);
      }
    }
  }

  refreshFilterOptions({
    tags: [...tags],
    correspondents: [...correspondents],
    document_types: [...documentTypes],
    statuses: ["received", "processing", "failed", "ready", ...statuses],
  });
}

function applyDocsStateToUrl(url) {
  url.searchParams.delete("q");
  url.searchParams.delete("tag");
  url.searchParams.delete("correspondent");
  url.searchParams.delete("document_type");
  url.searchParams.delete("status");
  url.searchParams.delete("view");
  url.searchParams.delete("page");
  url.searchParams.delete("page_size");
  url.searchParams.delete("sort_by");
  url.searchParams.delete("sort_dir");

  if (docsFilters.q) {
    url.searchParams.set("q", docsFilters.q);
  }
  for (const value of docsFilters.tag) {
    url.searchParams.append("tag", value);
  }
  for (const value of docsFilters.correspondent) {
    url.searchParams.append("correspondent", value);
  }
  for (const value of docsFilters.document_type) {
    url.searchParams.append("document_type", value);
  }
  for (const value of docsFilters.status) {
    url.searchParams.append("status", value);
  }
  if (docsPage > 1) {
    url.searchParams.set("page", String(docsPage));
  }
  if (docsPageSize !== 20) {
    url.searchParams.set("page_size", String(docsPageSize));
  }
  if (docsSort.field && docsSort.direction) {
    url.searchParams.set("sort_by", docsSort.field);
    url.searchParams.set("sort_dir", docsSort.direction);
  }
}

function buildDocumentsUrl() {
  const url = new URL("/ui/documents", window.location.origin);
  applyDocsStateToUrl(url);
  const qs = url.searchParams.toString();
  return qs ? `${url.pathname}?${qs}` : url.pathname;
}

function readDocumentListStateFromUrl() {
  const params = new URLSearchParams(window.location.search);
  docsFilters.q = String(params.get("q") || "").trim();
  docsFilters.tag = unique(params.getAll("tag"));
  docsFilters.correspondent = unique(params.getAll("correspondent"));
  docsFilters.document_type = unique(params.getAll("document_type"));
  const statusValues = unique(params.getAll("status"));
  docsFilters.status = statusValues.length ? statusValues : ["ready"];
  const pageValue = Number(params.get("page") || "1");
  docsPage = Number.isInteger(pageValue) && pageValue > 0 ? pageValue : 1;
  const pageSizeValue = params.get("page_size") || String(docsPageSize || 20);
  docsPageSize = normalizePageSize(pageSizeValue);
  docsSort = normalizeSortState(
    {
      field: params.get("sort_by") || "",
      direction: params.get("sort_dir") || "",
    },
    DOCS_SORT_FIELDS
  );
}

function navigateToDocumentsPageFromState() {
  window.location.href = buildDocumentsUrl();
}

function applyFiltersFromControls() {
  readFiltersFromControls();
  docsPage = 1;
  navigateToDocumentsPageFromState();
}

function applyDocumentsPartial(payload) {
  const docsTableBody = document.getElementById("docsTableBody");
  const documentsPaginationToolbar = document.getElementById("documentsPaginationToolbar");
  applyTableBodyPartial(docsTableBody, payload);
  replaceElementHtml(documentsPaginationToolbar, payload.pagination_toolbar_html);
  docsTotalCount = Number(payload.documents_total || 0);
  docsPage = Math.max(1, Number(payload.documents_page || docsPage || 1));
  docsPageSize = normalizePageSize(payload.documents_page_size || docsPageSize);
}

function prepareDocumentListDelete() {
  const docsTableBody = document.getElementById("docsTableBody");
  const visibleDocRows = docsTableBody?.querySelectorAll("tr[data-doc-id]").length || 0;
  if (docsTableBody && docsPage > 1 && visibleDocRows <= 1) {
    docsPage -= 1;
  }
}

async function refreshDocumentListAfterDelete() {
  if (document.getElementById("docsTableBody")) {
    await loadDocumentsList();
    return;
  }
  await initializeCurrentPageData();
}

async function loadDocumentsList() {
  const requestSeq = ++docsListRequestSeq;
  const docsTableBody = document.getElementById("docsTableBody");
  renderSortHeaders();
  const query = new URLSearchParams({
    page: String(docsPage),
    page_size: String(docsPageSize),
  });
  if (docsSort.field && docsSort.direction) {
    query.set("sort_by", docsSort.field);
    query.set("sort_dir", docsSort.direction);
  }
  if (docsFilters.q) {
    query.set("q", docsFilters.q);
  }
  for (const value of docsFilters.tag) {
    query.append("tag", value);
  }
  for (const value of docsFilters.correspondent) {
    query.append("correspondent", value);
  }
  for (const value of docsFilters.document_type) {
    query.append("document_type", value);
  }
  for (const value of docsFilters.status) {
    query.append("status", value);
  }

  let payload;
  try {
    payload = await loadTablePartial({
      url: `/ui/partials/documents?${query.toString()}`,
      tbody: docsTableBody,
      loadingColspan: 7,
      loadingMessage: "Loading documents...",
    });
  } catch (error) {
    logActivity(`Document list failed: ${error.message}`);
    return;
  }
  if (requestSeq !== docsListRequestSeq) {
    return;
  }
  applyDocumentsPartial(payload);
  logActivity(`Loaded ${Number(payload.documents_returned || 0)} document(s) of ${docsTotalCount} total`);
}

function hydrateInitialDocumentsData(initialData) {
  if (initialDocumentsHydrated) {
    return true;
  }
  if (
    initialData.authenticated !== true ||
    !Array.isArray(initialData.documents)
  ) {
    return false;
  }
  docsTotalCount = Number(initialData.documents_total || initialData.documents.length || 0);
  docsPage = Math.max(1, Number(initialData.documents_page || docsPage || 1));
  docsPageSize = normalizePageSize(initialData.documents_page_size || docsPageSize);
  if (initialData.document_filter_options) {
    refreshFilterOptions(initialData.document_filter_options);
  } else {
    refreshFilterOptionsFromDocuments(initialData.documents);
  }
  logActivity(`Loaded ${initialData.documents.length} document(s) of ${docsTotalCount} total`);
  initialDocumentsHydrated = true;
  return true;
}

function bindDocumentsEvents() {
  if (documentsEventsBound) {
    return;
  }
  const { docsFilterForm, clearFiltersBtn, filterQuery, filterSelects } = getDocumentsPageElements();

  docsFilterForm?.addEventListener("submit", (event) => {
    event.preventDefault();
  });

  for (const selectEl of filterSelects) {
    if (!selectEl) {
      continue;
    }
    selectEl.addEventListener("change", () => {
      applyFiltersFromControls();
    });
  }

  for (const selectEl of filterSelects) {
    if (!selectEl) {
      continue;
    }
    setupFilterDropdown(selectEl);
  }

  for (const header of getSortableHeaders()) {
    const button = header.querySelector(".table-sort-button");
    button?.addEventListener("click", () => {
      const tableName = header.dataset.sortTable || "";
      const field = header.dataset.sortField || "";
      if (tableName !== "docs") {
        return;
      }
      docsSort = getNextSortState(docsSort, field);
      docsPage = 1;
      renderSortHeaders();
      navigateToDocumentsPageFromState();
    });
  }

  document.addEventListener("click", (event) => {
    if (!activeFilterDropdown) {
      return;
    }
    const state = filterDropdownState.get(activeFilterDropdown);
    if (!state) {
      return;
    }
    if (!state.chip.contains(event.target)) {
      closeFilterDropdown(activeFilterDropdown);
    }
  });

  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape" && activeFilterDropdown) {
      closeFilterDropdown(activeFilterDropdown);
    }
  });

  clearFiltersBtn?.addEventListener("click", () => {
    docsFilters.q = "";
    docsFilters.tag = [];
    docsFilters.correspondent = [];
    docsFilters.document_type = [];
    docsFilters.status = ["ready"];
    docsPage = 1;
    applyDocumentListFiltersToControls();
    navigateToDocumentsPageFromState();
  });

  filterQuery?.addEventListener("input", () => {
    if (docsFilterNavigateTimer) {
      window.clearTimeout(docsFilterNavigateTimer);
    }
    docsFilterNavigateTimer = window.setTimeout(() => {
      docsFilterNavigateTimer = 0;
      applyFiltersFromControls();
    }, 350);
  });

  document.addEventListener("click", (event) => {
    const button =
      event.target instanceof Element ? event.target.closest("[data-docs-page-action]") : null;
    if (!(button instanceof HTMLButtonElement) || button.disabled) {
      return;
    }
    if (button.dataset.docsPageAction === "prev") {
      docsPage = Math.max(1, docsPage - 1);
    } else if (button.dataset.docsPageAction === "next") {
      docsPage += 1;
    } else {
      return;
    }
    navigateToDocumentsPageFromState();
  });

  documentsEventsBound = true;
}

window.initializePaperwisePage = async ({ authenticated, initialData }) => {
  if (authenticated !== true) {
    return;
  }
  bindDocumentsEvents();
  if (hydrateInitialDocumentsData(initialData || {})) {
    return;
  }
  await loadDocumentsList();
};
