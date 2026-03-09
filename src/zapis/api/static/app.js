const uploadForm = document.getElementById("uploadForm");
const docLookupForm = document.getElementById("docLookupForm");
const parseNowBtn = document.getElementById("parseNowBtn");
const parseFetchBtn = document.getElementById("parseFetchBtn");
const llmParseBtn = document.getElementById("llmParseBtn");
const llmFetchBtn = document.getElementById("llmFetchBtn");
const taxonomyBtn = document.getElementById("taxonomyBtn");
const refreshDocsBtn = document.getElementById("refreshDocsBtn");

const docIdInput = document.getElementById("docIdInput");
const docOutput = document.getElementById("docOutput");
const parseOutput = document.getElementById("parseOutput");
const llmOutput = document.getElementById("llmOutput");
const activityOutput = document.getElementById("activityOutput");
const docsTableBody = document.getElementById("docsTableBody");
const navLinks = [...document.querySelectorAll(".nav-link")];
const views = [...document.querySelectorAll(".view")];

let currentDocumentId = "";

function pretty(data) {
  return JSON.stringify(data, null, 2);
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
    docsTableBody.innerHTML = '<tr><td colspan="8">No documents found.</td></tr>';
    return;
  }
  docsTableBody.innerHTML = "";
  for (const doc of documents) {
    const row = document.createElement("tr");
    const filenameCell = document.createElement("td");
    filenameCell.textContent = doc.filename;

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
    titleCell.textContent = suggestedTitle;
    const typeCell = document.createElement("td");
    typeCell.textContent = documentType;
    const correspondentCell = document.createElement("td");
    correspondentCell.textContent = correspondent;
    const tagsCell = document.createElement("td");
    tagsCell.textContent = tags;
    const dateCell = document.createElement("td");
    dateCell.textContent = documentDate;
    const statusCell = document.createElement("td");
    statusCell.textContent = doc.status;

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

    row.appendChild(filenameCell);
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
  parseOutput.textContent = "No parse result yet.";
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

parseNowBtn.addEventListener("click", async () => {
  const documentId = docIdInput.value.trim() || currentDocumentId;
  if (!documentId) {
    logActivity("Parse blocked: load or upload a document first.");
    return;
  }

  logActivity(`Parsing document ${documentId}...`);
  const response = await fetch(`/documents/${documentId}/parse`, { method: "POST" });
  const payload = await response.json();
  if (!response.ok) {
    logActivity(`Parse failed: ${payload.detail || response.statusText}`);
    return;
  }

  parseOutput.textContent = pretty(payload);
  logActivity(`Parse completed for ${documentId}`);
});

parseFetchBtn.addEventListener("click", async () => {
  const documentId = docIdInput.value.trim() || currentDocumentId;
  if (!documentId) {
    logActivity("Fetch blocked: load or upload a document first.");
    return;
  }

  const response = await fetch(`/documents/${documentId}/parse`);
  const payload = await response.json();
  if (!response.ok) {
    logActivity(`Fetch parse failed: ${payload.detail || response.statusText}`);
    return;
  }

  parseOutput.textContent = pretty(payload);
  logActivity(`Fetched parse result for ${documentId}`);
});

llmParseBtn.addEventListener("click", async () => {
  const documentId = docIdInput.value.trim() || currentDocumentId;
  if (!documentId) {
    logActivity("LLM parse blocked: load or upload a document first.");
    return;
  }

  const response = await fetch(`/documents/${documentId}/llm-parse`, { method: "POST" });
  const payload = await response.json();
  if (!response.ok) {
    logActivity(`LLM parse failed: ${payload.detail || response.statusText}`);
    return;
  }
  llmOutput.textContent = pretty(payload);
  logActivity(`LLM parse completed for ${documentId}`);
});

llmFetchBtn.addEventListener("click", async () => {
  const documentId = docIdInput.value.trim() || currentDocumentId;
  if (!documentId) {
    logActivity("LLM fetch blocked: load or upload a document first.");
    return;
  }
  const response = await fetch(`/documents/${documentId}/llm-parse`);
  const payload = await response.json();
  if (!response.ok) {
    logActivity(`LLM fetch failed: ${payload.detail || response.statusText}`);
    return;
  }
  llmOutput.textContent = pretty(payload);
  logActivity(`Fetched LLM parse result for ${documentId}`);
});

taxonomyBtn.addEventListener("click", async () => {
  const response = await fetch("/documents/metadata/taxonomy");
  const payload = await response.json();
  if (!response.ok) {
    logActivity(`Taxonomy load failed: ${payload.detail || response.statusText}`);
    return;
  }
  llmOutput.textContent = pretty(payload);
  logActivity("Loaded current taxonomy");
});

refreshDocsBtn.addEventListener("click", async () => {
  await loadDocumentsList();
});

for (const link of navLinks) {
  link.addEventListener("click", () => {
    const targetId = link.dataset.target;
    const target = document.getElementById(targetId);
    if (!target) {
      return;
    }
    setActiveView(targetId);
    setActiveNav(targetId);
  });
}

setActiveView("section-docs");

loadDocumentsList().catch((error) => {
  logActivity(`Initial document list failed: ${error.message}`);
});
