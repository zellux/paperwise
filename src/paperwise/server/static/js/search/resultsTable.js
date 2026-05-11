export function renderSearchResultsTable(payload, tableBody, navigateToDocument) {
  if (!tableBody) {
    return;
  }
  const hits = Array.isArray(payload?.hits) ? payload.hits : [];
  if (!hits.length) {
    tableBody.innerHTML = '<tr><td colspan="6">No matches found.</td></tr>';
    return;
  }
  tableBody.innerHTML = "";
  for (const hit of hits) {
    const row = document.createElement("tr");

    const titleCell = document.createElement("td");
    titleCell.setAttribute("data-label", "Title");
    const titleBtn = document.createElement("button");
    titleBtn.type = "button";
    titleBtn.className = "link-button";
    titleBtn.textContent = hit.title || hit.filename || hit.document_id;
    titleBtn.addEventListener("click", () => navigateToDocument(hit.document_id));
    titleCell.appendChild(titleBtn);

    const typeCell = document.createElement("td");
    typeCell.setAttribute("data-label", "Type");
    typeCell.textContent = hit.document_type || "-";

    const correspondentCell = document.createElement("td");
    correspondentCell.setAttribute("data-label", "Correspondent");
    correspondentCell.textContent = hit.correspondent || "-";

    const tagsCell = document.createElement("td");
    tagsCell.setAttribute("data-label", "Tags");
    tagsCell.textContent = Array.isArray(hit.tags) && hit.tags.length ? hit.tags.join(", ") : "-";

    const scoreCell = document.createElement("td");
    scoreCell.setAttribute("data-label", "Score");
    scoreCell.textContent = Number(hit.score || 0).toFixed(3);

    const snippetCell = document.createElement("td");
    snippetCell.setAttribute("data-label", "Snippet");
    snippetCell.textContent = hit.snippet || "-";

    row.appendChild(titleCell);
    row.appendChild(typeCell);
    row.appendChild(correspondentCell);
    row.appendChild(tagsCell);
    row.appendChild(scoreCell);
    row.appendChild(snippetCell);
    tableBody.appendChild(row);
  }
}
