const uploadForm = document.getElementById("uploadForm");
const documentMetaForm = document.getElementById("documentMetaForm");
const backToDocsBtn = document.getElementById("backToDocsBtn");
const reprocessDocumentBtn = document.getElementById("reprocessDocumentBtn");
const viewDocumentFileBtn = document.getElementById("viewDocumentFileBtn");
const docsFilterForm = document.getElementById("docsFilterForm");
const clearFiltersBtn = document.getElementById("clearFiltersBtn");
const restartPendingBtn = document.getElementById("restartPendingBtn");

const metaTitleInput = document.getElementById("metaTitle");
const metaDateInput = document.getElementById("metaDate");
const metaCorrespondentInput = document.getElementById("metaCorrespondent");
const metaTypeInput = document.getElementById("metaType");
const metaTagsInput = document.getElementById("metaTags");
const detailDocId = document.getElementById("detailDocId");
const detailOwnerId = document.getElementById("detailOwnerId");
const detailFilename = document.getElementById("detailFilename");
const detailStatus = document.getElementById("detailStatus");
const detailCreatedAt = document.getElementById("detailCreatedAt");
const detailContentType = document.getElementById("detailContentType");
const detailSizeBytes = document.getElementById("detailSizeBytes");
const detailChecksum = document.getElementById("detailChecksum");
const detailBlobUri = document.getElementById("detailBlobUri");
const documentHistoryList = document.getElementById("documentHistoryList");
const filterTag = document.getElementById("filterTag");
const filterCorrespondent = document.getElementById("filterCorrespondent");
const filterType = document.getElementById("filterType");
const filterStatus = document.getElementById("filterStatus");
const filterSelects = [filterTag, filterCorrespondent, filterType, filterStatus];

const activityOutput = document.getElementById("activityOutput");
const docsTableBody = document.getElementById("docsTableBody");
const tagsTableBody = document.getElementById("tagsTableBody");
const pendingTableBody = document.getElementById("pendingTableBody");
const navLinks = [...document.querySelectorAll(".nav-link")];
const views = [...document.querySelectorAll(".view")];
const filterDropdownState = new Map();
let activeFilterDropdown = null;
let currentViewId = "section-docs";
const VIEW_ID_TO_PARAM = {
  "section-docs": "docs",
  "section-document": "document",
  "section-tags": "tags",
  "section-pending": "pending",
  "section-upload": "upload",
  "section-activity": "activity",
};
const VIEW_PARAM_TO_ID = Object.fromEntries(
  Object.entries(VIEW_ID_TO_PARAM).map(([viewId, param]) => [param, viewId])
);
const PATH_TO_VIEW_ID = {
  "/ui/documents": "section-docs",
  "/ui/document": "section-document",
  "/ui/tags": "section-tags",
  "/ui/pending": "section-pending",
  "/ui/upload": "section-upload",
  "/ui/activity": "section-activity",
};
const VIEW_ID_TO_PATH = {
  "section-docs": "/ui/documents",
  "section-document": "/ui/document",
  "section-tags": "/ui/tags",
  "section-pending": "/ui/pending",
  "section-upload": "/ui/upload",
  "section-activity": "/ui/activity",
};

let currentDocumentId = "";
const docsFilters = {
  tag: [],
  correspondent: [],
  document_type: [],
  status: ["ready"],
};

function formatStatus(value) {
  if (!value) {
    return "-";
  }
  return value
    .split("_")
    .join(" ")
    .toUpperCase();
}

function formatBytes(value) {
  const bytes = Number(value || 0);
  if (!Number.isFinite(bytes) || bytes <= 0) {
    return "0 B";
  }
  if (bytes < 1024) {
    return `${bytes} B`;
  }
  const kb = bytes / 1024;
  if (kb < 1024) {
    return `${kb.toFixed(1)} KB`;
  }
  const mb = kb / 1024;
  return `${mb.toFixed(2)} MB`;
}

function formatHistoryEventType(value) {
  const labels = {
    metadata_changed: "Metadata changed",
    tags_added: "Tags added",
    tags_removed: "Tags removed",
    file_moved: "File moved",
    processing_restarted: "Processing restarted",
    processing_completed: "Processing completed",
  };
  return labels[value] || formatStatus(value || "update");
}

function formatHistoryActor(event) {
  if (event.actor_type === "user") {
    return event.actor_id ? `User: ${event.actor_id}` : "User";
  }
  return "System";
}

function stringifyHistoryValue(value) {
  if (value === null || value === undefined || value === "") {
    return "(empty)";
  }
  return String(value);
}

function buildHistoryChangeLines(event) {
  const changes = event.changes || {};
  if (event.event_type === "metadata_changed") {
    const lines = [];
    for (const [field, values] of Object.entries(changes)) {
      const before = stringifyHistoryValue(values?.before);
      const after = stringifyHistoryValue(values?.after);
      lines.push(`${field}: ${before} -> ${after}`);
    }
    return lines;
  }
  if (event.event_type === "tags_added") {
    const tags = Array.isArray(changes.tags) ? changes.tags : [];
    return [tags.length ? `Added: ${tags.join(", ")}` : "Added tags"];
  }
  if (event.event_type === "tags_removed") {
    const tags = Array.isArray(changes.tags) ? changes.tags : [];
    return [tags.length ? `Removed: ${tags.join(", ")}` : "Removed tags"];
  }
  if (event.event_type === "file_moved") {
    const fromPath = toRelativeBlobPath(changes.from_blob_uri || "");
    const toPath = toRelativeBlobPath(changes.to_blob_uri || "");
    return [`From: ${fromPath}`, `To: ${toPath}`];
  }
  if (event.event_type === "processing_restarted") {
    const before = stringifyHistoryValue(changes.status?.before);
    const after = stringifyHistoryValue(changes.status?.after);
    return [`Status: ${before} -> ${after}`];
  }
  if (event.event_type === "processing_completed") {
    const before = stringifyHistoryValue(changes.status?.before);
    const after = stringifyHistoryValue(changes.status?.after);
    return [`Status: ${before} -> ${after}`];
  }
  try {
    return [JSON.stringify(changes)];
  } catch {
    return ["Details unavailable"];
  }
}

function renderDocumentHistory(events) {
  if (!documentHistoryList) {
    return;
  }
  if (!Array.isArray(events) || !events.length) {
    documentHistoryList.innerHTML =
      '<p class="document-history-empty">No history entries yet.</p>';
    return;
  }

  documentHistoryList.innerHTML = "";
  for (const event of events) {
    const item = document.createElement("article");
    item.className = "document-history-item";

    const header = document.createElement("div");
    header.className = "document-history-header";

    const type = document.createElement("span");
    type.className = "document-history-type";
    type.textContent = formatHistoryEventType(event.event_type);

    const meta = document.createElement("span");
    meta.className = "document-history-meta";
    const timestamp = event.created_at ? new Date(event.created_at).toLocaleString() : "-";
    meta.textContent = `${formatHistoryActor(event)} | ${event.source || "-"} | ${timestamp}`;

    const changes = document.createElement("div");
    changes.className = "document-history-changes";
    for (const line of buildHistoryChangeLines(event)) {
      const changeLine = document.createElement("p");
      changeLine.className = "document-history-change";
      changeLine.textContent = line;
      changes.appendChild(changeLine);
    }

    header.appendChild(type);
    header.appendChild(meta);
    item.appendChild(header);
    item.appendChild(changes);
    documentHistoryList.appendChild(item);
  }
}

function toRelativeBlobPath(blobUri) {
  if (!blobUri) {
    return "-";
  }
  try {
    const url = new URL(blobUri);
    if (url.protocol !== "file:") {
      return blobUri;
    }
    const absolutePath = decodeURIComponent(url.pathname);
    const marker = "/local/object-store/";
    const idx = absolutePath.indexOf(marker);
    if (idx >= 0) {
      return absolutePath.slice(idx + marker.length);
    }
    return absolutePath.replace(/^\/+/, "");
  } catch {
    return blobUri;
  }
}

function logActivity(message) {
  const now = new Date().toLocaleTimeString();
  activityOutput.textContent = `[${now}] ${message}\n${activityOutput.textContent}`;
}

function delay(ms) {
  return new Promise((resolve) => {
    window.setTimeout(resolve, ms);
  });
}

function setActiveNav(targetId) {
  for (const link of navLinks) {
    link.classList.toggle("active", link.dataset.target === targetId);
  }
}

function setActiveView(targetId) {
  if (!views.some((view) => view.id === targetId)) {
    return;
  }
  currentViewId = targetId;
  for (const view of views) {
    view.classList.toggle("view-hidden", view.id !== targetId);
  }
}

function getCurrentPathViewId() {
  const path = window.location.pathname.replace(/\/+$/, "") || "/";
  return PATH_TO_VIEW_ID[path] || "section-docs";
}

function splitTags(value) {
  return value
    .split(",")
    .map((part) => part.trim())
    .filter((part) => part.length > 0);
}

function unique(values) {
  return [...new Set(values.filter((item) => item && item.trim()))];
}

function sortValues(values) {
  return [...values].sort((a, b) => a.localeCompare(b, undefined, { sensitivity: "base" }));
}

function getFilterKey(selectEl) {
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
  return [...selectEl.selectedOptions].map((option) => option.value).filter((value) => value);
}

function setSelectedValues(selectEl, values) {
  const selected = new Set(values || []);
  for (const option of selectEl.options) {
    option.selected = selected.has(option.value);
  }
}

function summarizeSelectedValues(selectedValues) {
  if (!selectedValues.length) {
    return "Any";
  }
  if (selectedValues.length === 1) {
    return selectedValues[0];
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
  state.value.textContent = summarizeSelectedValues(selectedValues);
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

function applyFiltersToControls() {
  setSelectedValues(filterTag, docsFilters.tag);
  setSelectedValues(filterCorrespondent, docsFilters.correspondent);
  setSelectedValues(filterType, docsFilters.document_type);
  setSelectedValues(filterStatus, docsFilters.status);
  for (const selectEl of filterSelects) {
    renderFilterDropdown(selectEl);
  }
}

function setSelectOptions(selectEl, values) {
  const key = getFilterKey(selectEl);
  const selectedValues = docsFilters[key] || [];
  const mergedValues = sortValues(unique([...values, ...selectedValues]));
  selectEl.innerHTML = "";

  for (const value of mergedValues) {
    const option = document.createElement("option");
    option.value = value;
    option.textContent = value;
    selectEl.appendChild(option);
  }
  setSelectedValues(selectEl, selectedValues);
  renderFilterDropdown(selectEl);
}

function readFiltersFromControls() {
  docsFilters.tag = getSelectedValues(filterTag);
  docsFilters.correspondent = getSelectedValues(filterCorrespondent);
  docsFilters.document_type = getSelectedValues(filterType);
  docsFilters.status = getSelectedValues(filterStatus);
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

  setSelectOptions(filterTag, [...tags]);
  setSelectOptions(filterCorrespondent, [...correspondents]);
  setSelectOptions(filterType, [...documentTypes]);
  setSelectOptions(filterStatus, ["received", "processing", "ready", ...statuses]);
}

function syncUrlFromFilters() {
  const url = new URL(window.location.href);
  url.searchParams.delete("tag");
  url.searchParams.delete("correspondent");
  url.searchParams.delete("document_type");
  url.searchParams.delete("status");
  url.searchParams.delete("view");

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
  const viewPath = VIEW_ID_TO_PATH[currentViewId];
  if (viewPath) {
    url.pathname = viewPath;
  }

  const qs = url.searchParams.toString();
  window.history.replaceState(null, "", qs ? `${url.pathname}?${qs}` : url.pathname);
}

function readFiltersFromUrl() {
  const params = new URLSearchParams(window.location.search);
  docsFilters.tag = unique(params.getAll("tag"));
  docsFilters.correspondent = unique(params.getAll("correspondent"));
  docsFilters.document_type = unique(params.getAll("document_type"));
  const statusValues = unique(params.getAll("status"));
  docsFilters.status = statusValues.length ? statusValues : ["ready"];
  const viewFromUrl = params.get("view");
  const mappedViewId = viewFromUrl ? (VIEW_PARAM_TO_ID[viewFromUrl] || viewFromUrl) : "";
  const pathViewId = getCurrentPathViewId();
  if (pathViewId && views.some((view) => view.id === pathViewId)) {
    currentViewId = pathViewId;
  } else if (mappedViewId && views.some((view) => view.id === mappedViewId)) {
    // Backward compatibility for old links that use ?view=...
    currentViewId = mappedViewId;
  } else {
    currentViewId = "section-docs";
  }
}

async function applyFiltersFromControls() {
  readFiltersFromControls();
  syncUrlFromFilters();
  await loadDocumentsList();
}

function navigateToDocument(documentId) {
  const url = new URL("/ui/document", window.location.origin);
  url.searchParams.set("id", documentId);
  window.location.href = `${url.pathname}?${url.searchParams.toString()}`;
}

function openDocumentFile(documentId) {
  window.open(`/documents/${documentId}/file`, "_blank", "noopener,noreferrer");
}

function createActionIcon(name) {
  const ns = "http://www.w3.org/2000/svg";
  const svg = document.createElementNS(ns, "svg");
  svg.setAttribute("viewBox", "0 0 24 24");
  svg.setAttribute("fill", "none");
  svg.setAttribute("stroke", "currentColor");
  svg.setAttribute("stroke-width", "2");
  svg.setAttribute("stroke-linecap", "round");
  svg.setAttribute("stroke-linejoin", "round");
  svg.classList.add("action-icon-svg");

  const addPath = (d) => {
    const path = document.createElementNS(ns, "path");
    path.setAttribute("d", d);
    svg.appendChild(path);
  };
  const addLine = (x1, y1, x2, y2) => {
    const line = document.createElementNS(ns, "line");
    line.setAttribute("x1", x1);
    line.setAttribute("y1", y1);
    line.setAttribute("x2", x2);
    line.setAttribute("y2", y2);
    svg.appendChild(line);
  };
  const addPolyline = (points) => {
    const polyline = document.createElementNS(ns, "polyline");
    polyline.setAttribute("points", points);
    svg.appendChild(polyline);
  };

  if (name === "external-link") {
    addPath("M15 3h6v6");
    addPath("M10 14 21 3");
    addPath("M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6");
    return svg;
  }
  if (name === "file-text") {
    addPath("M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z");
    addPolyline("14 2 14 8 20 8");
    addLine("16", "13", "8", "13");
    addLine("16", "17", "8", "17");
    addPolyline("10 9 9 9 8 9");
    return svg;
  }

  addPath("M12 5v14");
  addPath("M5 12h14");
  return svg;
}

function createIconActionButton({ icon, label, onClick }) {
  const button = document.createElement("button");
  button.className = "action-icon-btn";
  button.type = "button";
  button.title = label;
  button.setAttribute("aria-label", label);
  button.appendChild(createActionIcon(icon));
  button.addEventListener("click", onClick);
  return button;
}

function getSuggestedTitle(doc) {
  if (doc.llm_metadata && doc.llm_metadata.suggested_title) {
    return doc.llm_metadata.suggested_title;
  }
  return "(Pending title)";
}

function renderDocsList(documents) {
  if (!documents.length) {
    docsTableBody.innerHTML = '<tr><td colspan="7">No documents found.</td></tr>';
    return;
  }
  docsTableBody.innerHTML = "";
  for (const doc of documents) {
    const row = document.createElement("tr");

    let suggestedTitle = "-";
    let documentType = "-";
    let correspondent = "-";
    let tags = "-";
    let documentDate = "-";
    if (doc.llm_metadata) {
      const m = doc.llm_metadata;
      suggestedTitle = m.suggested_title || "-";
      documentType = m.document_type || "-";
      correspondent = m.correspondent || "-";
      tags = Array.isArray(m.tags) && m.tags.length ? m.tags.join(", ") : "-";
      documentDate = m.document_date || "-";
    }

    const titleCell = document.createElement("td");
    titleCell.setAttribute("data-label", "Title");
    const titleButton = document.createElement("button");
    titleButton.className = "link-button";
    titleButton.type = "button";
    titleButton.textContent = suggestedTitle;
    titleButton.addEventListener("click", () => {
      navigateToDocument(doc.id);
    });
    titleCell.appendChild(titleButton);

    const typeCell = document.createElement("td");
    typeCell.setAttribute("data-label", "Type");
    typeCell.textContent = documentType;
    const correspondentCell = document.createElement("td");
    correspondentCell.setAttribute("data-label", "Correspondent");
    correspondentCell.textContent = correspondent;
    const tagsCell = document.createElement("td");
    tagsCell.setAttribute("data-label", "Tags");
    if (doc.llm_metadata && Array.isArray(doc.llm_metadata.tags) && doc.llm_metadata.tags.length) {
      const pills = document.createElement("div");
      pills.className = "tag-pills";
      for (const tag of doc.llm_metadata.tags) {
        const pill = document.createElement("span");
        pill.className = "tag-pill";
        pill.textContent = tag;
        pills.appendChild(pill);
      }
      tagsCell.appendChild(pills);
    } else {
      tagsCell.textContent = tags;
    }
    const dateCell = document.createElement("td");
    dateCell.setAttribute("data-label", "Date");
    dateCell.textContent = documentDate;
    const statusCell = document.createElement("td");
    statusCell.setAttribute("data-label", "Status");
    statusCell.textContent = formatStatus(doc.status);

    const actionCell = document.createElement("td");
    actionCell.setAttribute("data-label", "Action");
    const actionsWrap = document.createElement("div");
    actionsWrap.className = "table-actions";
    actionsWrap.appendChild(
      createIconActionButton({
        icon: "external-link",
        label: "Open document",
        onClick: () => navigateToDocument(doc.id),
      })
    );
    actionsWrap.appendChild(
      createIconActionButton({
        icon: "file-text",
        label: "View file",
        onClick: () => openDocumentFile(doc.id),
      })
    );
    actionCell.appendChild(actionsWrap);

    row.appendChild(titleCell);
    row.appendChild(typeCell);
    row.appendChild(correspondentCell);
    row.appendChild(tagsCell);
    row.appendChild(dateCell);
    row.appendChild(statusCell);
    row.appendChild(actionCell);
    docsTableBody.appendChild(row);
  }
}

function renderTagsList(tagStats) {
  if (!tagStats.length) {
    tagsTableBody.innerHTML = '<tr><td colspan="3">No tags found.</td></tr>';
    return;
  }
  tagsTableBody.innerHTML = "";
  for (const stat of tagStats) {
    const row = document.createElement("tr");
    const tagCell = document.createElement("td");
    tagCell.setAttribute("data-label", "Tag");
    tagCell.textContent = stat.tag;
    const countCell = document.createElement("td");
    countCell.setAttribute("data-label", "Documents");
    countCell.textContent = String(stat.document_count);
    const actionCell = document.createElement("td");
    actionCell.setAttribute("data-label", "Action");

    const viewBtn = document.createElement("button");
    viewBtn.className = "btn";
    viewBtn.type = "button";
    viewBtn.textContent = "View Docs";
    viewBtn.addEventListener("click", async () => {
      docsFilters.tag = [stat.tag];
      docsFilters.correspondent = [];
      docsFilters.document_type = [];
      docsFilters.status = [];
      applyFiltersToControls();
      setActiveView("section-docs");
      setActiveNav("section-docs");
      syncUrlFromFilters();
      await loadDocumentsList();
      logActivity(`Filtered documents by tag: ${stat.tag}`);
    });

    actionCell.appendChild(viewBtn);
    row.appendChild(tagCell);
    row.appendChild(countCell);
    row.appendChild(actionCell);
    tagsTableBody.appendChild(row);
  }
}

function renderPendingList(documents) {
  if (!documents.length) {
    pendingTableBody.innerHTML = '<tr><td colspan="4">No pending documents.</td></tr>';
    return;
  }
  pendingTableBody.innerHTML = "";
  for (const doc of documents) {
    const row = document.createElement("tr");

    const titleCell = document.createElement("td");
    titleCell.setAttribute("data-label", "Title");
    const titleButton = document.createElement("button");
    titleButton.className = "link-button";
    titleButton.type = "button";
    titleButton.textContent = getSuggestedTitle(doc);
    titleButton.addEventListener("click", () => {
      navigateToDocument(doc.id);
    });
    titleCell.appendChild(titleButton);

    const statusCell = document.createElement("td");
    statusCell.setAttribute("data-label", "Status");
    statusCell.textContent = formatStatus(doc.status);
    const createdCell = document.createElement("td");
    createdCell.setAttribute("data-label", "Created");
    createdCell.textContent = new Date(doc.created_at).toLocaleString();
    const actionCell = document.createElement("td");
    actionCell.setAttribute("data-label", "Action");

    const button = document.createElement("button");
    button.className = "btn";
    button.type = "button";
    button.textContent = "Open";
    button.addEventListener("click", () => {
      navigateToDocument(doc.id);
    });
    actionCell.appendChild(button);

    row.appendChild(titleCell);
    row.appendChild(statusCell);
    row.appendChild(createdCell);
    row.appendChild(actionCell);
    pendingTableBody.appendChild(row);
  }
}

function setRestartPendingButtonEnabled(enabled) {
  if (!restartPendingBtn) {
    return;
  }
  restartPendingBtn.disabled = !enabled;
}

async function loadDocumentsList() {
  const query = new URLSearchParams({ limit: "200" });
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

  const response = await fetch(`/documents?${query.toString()}`);
  const payload = await response.json();
  if (!response.ok) {
    logActivity(`Document list failed: ${payload.detail || response.statusText}`);
    return;
  }
  renderDocsList(payload);
  refreshFilterOptionsFromDocuments(payload);
  logActivity(`Loaded ${payload.length} document(s)`);
}

async function loadPendingDocuments() {
  const response = await fetch("/documents/pending?limit=200");
  const payload = await response.json();
  if (!response.ok) {
    setRestartPendingButtonEnabled(false);
    logActivity(`Pending list failed: ${payload.detail || response.statusText}`);
    return;
  }
  renderPendingList(payload);
  setRestartPendingButtonEnabled(payload.length > 0);
  logActivity(`Loaded ${payload.length} pending document(s)`);
}

async function loadTagStats() {
  const response = await fetch("/documents/metadata/tag-stats");
  const payload = await response.json();
  if (!response.ok) {
    logActivity(`Tag stats load failed: ${payload.detail || response.statusText}`);
    return;
  }
  renderTagsList(payload);
  logActivity(`Loaded ${payload.length} tag(s)`);
}

async function openDocumentView(documentId) {
  const response = await fetch(`/documents/${documentId}/detail`);
  const payload = await response.json();
  if (!response.ok) {
    throw new Error(payload.detail || "Failed to load document detail");
  }

  const doc = payload.document;
  const metadata = payload.llm_metadata;
  currentDocumentId = doc.id;

  metaTitleInput.value = metadata?.suggested_title || doc.filename;
  metaDateInput.value = metadata?.document_date || "";
  metaCorrespondentInput.value = metadata?.correspondent || "";
  metaTypeInput.value = metadata?.document_type || "";
  metaTagsInput.value = metadata?.tags?.join(", ") || "";
  detailDocId.textContent = doc.id || "-";
  detailOwnerId.textContent = doc.owner_id || "-";
  detailFilename.textContent = doc.filename || "-";
  detailStatus.textContent = formatStatus(doc.status);
  detailCreatedAt.textContent = doc.created_at
    ? new Date(doc.created_at).toLocaleString()
    : "-";
  detailContentType.textContent = doc.content_type || "-";
  detailSizeBytes.textContent = `${formatBytes(doc.size_bytes)} (${doc.size_bytes || 0} bytes)`;
  detailChecksum.textContent = doc.checksum_sha256 || "-";
  detailBlobUri.textContent = toRelativeBlobPath(doc.blob_uri);
  detailBlobUri.title = doc.blob_uri || "";

  const historyResponse = await fetch(`/documents/${documentId}/history?limit=100`);
  const historyPayload = await historyResponse.json();
  if (!historyResponse.ok) {
    renderDocumentHistory([]);
    logActivity(`History load failed: ${historyPayload.detail || historyResponse.statusText}`);
  } else {
    renderDocumentHistory(historyPayload);
  }

  setActiveView("section-document");
  setActiveNav("section-document");
  syncUrlFromFilters();
  logActivity(`Opened document ${documentId}`);
}

async function waitForDocumentReady(documentId, timeoutMs = 45000, intervalMs = 1500) {
  const deadline = Date.now() + timeoutMs;
  while (Date.now() < deadline) {
    const response = await fetch(`/documents/${documentId}`);
    const payload = await response.json();
    if (!response.ok) {
      throw new Error(payload.detail || "Failed to refresh document status");
    }
    if (payload.status === "ready") {
      return true;
    }
    await delay(intervalMs);
  }
  return false;
}

uploadForm.addEventListener("submit", async (event) => {
  event.preventDefault();

  const ownerId = document.getElementById("ownerId").value.trim();
  const fileInput = document.getElementById("fileInput");
  const file = fileInput.files && fileInput.files[0];
  if (!ownerId || !file) {
    logActivity("Upload blocked: owner_id and file are required.");
    return;
  }

  const form = new FormData();
  form.append("owner_id", ownerId);
  form.append("file", file);

  logActivity(`Uploading ${file.name}...`);
  const response = await fetch("/documents", { method: "POST", body: form });
  const payload = await response.json();
  if (!response.ok) {
    logActivity(`Upload failed: ${payload.detail || response.statusText}`);
    return;
  }

  logActivity(`Uploaded ${file.name} => document ${payload.id}`);
  navigateToDocument(payload.id);
});

documentMetaForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  if (!currentDocumentId) {
    logActivity("No document selected.");
    return;
  }

  const response = await fetch(`/documents/${currentDocumentId}/metadata`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      suggested_title: metaTitleInput.value.trim(),
      document_date: metaDateInput.value || null,
      correspondent: metaCorrespondentInput.value.trim(),
      document_type: metaTypeInput.value.trim(),
      tags: splitTags(metaTagsInput.value),
    }),
  });
  const payload = await response.json();
  if (!response.ok) {
    logActivity(`Metadata save failed: ${payload.detail || response.statusText}`);
    return;
  }

  logActivity(`Saved metadata for ${currentDocumentId}`);
  await openDocumentView(currentDocumentId);
  await loadDocumentsList();
  await loadPendingDocuments();
  await loadTagStats();
});

reprocessDocumentBtn?.addEventListener("click", async () => {
  if (!currentDocumentId) {
    logActivity("No document selected.");
    return;
  }

  const response = await fetch(`/documents/${currentDocumentId}/reprocess`, {
    method: "POST",
  });
  const payload = await response.json();
  if (!response.ok) {
    logActivity(`Reprocess failed: ${payload.detail || response.statusText}`);
    return;
  }

  logActivity(
    `Reprocessing queued for ${currentDocumentId} (job ${payload.job_id}).`
  );
  await openDocumentView(currentDocumentId);
  await loadDocumentsList();
  await loadPendingDocuments();
  const completed = await waitForDocumentReady(currentDocumentId);
  if (completed) {
    logActivity(`Reprocessing completed for ${currentDocumentId}.`);
    await openDocumentView(currentDocumentId);
    await loadDocumentsList();
    await loadPendingDocuments();
    await loadTagStats();
  } else {
    logActivity(`Reprocessing still running for ${currentDocumentId}. Refresh to check later.`);
  }
});

viewDocumentFileBtn?.addEventListener("click", () => {
  if (!currentDocumentId) {
    logActivity("No document selected.");
    return;
  }
  openDocumentFile(currentDocumentId);
});

backToDocsBtn.addEventListener("click", () => {
  const url = new URL("/ui/documents", window.location.origin);
  window.location.href = `${url.pathname}?${url.searchParams.toString()}`;
});

docsFilterForm.addEventListener("submit", (event) => {
  event.preventDefault();
});

for (const selectEl of filterSelects) {
  selectEl.addEventListener("change", async () => {
    await applyFiltersFromControls();
  });
}

for (const selectEl of filterSelects) {
  setupFilterDropdown(selectEl);
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

clearFiltersBtn.addEventListener("click", async () => {
  docsFilters.tag = [];
  docsFilters.correspondent = [];
  docsFilters.document_type = [];
  docsFilters.status = ["ready"];
  applyFiltersToControls();
  syncUrlFromFilters();
  await loadDocumentsList();
});

restartPendingBtn?.addEventListener("click", async () => {
  if (restartPendingBtn.disabled) {
    return;
  }
  const confirmed = window.confirm(
    "Restart analysis for all documents that are not ready?"
  );
  if (!confirmed) {
    return;
  }

  const response = await fetch("/documents/pending/restart?limit=200", {
    method: "POST",
  });
  const payload = await response.json();
  if (!response.ok) {
    logActivity(`Restart failed: ${payload.detail || response.statusText}`);
    return;
  }

  logActivity(
    `Restarted ${payload.restarted_count} pending document(s). ` +
      `${payload.skipped_ready_count} ready document(s) skipped.`
  );
  await loadPendingDocuments();
  await loadDocumentsList();
});

window.addEventListener("popstate", async () => {
  readFiltersFromUrl();
  applyFiltersToControls();
  setActiveView(currentViewId);
  setActiveNav(currentViewId);
  if (currentViewId === "section-tags") {
    await loadTagStats();
    return;
  }
  if (currentViewId === "section-pending") {
    await loadPendingDocuments();
    return;
  }
  if (currentViewId === "section-document" && currentDocumentId) {
    await openDocumentView(currentDocumentId);
    return;
  }
  await loadDocumentsList();
});

readFiltersFromUrl();
applyFiltersToControls();
setActiveView(currentViewId);
setActiveNav(currentViewId);

if (currentViewId === "section-docs") {
  loadDocumentsList().catch((error) => {
    logActivity(`Initial document list failed: ${error.message}`);
  });
}

if (currentViewId === "section-tags") {
  loadTagStats().catch((error) => {
    logActivity(`Initial tag stats failed: ${error.message}`);
  });
}

if (currentViewId === "section-pending") {
  loadPendingDocuments().catch((error) => {
    logActivity(`Initial pending list failed: ${error.message}`);
  });
}

if (currentViewId === "section-document") {
  const docId = new URLSearchParams(window.location.search).get("id");
  if (docId) {
    openDocumentView(docId).catch((error) => {
      logActivity(`Initial document detail failed: ${error.message}`);
    });
  }
}
