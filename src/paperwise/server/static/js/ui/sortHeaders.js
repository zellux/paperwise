import { getNextSortState } from "../state/preferences.js";

export function getSortableHeaders() {
  return [...document.querySelectorAll("th[data-sort-table][data-sort-field]")];
}

export function renderSortHeaders(getSortStateForTable) {
  for (const header of getSortableHeaders()) {
    const tableName = header.dataset.sortTable || "";
    const field = header.dataset.sortField || "";
    const sortState = getSortStateForTable(tableName);
    const direction = sortState.field === field ? sortState.direction : "";
    const button = header.querySelector(".table-sort-button");
    const indicator = header.querySelector(".table-sort-indicator");
    header.setAttribute(
      "aria-sort",
      direction === "asc" ? "ascending" : direction === "desc" ? "descending" : "none"
    );
    if (indicator) {
      indicator.textContent = direction === "asc" ? "▲" : direction === "desc" ? "▼" : "⇅";
    }
    if (button) {
      const label = button.querySelector("span")?.textContent?.trim() || field;
      const nextDirection = getNextSortState(sortState, field).direction || "none";
      button.title = `Sort ${label} (${nextDirection})`;
    }
  }
}
