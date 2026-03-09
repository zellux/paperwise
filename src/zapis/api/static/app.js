const uploadForm = document.getElementById("uploadForm");
const docLookupForm = document.getElementById("docLookupForm");
const parseNowBtn = document.getElementById("parseNowBtn");
const parseFetchBtn = document.getElementById("parseFetchBtn");

const docIdInput = document.getElementById("docIdInput");
const docOutput = document.getElementById("docOutput");
const parseOutput = document.getElementById("parseOutput");
const activityOutput = document.getElementById("activityOutput");

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

