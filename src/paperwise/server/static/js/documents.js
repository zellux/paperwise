let initialDocumentsHydrated = false;

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
  refreshFilterOptionsFromDocuments(initialData.documents);
  logActivity(`Loaded ${initialData.documents.length} document(s) of ${docsTotalCount} total`);
  initialDocumentsHydrated = true;
  return true;
}

window.initializePaperwisePage = async ({ authenticated, initialData }) => {
  if (authenticated !== true) {
    return;
  }
  if (hydrateInitialDocumentsData(initialData || {})) {
    return;
  }
  await loadDocumentsList();
};

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

for (const header of sortableHeaders) {
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
  applyFiltersToControls();
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
