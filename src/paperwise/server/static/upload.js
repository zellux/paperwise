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
