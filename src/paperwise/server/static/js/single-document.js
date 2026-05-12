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
import { splitTags } from "./ui/values.js";

let singleDocumentEventsBound = false;
const TAG_COLOR_SET = [
  "#8e5bcb",
  "#1d6a55",
  "#b0552f",
  "#c47a2a",
  "#2c6488",
  "#7a5c2e",
  "#8b4778",
  "#3d7a66",
  "#9f4a28",
  "#4f6f9f",
  "#6b5b95",
  "#2f7a8a",
];
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
    detailFilePreview: document.getElementById("detailFilePreview"),
    pageStrip: document.getElementById("pageStrip"),
    previewCurrentPage: document.getElementById("previewCurrentPage"),
    previewTotalPages: document.getElementById("previewTotalPages"),
    previewPrevPageBtn: document.getElementById("previewPrevPageBtn"),
    previewNextPageBtn: document.getElementById("previewNextPageBtn"),
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

function stableTagColor(value) {
  const normalized = String(value || "").trim().toLowerCase();
  if (!normalized) {
    return "#7c8783";
  }
  let hash = 0;
  for (const char of normalized) {
    hash = (hash * 33 + char.charCodeAt(0)) % 2147483647;
  }
  return TAG_COLOR_SET[hash % TAG_COLOR_SET.length];
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
  renderTagEditor();
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

function setPreviewPage(pageNumber, options = {}) {
  const {
    detailFilePreview,
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

  if (options.updateFrame !== false && detailFilePreview instanceof HTMLIFrameElement) {
    const nextSrc = previewUrlForPage(detailFilePreview.getAttribute("src") || detailFilePreview.src, nextPage);
    if (nextSrc) {
      detailFilePreview.src = nextSrc;
    }
  }
}

function bindPreviewPager() {
  const { pageStrip, previewPrevPageBtn, previewNextPageBtn } = getSingleDocumentElements();
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
  setPreviewPage(1, { updateFrame: false });
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
    viewDocumentFileBtn,
    metaTitleInput,
    metaDateInput,
    metaCorrespondentInput,
    metaTypeInput,
    metaTagsInput,
    detailFilename,
  } = getSingleDocumentElements();

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
  document.addEventListener("paperwise:document-detail-updated", () => {
    renderTagEditor();
    renderOcrText();
    setPreviewPage(1, { updateFrame: false });
  });

  singleDocumentEventsBound = true;
}

export async function initializePage({ authenticated, initialData }) {
  if (authenticated !== true) {
    return;
  }
  bindSingleDocumentEvents();
  if (hydrateInitialDocumentData(initialData || {})) {
    renderTagEditor();
    renderOcrText();
    return;
  }
  appState.currentDocumentId = new URLSearchParams(window.location.search).get("id") || "";
  if (appState.currentDocumentId) {
    await openDocumentView(appState.currentDocumentId);
  }
}
