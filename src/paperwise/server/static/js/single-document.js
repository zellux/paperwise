import {
  apiFetch,
} from "paperwise/shared";
import {
  appState,
  deleteDocumentById,
  logActivity,
  openDocumentFile,
  openDocumentView,
  waitForDocumentReady,
} from "paperwise/app";
import { stableTagColor } from "./ui/tagColor.js";
import { splitTags } from "./ui/values.js";

let singleDocumentEventsBound = false;
let documentMetadataDirty = false;
let pdfDocument = null;
let pdfDocumentUrl = "";
let pdfjsPromise = null;
let pdfRenderTask = null;
let pdfRenderSerial = 0;
let pdfScaleMode = "fit";
let pdfManualScale = 1;
let pdfResizeObserver = null;
const PDFJS_MODULE_URL = "/static/vendor/pdfjs/pdf.min.mjs";
const PDFJS_WORKER_URL = "/static/vendor/pdfjs/pdf.worker.min.mjs";
const PDFJS_CMAP_URL = "/static/vendor/pdfjs/cmaps/";
const PDFJS_ICC_URL = "/static/vendor/pdfjs/iccs/";
const PDFJS_STANDARD_FONT_URL = "/static/vendor/pdfjs/standard_fonts/";
const PDFJS_WASM_URL = "/static/vendor/pdfjs/wasm/";
const TAG_SUGGESTIONS = [
  "Finance",
  "Credit Reports",
  "Identity",
  "Statements",
  "Investments",
  "Tax docs",
  "Insurance",
  "Medical records",
  "Utilities",
  "Lease & deeds",
  "Repairs & receipts",
  "Contracts",
  "Payslips",
  "Passport & ID",
];

function getSingleDocumentElements() {
  return {
    documentMetaForm: document.getElementById("documentMetaForm"),
    backToDocsBtn: document.getElementById("backToDocsBtn"),
    reprocessDocumentBtn: document.getElementById("reprocessDocumentBtn"),
    deleteDocumentBtn: document.getElementById("deleteDocumentBtn"),
    starDocumentBtn: document.getElementById("starDocumentBtn"),
    viewDocumentFileBtn: document.getElementById("viewDocumentFileBtn"),
    metaTitleInput: document.getElementById("metaTitle"),
    metaDateInput: document.getElementById("metaDate"),
    metaCorrespondentInput: document.getElementById("metaCorrespondent"),
    metaTypeInput: document.getElementById("metaType"),
    metaTagsInput: document.getElementById("metaTags"),
    metaTagEditor: document.getElementById("metaTagEditor"),
    metaTagChips: document.getElementById("metaTagChips"),
    metaTagQuery: document.getElementById("metaTagQuery"),
    metaTagSuggestions: document.getElementById("metaTagSuggestions"),
    detailOcrContent: document.getElementById("detailOcrContent"),
    detailOcrLines: document.getElementById("detailOcrLines"),
    detailOcrSearch: document.getElementById("detailOcrSearch"),
    detailOcrCopyBtn: document.getElementById("detailOcrCopyBtn"),
    detailFilename: document.getElementById("detailFilename"),
    documentPreviewFrame: document.getElementById("documentPreviewFrame"),
    detailImagePreview: document.getElementById("detailImagePreview"),
    detailEmbedPreview: document.getElementById("detailEmbedPreview"),
    detailPdfPreview: document.getElementById("detailPdfPreview"),
    detailPdfCanvas: document.getElementById("detailPdfCanvas"),
    detailPdfStatus: document.getElementById("detailPdfStatus"),
    pageStrip: document.getElementById("pageStrip"),
    previewCurrentPage: document.getElementById("previewCurrentPage"),
    previewTotalPages: document.getElementById("previewTotalPages"),
    previewPrevPageBtn: document.getElementById("previewPrevPageBtn"),
    previewNextPageBtn: document.getElementById("previewNextPageBtn"),
    previewZoomOutBtn: document.getElementById("previewZoomOutBtn"),
    previewZoomInBtn: document.getElementById("previewZoomInBtn"),
    previewFitWidthBtn: document.getElementById("previewFitWidthBtn"),
    previewZoomText: document.getElementById("previewZoomText"),
  };
}

async function refreshDocumentRelatedLists(options = {}) {
  void options;
}

function hydrateInitialDocumentData(initialData) {
  const detail = initialData.document_detail;
  const documentId = String(detail?.document?.id || "").trim();
  if (initialData.authenticated !== true || !documentId) {
    return false;
  }
  appState.currentDocumentId = documentId;
  logActivity(`Opened document ${appState.currentDocumentId}`);
  return true;
}

function renderDocumentStarButton(starred) {
  const { starDocumentBtn } = getSingleDocumentElements();
  if (!(starDocumentBtn instanceof HTMLButtonElement)) {
    return;
  }
  const isStarred = Boolean(starred);
  starDocumentBtn.classList.toggle("is-starred", isStarred);
  starDocumentBtn.setAttribute("aria-pressed", isStarred ? "true" : "false");
  starDocumentBtn.title = isStarred ? "Unstar document" : "Star document";
  const label = starDocumentBtn.querySelector("span");
  if (label) {
    label.textContent = isStarred ? "Starred" : "Star";
  }
  const icon = starDocumentBtn.querySelector("svg");
  if (icon) {
    icon.setAttribute("fill", isStarred ? "currentColor" : "none");
  }
}

function getDetailTags() {
  const { metaTagsInput } = getSingleDocumentElements();
  return splitTags(metaTagsInput?.value || "");
}

function setDetailTags(tags) {
  const { metaTagsInput } = getSingleDocumentElements();
  if (metaTagsInput instanceof HTMLInputElement) {
    metaTagsInput.value = tags.join(", ");
  }
  setDocumentMetadataDirty(true);
  renderTagEditor();
}

function setDocumentMetadataDirty(isDirty) {
  documentMetadataDirty = Boolean(isDirty);
}

function handleDocumentBeforeUnload(event) {
  if (!documentMetadataDirty) {
    return;
  }
  event.preventDefault();
  event.returnValue = "";
}

function bindDocumentDirtyState() {
  const { documentMetaForm } = getSingleDocumentElements();
  const markDirtyFromFormEvent = (event) => {
    if (event.target === document.getElementById("metaTagQuery")) {
      return;
    }
    setDocumentMetadataDirty(true);
  };
  documentMetaForm?.addEventListener("input", markDirtyFromFormEvent);
  documentMetaForm?.addEventListener("change", markDirtyFromFormEvent);
  window.addEventListener("beforeunload", handleDocumentBeforeUnload);
}

function hideTagSuggestions() {
  const { metaTagEditor, metaTagSuggestions } = getSingleDocumentElements();
  metaTagEditor?.classList.remove("is-open");
  if (metaTagSuggestions instanceof HTMLElement) {
    metaTagSuggestions.hidden = true;
    metaTagSuggestions.replaceChildren();
  }
}

function renderTagEditor() {
  const { metaTagEditor, metaTagChips, metaTagQuery, metaTagSuggestions } = getSingleDocumentElements();
  if (!(metaTagEditor instanceof HTMLElement) || !(metaTagChips instanceof HTMLElement)) {
    return;
  }
  const tags = getDetailTags();
  metaTagChips.replaceChildren();
  for (const tag of tags) {
    const chip = document.createElement("span");
    chip.className = "tag-pill tag-pill-removable";
    chip.style.setProperty("--tag-color", stableTagColor(tag));

    const swatch = document.createElement("span");
    swatch.className = "tag-swatch tag-swatch-xs";
    swatch.setAttribute("aria-hidden", "true");
    chip.append(swatch, document.createTextNode(tag));

    const removeButton = document.createElement("button");
    removeButton.type = "button";
    removeButton.className = "tag-pill-x";
    removeButton.setAttribute("aria-label", `Remove ${tag}`);
    removeButton.textContent = "x";
    removeButton.addEventListener("click", () => {
      setDetailTags(tags.filter((candidate) => candidate !== tag));
      metaTagQuery?.focus();
    });
    chip.append(removeButton);
    metaTagChips.append(chip);
  }
  if (document.activeElement === metaTagQuery || metaTagEditor.classList.contains("is-open")) {
    renderTagSuggestions();
  } else {
    hideTagSuggestions();
  }
}

function renderTagSuggestions() {
  const { metaTagEditor, metaTagQuery, metaTagSuggestions } = getSingleDocumentElements();
  if (
    !(metaTagEditor instanceof HTMLElement) ||
    !(metaTagQuery instanceof HTMLInputElement) ||
    !(metaTagSuggestions instanceof HTMLElement)
  ) {
    return;
  }
  const tags = getDetailTags();
  const query = metaTagQuery.value.trim().toLowerCase();
  const suggestions = TAG_SUGGESTIONS.filter(
    (tag) => !tags.includes(tag) && (!query || tag.toLowerCase().includes(query))
  ).slice(0, 8);
  metaTagSuggestions.replaceChildren();
  if (!suggestions.length) {
    metaTagEditor.classList.remove("is-open");
    metaTagSuggestions.hidden = true;
    return;
  }
  for (const suggestion of suggestions) {
    const item = document.createElement("li");
    const button = document.createElement("button");
    button.type = "button";
    button.addEventListener("mousedown", (event) => {
      event.preventDefault();
      setDetailTags([...tags, suggestion]);
      metaTagQuery.value = "";
      metaTagQuery.focus();
    });
    const swatch = document.createElement("span");
    swatch.className = "tag-swatch tag-swatch-xs";
    swatch.style.setProperty("--tag-color", stableTagColor(suggestion));
    swatch.setAttribute("aria-hidden", "true");
    button.append(swatch, document.createTextNode(suggestion));
    item.append(button);
    metaTagSuggestions.append(item);
  }
  metaTagEditor.classList.add("is-open");
  metaTagSuggestions.hidden = false;
}

function bindTagEditorEvents() {
  const { metaTagEditor, metaTagQuery } = getSingleDocumentElements();
  if (!(metaTagEditor instanceof HTMLElement) || !(metaTagQuery instanceof HTMLInputElement)) {
    return;
  }
  metaTagQuery.addEventListener("focus", renderTagSuggestions);
  metaTagQuery.addEventListener("input", renderTagSuggestions);
  metaTagQuery.addEventListener("keydown", (event) => {
    const query = metaTagQuery.value.trim();
    if (event.key === "Enter" && query) {
      event.preventDefault();
      const tags = getDetailTags();
      if (!tags.includes(query)) {
        setDetailTags([...tags, query]);
      }
      metaTagQuery.value = "";
    }
    if (event.key === "Backspace" && !query) {
      const tags = getDetailTags();
      if (tags.length) {
        setDetailTags(tags.slice(0, -1));
      }
    }
    if (event.key === "Escape") {
      hideTagSuggestions();
      metaTagQuery.blur();
    }
  });
  metaTagQuery.addEventListener("blur", () => {
    window.setTimeout(() => {
      hideTagSuggestions();
    }, 150);
  });
}

function renderOcrText() {
  const { detailOcrContent, detailOcrLines, detailOcrSearch } = getSingleDocumentElements();
  if (!(detailOcrContent instanceof HTMLElement) || !(detailOcrLines instanceof HTMLElement)) {
    return;
  }
  const query = String(detailOcrSearch?.value || "").trim();
  const lines = detailOcrContent.textContent?.split("\n") || [];
  detailOcrLines.replaceChildren();
  for (const [index, line] of lines.entries()) {
    const row = document.createElement("div");
    row.className = "ocr-line";
    if (query && line.toLowerCase().includes(query.toLowerCase())) {
      row.classList.add("hit");
    }
    const num = document.createElement("span");
    num.className = "ocr-num";
    num.textContent = String(index + 1).padStart(3, "0");
    const content = document.createElement("span");
    content.className = "ocr-content";
    content.textContent = line;
    row.append(num, content);
    detailOcrLines.append(row);
  }
}

function bindDetailTabs() {
  document.querySelectorAll("[data-detail-tab]").forEach((tab) => {
    tab.addEventListener("click", () => {
      const target = tab instanceof HTMLElement ? tab.dataset.detailTab || "details" : "details";
      document.querySelectorAll("[data-detail-tab]").forEach((candidate) => {
        const active = candidate === tab;
        candidate.classList.toggle("active", active);
        candidate.setAttribute("aria-selected", active ? "true" : "false");
      });
      document.querySelectorAll("[data-detail-pane]").forEach((pane) => {
        pane.hidden = !(pane instanceof HTMLElement && pane.dataset.detailPane === target);
      });
      if (target === "ocr") {
        renderOcrText();
      }
    });
  });
}

function bindOcrEvents() {
  const { detailOcrSearch, detailOcrCopyBtn, detailOcrContent } = getSingleDocumentElements();
  detailOcrSearch?.addEventListener("input", renderOcrText);
  detailOcrCopyBtn?.addEventListener("click", async () => {
    try {
      await navigator.clipboard.writeText(detailOcrContent?.textContent || "");
      logActivity("Copied OCR text.");
    } catch (error) {
      logActivity(`Failed to copy OCR text: ${error.message}`);
    }
  });
}

function bindSystemInformationToggle() {
  const toggle = document.getElementById("systemInformationToggle");
  const body = document.getElementById("systemInformationBody");
  toggle?.addEventListener("click", () => {
    if (!(toggle instanceof HTMLButtonElement) || !(body instanceof HTMLElement)) {
      return;
    }
    const expanded = toggle.getAttribute("aria-expanded") === "true";
    toggle.setAttribute("aria-expanded", expanded ? "false" : "true");
    body.hidden = expanded;
  });
}

function getPreviewPageCount() {
  const { pageStrip, previewTotalPages } = getSingleDocumentElements();
  const rawCount = pageStrip instanceof HTMLElement
    ? pageStrip.dataset.pageCount
    : previewTotalPages?.textContent;
  const pageCount = Number.parseInt(rawCount || "1", 10);
  return Number.isFinite(pageCount) && pageCount > 0 ? pageCount : 1;
}

function previewUrlForPage(src, pageNumber) {
  const source = String(src || "");
  if (!source) {
    return "";
  }
  const [base, hash = ""] = source.split("#");
  const url = new URL(base, window.location.origin);
  url.searchParams.set("preview_page", String(pageNumber));
  const params = new URLSearchParams(hash);
  params.set("page", String(pageNumber));
  params.set("toolbar", "0");
  params.set("navpanes", "0");
  params.set("scrollbar", "0");
  params.set("view", "FitH");
  return `${url.pathname}${url.search}#${params.toString()}`;
}

function isPdfPreviewActive() {
  const { documentPreviewFrame, detailPdfPreview } = getSingleDocumentElements();
  return (
    documentPreviewFrame instanceof HTMLElement &&
    detailPdfPreview instanceof HTMLElement &&
    documentPreviewFrame.dataset.previewKind === "pdf" &&
    !detailPdfPreview.hidden
  );
}

function getPdfPreviewUrl() {
  const { detailPdfPreview, documentPreviewFrame } = getSingleDocumentElements();
  return String(
    detailPdfPreview?.dataset?.pdfUrl ||
    documentPreviewFrame?.dataset?.previewUrl ||
    "",
  ).trim();
}

async function loadPdfJs() {
  if (!pdfjsPromise) {
    pdfjsPromise = import(PDFJS_MODULE_URL).then((pdfjs) => {
      pdfjs.GlobalWorkerOptions.workerSrc = PDFJS_WORKER_URL;
      return pdfjs;
    });
  }
  return pdfjsPromise;
}

function setPdfStatus(message) {
  const { detailPdfStatus } = getSingleDocumentElements();
  if (detailPdfStatus instanceof HTMLElement) {
    detailPdfStatus.textContent = message || "";
  }
}

function updatePdfZoomText(scale) {
  const { previewZoomText } = getSingleDocumentElements();
  if (previewZoomText instanceof HTMLElement) {
    previewZoomText.textContent = `${Math.max(10, Math.round(scale * 100))}%`;
  }
}

function getPdfFitWidth(detailPdfPreview) {
  const canvasStage = detailPdfPreview.closest(".page-canvas");
  const stageWidth = canvasStage instanceof HTMLElement
    ? canvasStage.clientWidth
    : detailPdfPreview.parentElement?.clientWidth || detailPdfPreview.clientWidth || 800;
  const stageStyle = canvasStage instanceof HTMLElement ? window.getComputedStyle(canvasStage) : null;
  const horizontalPadding = stageStyle
    ? Number.parseFloat(stageStyle.paddingLeft || "0") + Number.parseFloat(stageStyle.paddingRight || "0")
    : 0;
  return Math.max(240, stageWidth - horizontalPadding);
}

async function ensurePdfDocument() {
  const url = getPdfPreviewUrl();
  if (!url) {
    throw new Error("No PDF file URL is available.");
  }
  if (pdfDocument && pdfDocumentUrl === url) {
    return pdfDocument;
  }
  if (pdfRenderTask) {
    pdfRenderTask.cancel();
    pdfRenderTask = null;
  }
  pdfDocument = null;
  pdfDocumentUrl = url;
  setPdfStatus("Loading PDF...");
  const pdfjs = await loadPdfJs();
  pdfDocument = await pdfjs.getDocument({
    url,
    cMapPacked: true,
    cMapUrl: PDFJS_CMAP_URL,
    iccUrl: PDFJS_ICC_URL,
    standardFontDataUrl: PDFJS_STANDARD_FONT_URL,
    wasmUrl: PDFJS_WASM_URL,
    withCredentials: true,
  }).promise;
  const { previewTotalPages } = getSingleDocumentElements();
  if (previewTotalPages instanceof HTMLElement) {
    previewTotalPages.textContent = String(pdfDocument.numPages || 1);
  }
  return pdfDocument;
}

async function renderPdfPage(pageNumber) {
  if (!isPdfPreviewActive()) {
    return;
  }
  const { detailPdfPreview, detailPdfCanvas } = getSingleDocumentElements();
  if (!(detailPdfPreview instanceof HTMLElement) || !(detailPdfCanvas instanceof HTMLCanvasElement)) {
    return;
  }
  const serial = pdfRenderSerial + 1;
  pdfRenderSerial = serial;
  try {
    const pdf = await ensurePdfDocument();
    if (serial !== pdfRenderSerial) {
      return;
    }
    const safePage = Math.min(Math.max(1, pageNumber), pdf.numPages || 1);
    const page = await pdf.getPage(safePage);
    if (serial !== pdfRenderSerial) {
      return;
    }
    const baseViewport = page.getViewport({ scale: 1 });
    const availableWidth = getPdfFitWidth(detailPdfPreview);
    const scale = pdfScaleMode === "fit"
      ? Math.max(0.25, Math.min(3, availableWidth / baseViewport.width))
      : pdfManualScale;
    const viewport = page.getViewport({ scale });
    const deviceScale = window.devicePixelRatio || 1;
    detailPdfCanvas.width = Math.floor(viewport.width * deviceScale);
    detailPdfCanvas.height = Math.floor(viewport.height * deviceScale);
    detailPdfCanvas.style.width = `${viewport.width}px`;
    detailPdfCanvas.style.height = `${viewport.height}px`;
    detailPdfPreview.style.width = `${viewport.width}px`;
    detailPdfPreview.style.minHeight = `${viewport.height}px`;
    const context = detailPdfCanvas.getContext("2d");
    if (!context) {
      throw new Error("Canvas rendering is not available.");
    }
    if (pdfRenderTask) {
      pdfRenderTask.cancel();
    }
    setPdfStatus("");
    updatePdfZoomText(scale);
    pdfRenderTask = page.render({
      canvasContext: context,
      viewport,
      transform: deviceScale === 1 ? null : [deviceScale, 0, 0, deviceScale, 0, 0],
    });
    await pdfRenderTask.promise;
    if (serial === pdfRenderSerial) {
      pdfRenderTask = null;
    }
  } catch (error) {
    if (String(error?.name || "") === "RenderingCancelledException") {
      return;
    }
    setPdfStatus(`Could not render PDF preview: ${error.message || error}`);
  }
}

function setPreviewPage(pageNumber, options = {}) {
  const {
    detailEmbedPreview,
    pageStrip,
    previewCurrentPage,
    previewPrevPageBtn,
    previewNextPageBtn,
  } = getSingleDocumentElements();
  const pageCount = getPreviewPageCount();
  const nextPage = Math.min(Math.max(1, Number.parseInt(String(pageNumber || 1), 10) || 1), pageCount);

  if (previewCurrentPage instanceof HTMLElement) {
    previewCurrentPage.textContent = String(nextPage);
  }
  if (previewPrevPageBtn instanceof HTMLButtonElement) {
    previewPrevPageBtn.disabled = nextPage <= 1;
  }
  if (previewNextPageBtn instanceof HTMLButtonElement) {
    previewNextPageBtn.disabled = nextPage >= pageCount;
  }
  pageStrip?.querySelectorAll("[data-preview-page]").forEach((candidate) => {
    if (!(candidate instanceof HTMLElement)) {
      return;
    }
    const active = Number.parseInt(candidate.dataset.previewPage || "1", 10) === nextPage;
    candidate.classList.toggle("active", active);
    if (active) {
      candidate.setAttribute("aria-current", "page");
      candidate.scrollIntoView({ block: "nearest" });
    } else {
      candidate.removeAttribute("aria-current");
    }
  });

  if (options.updateFrame !== false && isPdfPreviewActive()) {
    void renderPdfPage(nextPage);
    return;
  }

  if (options.updateFrame !== false && detailEmbedPreview instanceof HTMLIFrameElement) {
    const nextSrc = previewUrlForPage(detailEmbedPreview.getAttribute("src") || detailEmbedPreview.src, nextPage);
    if (nextSrc) {
      detailEmbedPreview.src = nextSrc;
    }
  }
}

function bindPreviewPager() {
  const {
    pageStrip,
    previewPrevPageBtn,
    previewNextPageBtn,
    previewZoomOutBtn,
    previewZoomInBtn,
    previewFitWidthBtn,
  } = getSingleDocumentElements();
  pageStrip?.addEventListener("click", (event) => {
    const target = event.target instanceof Element ? event.target.closest("[data-preview-page]") : null;
    if (!(target instanceof HTMLElement)) {
      return;
    }
    setPreviewPage(Number.parseInt(target.dataset.previewPage || "1", 10));
  });
  [previewPrevPageBtn, previewNextPageBtn].forEach((button) => {
    button?.addEventListener("click", () => {
      const { previewCurrentPage } = getSingleDocumentElements();
      const currentPage = Number.parseInt(previewCurrentPage?.textContent || "1", 10) || 1;
      const step = Number.parseInt(button.dataset.previewPageStep || "0", 10) || 0;
      setPreviewPage(currentPage + step);
    });
  });
  previewZoomOutBtn?.addEventListener("click", () => {
    if (!isPdfPreviewActive()) {
      return;
    }
    const { previewCurrentPage } = getSingleDocumentElements();
    pdfScaleMode = "manual";
    pdfManualScale = Math.max(0.25, pdfManualScale - 0.15);
    renderPdfPage(Number.parseInt(previewCurrentPage?.textContent || "1", 10) || 1);
  });
  previewZoomInBtn?.addEventListener("click", () => {
    if (!isPdfPreviewActive()) {
      return;
    }
    const { previewCurrentPage } = getSingleDocumentElements();
    pdfScaleMode = "manual";
    pdfManualScale = Math.min(3, pdfManualScale + 0.15);
    renderPdfPage(Number.parseInt(previewCurrentPage?.textContent || "1", 10) || 1);
  });
  previewFitWidthBtn?.addEventListener("click", () => {
    if (!isPdfPreviewActive()) {
      return;
    }
    const { previewCurrentPage } = getSingleDocumentElements();
    pdfScaleMode = "fit";
    renderPdfPage(Number.parseInt(previewCurrentPage?.textContent || "1", 10) || 1);
  });
  setPreviewPage(1, { updateFrame: false });
}

function initializePdfPreview() {
  const { detailPdfPreview, previewCurrentPage } = getSingleDocumentElements();
  if (pdfResizeObserver) {
    pdfResizeObserver.disconnect();
    pdfResizeObserver = null;
  }
  if (!isPdfPreviewActive()) {
    pdfDocument = null;
    pdfDocumentUrl = "";
    setPdfStatus("");
    return;
  }
  pdfScaleMode = "fit";
  pdfManualScale = 1;
  pdfResizeObserver = new ResizeObserver(() => {
    if (pdfScaleMode !== "fit" || !isPdfPreviewActive()) {
      return;
    }
    const pageNumber = Number.parseInt(previewCurrentPage?.textContent || "1", 10) || 1;
    renderPdfPage(pageNumber);
  });
  if (detailPdfPreview instanceof HTMLElement) {
    pdfResizeObserver.observe(detailPdfPreview);
  }
  renderPdfPage(Number.parseInt(previewCurrentPage?.textContent || "1", 10) || 1);
}

function bindSingleDocumentEvents() {
  if (singleDocumentEventsBound) {
    return;
  }
  const {
    documentMetaForm,
    backToDocsBtn,
    reprocessDocumentBtn,
    deleteDocumentBtn,
    starDocumentBtn,
    viewDocumentFileBtn,
    metaTitleInput,
    metaDateInput,
    metaCorrespondentInput,
    metaTypeInput,
    metaTagsInput,
    detailFilename,
  } = getSingleDocumentElements();

  starDocumentBtn?.addEventListener("click", async () => {
    if (!appState.currentDocumentId) {
      logActivity("No document selected.");
      return;
    }
    const nextStarred = starDocumentBtn.getAttribute("aria-pressed") !== "true";
    starDocumentBtn.disabled = true;
    const response = await apiFetch(`/documents/${appState.currentDocumentId}/starred`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ starred: nextStarred }),
    });
    const payload = await response.json().catch(() => ({}));
    starDocumentBtn.disabled = false;
    if (!response.ok) {
      logActivity(`Star update failed: ${payload.detail || response.statusText}`);
      return;
    }
    const starred = Boolean(payload?.document?.starred);
    renderDocumentStarButton(starred);
    logActivity(`${starred ? "Starred" : "Unstarred"} document ${appState.currentDocumentId}.`);
  });

  documentMetaForm?.addEventListener("submit", async (event) => {
    event.preventDefault();
    if (!appState.currentDocumentId) {
      logActivity("No document selected.");
      return;
    }

    const response = await apiFetch(`/documents/${appState.currentDocumentId}/metadata`, {
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

    logActivity(`Saved metadata for ${appState.currentDocumentId}`);
    setDocumentMetadataDirty(false);
    await openDocumentView(appState.currentDocumentId);
    await refreshDocumentRelatedLists({ catalog: true });
  });

  reprocessDocumentBtn?.addEventListener("click", async () => {
    if (!appState.currentDocumentId) {
      logActivity("No document selected.");
      return;
    }

    const response = await apiFetch(`/documents/${appState.currentDocumentId}/reprocess`, {
      method: "POST",
    });
    const payload = await response.json();
    if (!response.ok) {
      logActivity(`Reprocess failed: ${payload.detail || response.statusText}`);
      return;
    }

    logActivity(
      `Reprocessing queued for ${appState.currentDocumentId} (job ${payload.job_id}).`
    );
    await openDocumentView(appState.currentDocumentId);
    await refreshDocumentRelatedLists();
    const completed = await waitForDocumentReady(appState.currentDocumentId);
    if (completed) {
      logActivity(`Reprocessing completed for ${appState.currentDocumentId}.`);
      await openDocumentView(appState.currentDocumentId);
      await refreshDocumentRelatedLists({ catalog: true });
    } else {
      logActivity(`Reprocessing still running for ${appState.currentDocumentId}. Refresh to check later.`);
    }
  });

  deleteDocumentBtn?.addEventListener("click", async () => {
    if (!appState.currentDocumentId) {
      logActivity("No document selected.");
      return;
    }
    await deleteDocumentById(appState.currentDocumentId, {
      documentLabel: metaTitleInput?.value?.trim() || detailFilename?.textContent || appState.currentDocumentId,
    });
  });

  viewDocumentFileBtn?.addEventListener("click", async () => {
    if (!appState.currentDocumentId) {
      logActivity("No document selected.");
      return;
    }
    try {
      await openDocumentFile(appState.currentDocumentId);
    } catch (error) {
      logActivity(`Failed to open file: ${error.message}`);
    }
  });

  backToDocsBtn?.addEventListener("click", () => {
    const url = new URL("/ui/documents", window.location.origin);
    window.location.href = url.pathname;
  });

  bindDetailTabs();
  bindTagEditorEvents();
  bindOcrEvents();
  bindSystemInformationToggle();
  bindPreviewPager();
  bindDocumentDirtyState();
  document.addEventListener("paperwise:document-detail-updated", () => {
    setDocumentMetadataDirty(false);
    renderTagEditor();
    renderOcrText();
    setPreviewPage(1, { updateFrame: false });
    initializePdfPreview();
  });

  singleDocumentEventsBound = true;
}

export async function initializePage({ authenticated, initialData }) {
  if (authenticated !== true) {
    return;
  }
  bindSingleDocumentEvents();
  if (hydrateInitialDocumentData(initialData || {})) {
    setDocumentMetadataDirty(false);
    renderDocumentStarButton(Boolean(initialData?.document_detail?.document?.starred));
    renderTagEditor();
    renderOcrText();
    initializePdfPreview();
    return;
  }
  appState.currentDocumentId = new URLSearchParams(window.location.search).get("id") || "";
  if (appState.currentDocumentId) {
    await openDocumentView(appState.currentDocumentId);
  }
}
