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

pagePrevBtn?.addEventListener("click", () => {
  if (docsPage <= 1) {
    return;
  }
  docsPage -= 1;
  navigateToDocumentsPageFromState();
});

pageNextBtn?.addEventListener("click", () => {
  docsPage += 1;
  navigateToDocumentsPageFromState();
});
