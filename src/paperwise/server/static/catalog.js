for (const header of sortableHeaders) {
  const button = header.querySelector(".table-sort-button");
  button?.addEventListener("click", () => {
    const tableName = header.dataset.sortTable || "";
    const field = header.dataset.sortField || "";
    if (tableName === "tags") {
      tagStatsSort = getNextSortState(tagStatsSort, field);
      renderTagsList(currentTagStats);
      return;
    }
    if (tableName === "document-types") {
      documentTypesSort = getNextSortState(documentTypesSort, field);
      renderDocumentTypesList(currentDocumentTypeStats);
    }
  });
}
