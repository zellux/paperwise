const uploadForm = document.getElementById("uploadForm");
const documentMetaForm = document.getElementById("documentMetaForm");
const backToDocsBtn = document.getElementById("backToDocsBtn");
const docsFilterForm = document.getElementById("docsFilterForm");
const clearFiltersBtn = document.getElementById("clearFiltersBtn");

const metaTitleInput = document.getElementById("metaTitle");
const metaDateInput = document.getElementById("metaDate");
const metaCorrespondentInput = document.getElementById("metaCorrespondent");
const metaTypeInput = document.getElementById("metaType");
const metaTagsInput = document.getElementById("metaTags");
const documentSummary = document.getElementById("documentSummary");
const filterTag = document.getElementById("filterTag");
const filterCorrespondent = document.getElementById("filterCorrespondent");
const filterType = document.getElementById("filterType");
const filterStatus = document.getElementById("filterStatus");

const activityOutput = document.getElementById("activityOutput");
const docsTableBody = document.getElementById("docsTableBody");
const tagsTableBody = document.getElementById("tagsTableBody");
const pendingTableBody = document.getElementById("pendingTableBody");
const navLinks = [...document.querySelectorAll(".nav-link")];
const views = [...document.querySelectorAll(".view")];

let currentDocumentId = "";
const docsFilters = {
  tag: "",
  correspondent: "",
  document_type: "",
  status: "",
};

function formatStatus(value) {
  if (!value) {
    return "-";
  }
  return value
    .split("_")
    .map((chunk) => chunk.charAt(0).toUpperCase() + chunk.slice(1))
    .join(" ");
}

function logActivity(message) {
  const now = new Date().toLocaleTimeString();
  activityOutput.textContent = `[${now}] ${message}\n${activityOutput.textContent}`;
}

function setActiveNav(targetId) {
  for (const link of navLinks) {
    link.classList.toggle("active", link.dataset.target === targetId);
  }
}

function setActiveView(targetId) {
  for (const view of views) {
    view.classList.toggle("view-hidden", view.id !== targetId);
  }
}

function splitTags(value) {
  return value
    .split(",")
    .map((part) => part.trim())
    .filter((part) => part.length > 0);
}

function setSelectOptions(selectEl, values, placeholderLabel) {
  const previous = selectEl.value;
  selectEl.innerHTML = "";
  const placeholder = document.createElement("option");
  placeholder.value = "";
  placeholder.textContent = placeholderLabel;
  selectEl.appendChild(placeholder);
  for (const value of values) {
    const option = document.createElement("option");
    option.value = value;
    option.textContent = value;
    selectEl.appendChild(option);
  }
  selectEl.value = values.includes(previous) ? previous : "";
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
    const titleButton = document.createElement("button");
    titleButton.className = "link-button";
    titleButton.type = "button";
    titleButton.textContent = suggestedTitle;
    titleButton.addEventListener("click", async () => {
      try {
        await openDocumentView(doc.id);
      } catch (error) {
        logActivity(error.message);
      }
    });
    titleCell.appendChild(titleButton);

    const typeCell = document.createElement("td");
    typeCell.textContent = documentType;
    const correspondentCell = document.createElement("td");
    correspondentCell.textContent = correspondent;
    const tagsCell = document.createElement("td");
    tagsCell.textContent = tags;
    const dateCell = document.createElement("td");
    dateCell.textContent = documentDate;
    const statusCell = document.createElement("td");
    statusCell.textContent = formatStatus(doc.status);

    const actionCell = document.createElement("td");
    const button = document.createElement("button");
    button.className = "btn";
    button.type = "button";
    button.textContent = "Open";
    button.addEventListener("click", async () => {
      try {
        await openDocumentView(doc.id);
      } catch (error) {
        logActivity(error.message);
      }
    });
    actionCell.appendChild(button);

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
    tagsTableBody.innerHTML = '<tr><td colspan="2">No tags found.</td></tr>';
    return;
  }
  tagsTableBody.innerHTML = "";
  for (const stat of tagStats) {
    const row = document.createElement("tr");
    const tagCell = document.createElement("td");
    tagCell.textContent = stat.tag;
    const countCell = document.createElement("td");
    countCell.textContent = String(stat.document_count);
    row.appendChild(tagCell);
    row.appendChild(countCell);
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
    const titleButton = document.createElement("button");
    titleButton.className = "link-button";
    titleButton.type = "button";
    titleButton.textContent = getSuggestedTitle(doc);
    titleButton.addEventListener("click", async () => {
      try {
        await openDocumentView(doc.id);
      } catch (error) {
        logActivity(error.message);
      }
    });
    titleCell.appendChild(titleButton);

    const statusCell = document.createElement("td");
    statusCell.textContent = formatStatus(doc.status);
    const createdCell = document.createElement("td");
    createdCell.textContent = new Date(doc.created_at).toLocaleString();
    const actionCell = document.createElement("td");

    const button = document.createElement("button");
    button.className = "btn";
    button.type = "button";
    button.textContent = "Open";
    button.addEventListener("click", async () => {
      try {
        await openDocumentView(doc.id);
      } catch (error) {
        logActivity(error.message);
      }
    });
    actionCell.appendChild(button);

    row.appendChild(titleCell);
    row.appendChild(statusCell);
    row.appendChild(createdCell);
    row.appendChild(actionCell);
    pendingTableBody.appendChild(row);
  }
}

async function loadDocumentsList() {
  const query = new URLSearchParams({ limit: "200" });
  if (docsFilters.tag) {
    query.set("tag", docsFilters.tag);
  }
  if (docsFilters.correspondent) {
    query.set("correspondent", docsFilters.correspondent);
  }
  if (docsFilters.document_type) {
    query.set("document_type", docsFilters.document_type);
  }
  if (docsFilters.status) {
    query.set("status", docsFilters.status);
  }

  const response = await fetch(`/documents?${query.toString()}`);
  const payload = await response.json();
  if (!response.ok) {
    logActivity(`Document list failed: ${payload.detail || response.statusText}`);
    return;
  }
  renderDocsList(payload);
  logActivity(`Loaded ${payload.length} document(s)`);
}

async function loadPendingDocuments() {
  const response = await fetch("/documents/pending?limit=200");
  const payload = await response.json();
  if (!response.ok) {
    logActivity(`Pending list failed: ${payload.detail || response.statusText}`);
    return;
  }
  renderPendingList(payload);
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

async function loadFilterOptions() {
  const response = await fetch("/documents/metadata/taxonomy");
  const payload = await response.json();
  if (!response.ok) {
    logActivity(`Filter options load failed: ${payload.detail || response.statusText}`);
    return;
  }
  setSelectOptions(filterTag, payload.tags || [], "All Tags");
  setSelectOptions(filterCorrespondent, payload.correspondents || [], "All Correspondents");
  setSelectOptions(filterType, payload.document_types || [], "All Types");
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

  documentSummary.textContent = `ID: ${doc.id} | File: ${doc.filename} | Status: ${formatStatus(doc.status)} | Created: ${new Date(doc.created_at).toLocaleString()}`;

  setActiveView("section-document");
  setActiveNav("section-document");
  logActivity(`Opened document ${documentId}`);
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
  await loadDocumentsList();
  await loadPendingDocuments();
  await loadTagStats();
  await loadFilterOptions();
  await openDocumentView(payload.id);
  logActivity("Automatic analysis queued (parse + LLM enrichment).");
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
  await loadFilterOptions();
});

backToDocsBtn.addEventListener("click", () => {
  setActiveView("section-docs");
  setActiveNav("section-docs");
});

docsFilterForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  docsFilters.tag = filterTag.value;
  docsFilters.correspondent = filterCorrespondent.value;
  docsFilters.document_type = filterType.value;
  docsFilters.status = filterStatus.value;
  await loadDocumentsList();
});

clearFiltersBtn.addEventListener("click", async () => {
  docsFilters.tag = "";
  docsFilters.correspondent = "";
  docsFilters.document_type = "";
  docsFilters.status = "";
  filterTag.value = "";
  filterCorrespondent.value = "";
  filterType.value = "";
  filterStatus.value = "";
  await loadDocumentsList();
});

for (const link of navLinks) {
  link.addEventListener("click", async () => {
    const targetId = link.dataset.target;
    const target = document.getElementById(targetId);
    if (!target) {
      return;
    }
    setActiveView(targetId);
    setActiveNav(targetId);
    if (targetId === "section-docs") {
      await loadFilterOptions();
      await loadDocumentsList();
      return;
    }
    if (targetId === "section-tags") {
      await loadTagStats();
      return;
    }
    if (targetId === "section-pending") {
      await loadPendingDocuments();
      return;
    }
    if (targetId === "section-document" && currentDocumentId) {
      await openDocumentView(currentDocumentId);
    }
  });
}

setActiveView("section-docs");
setActiveNav("section-docs");

loadFilterOptions().catch((error) => {
  logActivity(`Initial filter options failed: ${error.message}`);
});

loadDocumentsList().catch((error) => {
  logActivity(`Initial document list failed: ${error.message}`);
});

loadTagStats().catch((error) => {
  logActivity(`Initial tag stats failed: ${error.message}`);
});

loadPendingDocuments().catch((error) => {
  logActivity(`Initial pending list failed: ${error.message}`);
});
