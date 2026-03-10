const uploadForm = document.getElementById("uploadForm");
const docLookupForm = document.getElementById("docLookupForm");

const docIdInput = document.getElementById("docIdInput");
const docOutput = document.getElementById("docOutput");
const activityOutput = document.getElementById("activityOutput");
const docsTableBody = document.getElementById("docsTableBody");
const tagsTableBody = document.getElementById("tagsTableBody");
const pendingTableBody = document.getElementById("pendingTableBody");
const navLinks = [...document.querySelectorAll(".nav-link")];
const views = [...document.querySelectorAll(".view")];

let currentDocumentId = "";

function pretty(data) {
  return JSON.stringify(data, null, 2);
}

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

async function loadDocument(documentId) {
  const response = await fetch(`/documents/${documentId}`);
  const payload = await response.json();
  if (!response.ok) {
    throw new Error(payload.detail || "Failed to load document");
  }
  docOutput.textContent = pretty(payload);
  currentDocumentId = documentId;
  docIdInput.value = documentId;
  logActivity(`Loaded document ${documentId}`);
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
        await loadDocument(doc.id);
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
        await loadDocument(doc.id);
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

function getSuggestedTitle(doc) {
  if (doc.llm_metadata && doc.llm_metadata.suggested_title) {
    return doc.llm_metadata.suggested_title;
  }
  return "(Pending title)";
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
    titleCell.textContent = getSuggestedTitle(doc);
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
        await loadDocument(doc.id);
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

async function loadDocumentsList() {
  const response = await fetch("/documents?limit=200");
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
  await loadDocument(payload.id);
  await loadDocumentsList();
  await loadPendingDocuments();
  await loadTagStats();
  logActivity("Automatic analysis queued (parse + LLM enrichment).");
});

docLookupForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  const documentId = docIdInput.value.trim();
  if (!documentId) {
    return;
  }

  try {
    await loadDocument(documentId);
  } catch (error) {
    logActivity(error.message);
  }
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
      await loadDocumentsList();
      return;
    }
    if (targetId === "section-tags") {
      await loadTagStats();
      return;
    }
    if (targetId === "section-pending") {
      await loadPendingDocuments();
    }
  });
}

setActiveView("section-docs");

loadDocumentsList().catch((error) => {
  logActivity(`Initial document list failed: ${error.message}`);
});

loadTagStats().catch((error) => {
  logActivity(`Initial tag stats failed: ${error.message}`);
});

loadPendingDocuments().catch((error) => {
  logActivity(`Initial pending list failed: ${error.message}`);
});
