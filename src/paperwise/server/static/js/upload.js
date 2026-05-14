import {
  apiFetch,
} from "paperwise/shared";
import {
  logActivity,
  navigateToDocument,
} from "paperwise/app";
import { getLlmUploadBlockReason } from "./state/llm.js";

let uploadInProgress = false;
let uploadSelectionContext = { source: "files", folderName: "" };
let uploadEventsBound = false;

function getUploadElements() {
  return {
    uploadForm: document.getElementById("uploadForm"),
    fileInput: document.getElementById("fileInput"),
    folderInput: document.getElementById("folderInput"),
    uploadFolderBtn: document.getElementById("uploadFolderBtn"),
    uploadDropzone: document.getElementById("uploadDropzone"),
    uploadSelectionLabel: document.getElementById("uploadSelectionLabel"),
    uploadSubmitBtn: document.getElementById("uploadSubmitBtn"),
    uploadProgressWrap: document.getElementById("uploadProgressWrap"),
    uploadProgressBar: document.getElementById("uploadProgressBar"),
    uploadProgressStatus: document.getElementById("uploadProgressStatus"),
  };
}

const SUPPORTED_UPLOAD_LABEL = "Supports: PDF, TXT, MD, DOCX, DOC, PNG, JPG, WEBP, GIF";
const SUPPORTED_UPLOAD_EXTENSIONS = new Set([
  ".pdf",
  ".txt",
  ".md",
  ".markdown",
  ".doc",
  ".docx",
  ".png",
  ".jpg",
  ".jpeg",
  ".webp",
  ".gif",
]);
const SUPPORTED_UPLOAD_MIME_TYPES = new Set([
  "application/msword",
  "application/octet-stream",
  "application/pdf",
  "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
  "image/gif",
  "image/jpeg",
  "image/png",
  "image/webp",
  "text/markdown",
  "text/plain",
]);

function isSupportedUploadFile(file) {
  const name = (file?.name || "").toLowerCase();
  const ext = name.includes(".") ? `.${name.split(".").pop()}` : "";
  const type = String(file?.type || "").split(";")[0].trim().toLowerCase();
  return SUPPORTED_UPLOAD_EXTENSIONS.has(ext) || SUPPORTED_UPLOAD_MIME_TYPES.has(type);
}

function collectSupportedFiles(fileList) {
  return [...(fileList || [])].filter((file) => isSupportedUploadFile(file));
}

function getFolderNameFromFiles(files) {
  for (const file of files || []) {
    const relativePath = String(file?.webkitRelativePath || "").trim();
    if (!relativePath) {
      continue;
    }
    const folderName = relativePath.split("/")[0]?.trim();
    if (folderName) {
      return folderName;
    }
  }
  return "";
}

async function collectFilesFromDirectoryHandle(directoryHandle) {
  const files = [];

  async function visit(handle) {
    for await (const entry of handle.values()) {
      if (entry.kind === "file") {
        files.push(await entry.getFile());
        continue;
      }
      if (entry.kind === "directory") {
        await visit(entry);
      }
    }
  }

  await visit(directoryHandle);
  return files;
}

function applyFolderSelection(selectedFiles, folderName = "") {
  const supportedFiles = collectSupportedFiles(selectedFiles);
  const ignoredCount = selectedFiles.length - supportedFiles.length;

  if (!supportedFiles.length) {
    setSelectedFiles([], { source: "folder", folderName });
    if (selectedFiles.length) {
      logActivity("Folder selection ignored: no supported files were found.");
    }
    return;
  }

  setSelectedFiles(supportedFiles, { source: "folder", folderName });
  if (ignoredCount > 0) {
    logActivity(`Folder selection skipped ${ignoredCount} unsupported file(s).`);
  }
  logActivity(`Ready to upload ${supportedFiles.length} file(s) from folder selection.`);
}

function updateSelectedFilesLabel() {
  const { fileInput, uploadSelectionLabel } = getUploadElements();
  if (!uploadSelectionLabel || !fileInput) {
    return;
  }
  const files = fileInput.files ? [...fileInput.files] : [];
  if (!files.length) {
    uploadSelectionLabel.textContent = SUPPORTED_UPLOAD_LABEL;
    return;
  }
  if (files.length === 1) {
    uploadSelectionLabel.textContent = `Selected: ${files[0].name}`;
    return;
  }
  if (uploadSelectionContext.source === "folder" && uploadSelectionContext.folderName) {
    uploadSelectionLabel.textContent = `Selected ${files.length} files from ${uploadSelectionContext.folderName}`;
    return;
  }
  uploadSelectionLabel.textContent = `Selected ${files.length} files`;
}

function hideUploadProgress() {
  const { uploadProgressWrap, uploadProgressBar, uploadProgressStatus } = getUploadElements();
  if (uploadProgressWrap) {
    uploadProgressWrap.hidden = true;
  }
  if (uploadProgressBar) {
    uploadProgressBar.max = 1;
    uploadProgressBar.value = 0;
  }
  if (uploadProgressStatus) {
    uploadProgressStatus.textContent = "Ready.";
  }
}

function showUploadProgress(processed, total, message) {
  const { uploadProgressWrap, uploadProgressBar, uploadProgressStatus } = getUploadElements();
  if (!uploadProgressWrap || !uploadProgressBar || !uploadProgressStatus) {
    return;
  }
  uploadProgressWrap.hidden = false;
  uploadProgressBar.max = Math.max(total, 1);
  uploadProgressBar.value = Math.max(0, Math.min(processed, total));
  uploadProgressStatus.textContent = message;
}

function syncUploadProgressFromSelection() {
  const { fileInput } = getUploadElements();
  if (!fileInput || uploadInProgress) {
    return;
  }
  const files = fileInput.files ? [...fileInput.files] : [];
  if (files.length <= 1) {
    hideUploadProgress();
    return;
  }
  showUploadProgress(0, files.length, `Ready to upload ${files.length} files.`);
}

function setSelectedFiles(files, options = {}) {
  const { fileInput } = getUploadElements();
  if (!fileInput) {
    return;
  }
  const data = new DataTransfer();
  for (const file of files) {
    data.items.add(file);
  }
  fileInput.files = data.files;
  uploadSelectionContext = {
    source: options.source === "folder" ? "folder" : "files",
    folderName: String(options.folderName || "").trim(),
  };
  updateSelectedFilesLabel();
  syncUploadProgressFromSelection();
}

async function uploadDocumentFile(file) {
  const form = new FormData();
  form.append("file", file);
  if (Number.isFinite(file?.lastModified) && file.lastModified > 0) {
    form.append("source_last_modified_ms", String(file.lastModified));
    form.append("source_last_modified_at", new Date(file.lastModified).toISOString());
  }
  const response = await apiFetch("/documents", { method: "POST", body: form });
  const payload = await response.json();
  if (!response.ok) {
    throw new Error(payload.detail || response.statusText);
  }
  return payload;
}

export function syncUploadAvailability(options = {}) {
  const {
    fileInput,
    folderInput,
    uploadFolderBtn,
    uploadDropzone,
    uploadSelectionLabel,
    uploadSubmitBtn,
  } = getUploadElements();
  const announce = options.announce === true;
  const navigateToSettings = options.navigateToSettings === true;
  const reason = getLlmUploadBlockReason();
  const blocked = Boolean(reason);

  if (uploadSubmitBtn) {
    uploadSubmitBtn.disabled = blocked;
  }
  if (fileInput) {
    fileInput.disabled = blocked;
  }
  if (folderInput) {
    folderInput.disabled = blocked;
  }
  if (uploadFolderBtn) {
    uploadFolderBtn.disabled = blocked;
  }
  if (uploadDropzone) {
    uploadDropzone.classList.toggle("is-disabled", blocked);
    uploadDropzone.setAttribute("aria-disabled", blocked ? "true" : "false");
    uploadDropzone.tabIndex = blocked ? -1 : 0;
  }

  if (blocked) {
    if (uploadSelectionLabel) {
      uploadSelectionLabel.textContent = "Upload disabled: update LLM settings first.";
    }
    if (announce) {
      logActivity(`Upload blocked: ${reason} Go to Settings first.`);
    }
    if (navigateToSettings) {
      window.location.href = "/ui/settings/models";
    }
    return false;
  }

  updateSelectedFilesLabel();
  return true;
}

function bindUploadEvents() {
  if (uploadEventsBound) {
    return;
  }
  const {
    uploadForm,
    fileInput,
    folderInput,
    uploadFolderBtn,
    uploadDropzone,
    uploadSubmitBtn,
  } = getUploadElements();

  uploadForm?.addEventListener("submit", async (event) => {
    event.preventDefault();
    if (!syncUploadAvailability({ announce: true, navigateToSettings: true })) {
      return;
    }

    const files = collectSupportedFiles(fileInput?.files || []);
    if (!files.length) {
      logActivity("Upload blocked: select at least one supported document or image file.");
      return;
    }

    const uploadedIds = [];
    let failedUploads = 0;
    uploadInProgress = true;
    if (uploadSubmitBtn) {
      uploadSubmitBtn.disabled = true;
    }
    if (fileInput) {
      fileInput.disabled = true;
    }
    if (folderInput) {
      folderInput.disabled = true;
    }
    if (uploadFolderBtn) {
      uploadFolderBtn.disabled = true;
    }
    if (uploadDropzone) {
      uploadDropzone.classList.add("is-disabled");
      uploadDropzone.setAttribute("aria-disabled", "true");
      uploadDropzone.tabIndex = -1;
    }
    if (files.length > 1) {
      showUploadProgress(0, files.length, `Uploading 0 of ${files.length} files...`);
    }
    try {
      for (const [index, file] of files.entries()) {
        logActivity(`Uploading ${file.name}...`);
        try {
          const payload = await uploadDocumentFile(file);
          uploadedIds.push(payload.id);
          logActivity(`Uploaded ${file.name} => document ${payload.id}`);
        } catch (error) {
          failedUploads += 1;
          logActivity(`Upload failed for ${file.name}: ${error.message}`);
        }
        if (files.length > 1) {
          const processed = index + 1;
          const message =
            failedUploads > 0
              ? `Uploading ${processed} of ${files.length} files... ${failedUploads} failed so far.`
              : `Uploading ${processed} of ${files.length} files...`;
          showUploadProgress(processed, files.length, message);
        }
      }
    } finally {
      uploadInProgress = false;
      syncUploadAvailability();
    }

    updateSelectedFilesLabel();
    if (files.length > 1) {
      const successCount = uploadedIds.length;
      const summary =
        failedUploads > 0
          ? `Finished ${successCount} of ${files.length} files. ${failedUploads} failed.`
          : `Finished uploading ${files.length} files.`;
      showUploadProgress(files.length, files.length, summary);
    }
    if (!uploadedIds.length) {
      return;
    }
    if (uploadedIds.length === 1) {
      navigateToDocument(uploadedIds[0]);
      return;
    }
    logActivity(`Uploaded ${uploadedIds.length} files.`);
    window.location.href = "/ui/documents";
  });

  fileInput?.addEventListener("change", () => {
    uploadSelectionContext = { source: "files", folderName: "" };
    updateSelectedFilesLabel();
    syncUploadProgressFromSelection();
  });

  folderInput?.addEventListener("change", () => {
    const selectedFiles = [...(folderInput.files || [])];
    const folderName = getFolderNameFromFiles(selectedFiles);
    applyFolderSelection(selectedFiles, folderName);
    folderInput.value = "";
  });

  uploadFolderBtn?.addEventListener("click", async () => {
    if (!syncUploadAvailability({ announce: true, navigateToSettings: true })) {
      return;
    }
    if (typeof window.showDirectoryPicker === "function") {
      try {
        const directoryHandle = await window.showDirectoryPicker();
        const selectedFiles = await collectFilesFromDirectoryHandle(directoryHandle);
        applyFolderSelection(selectedFiles, directoryHandle.name || "");
        return;
      } catch (error) {
        if (error?.name === "AbortError") {
          return;
        }
        logActivity("Directory picker unavailable in this browser context. Falling back to file input.");
      }
    }
    folderInput?.click();
  });

  uploadDropzone?.addEventListener("click", (event) => {
    if (!syncUploadAvailability({ announce: true, navigateToSettings: true })) {
      return;
    }
    if (event.target === fileInput) {
      return;
    }
    fileInput?.click();
  });

  uploadDropzone?.addEventListener("keydown", (event) => {
    if (!syncUploadAvailability({ announce: true, navigateToSettings: true })) {
      return;
    }
    if (event.key !== "Enter" && event.key !== " ") {
      return;
    }
    event.preventDefault();
    fileInput?.click();
  });

  ["dragenter", "dragover"].forEach((eventName) => {
    uploadDropzone?.addEventListener(eventName, (event) => {
      if (!syncUploadAvailability()) {
        return;
      }
      event.preventDefault();
      uploadDropzone.classList.add("is-drag-over");
    });
  });

  ["dragleave", "drop"].forEach((eventName) => {
    uploadDropzone?.addEventListener(eventName, (event) => {
      event.preventDefault();
      uploadDropzone.classList.remove("is-drag-over");
    });
  });

  uploadDropzone?.addEventListener("drop", (event) => {
    if (!syncUploadAvailability({ announce: true, navigateToSettings: true })) {
      return;
    }
    const dropped = collectSupportedFiles(event.dataTransfer?.files || []);
    if (!dropped.length) {
      logActivity("Drop ignored: only supported document and image types are accepted.");
      return;
    }
    setSelectedFiles(dropped);
    logActivity(`Ready to upload ${dropped.length} file(s).`);
  });

  uploadEventsBound = true;
}

export async function initializePage({ authenticated }) {
  if (authenticated !== true) {
    return;
  }
  bindUploadEvents();
  syncUploadAvailability();
}
