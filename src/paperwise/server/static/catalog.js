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
