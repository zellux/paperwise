import {
  apiFetch,
  applyHtmlPartialTarget,
  fetchHtmlPartial,
  renderTableLoading,
  replaceElementHtml,
} from "paperwise/shared";
import {
  appState,
  logActivity,
  navigateToDocument,
} from "paperwise/app";
import { readInitialData } from "./state/initialData.js";
import { getResolvedTaskSettings } from "./state/llm.js";
import {
  normalizeGroundedQaMaxDocuments,
  normalizeGroundedQaTopK,
} from "./state/preferences.js";
import {
  formatChatEventDetail,
  parseChatStreamEvent,
} from "./chat/streamEvents.js";
import { renderChatTranscript } from "./chat/transcript.js";
import { renderSearchResultsTable as renderSearchResultsTableInto } from "./search/resultsTable.js";

let searchKeywordForm = null;
let searchKeywordInput = null;
let searchKeywordLimitSelect = null;
let searchResultsMeta = null;
let searchResultsTableBody = null;
let searchAskForm = null;
let searchAskQuestion = null;
let searchAskNewChatBtn = null;
let searchAskThreadSearch = null;
let searchAskThreadList = null;
let searchAskThreadTitle = null;
let searchAskModelLabel = null;
let searchAskTokenUsage = null;
let searchAskMessages = null;
let searchAskHints = null;

let searchAskMessagesState = [];
let searchAskInFlight = false;
let searchAskMessageSeq = 0;
let searchAskCurrentTokens = 0;
let searchAskTimerId = 0;
let searchAskThreadId = "";
let initialChatThreadsConsumed = false;
let searchEventsBound = false;

function bindSearchElements() {
  searchKeywordForm = document.getElementById("searchKeywordForm");
  searchKeywordInput = document.getElementById("searchKeywordInput");
  searchKeywordLimitSelect = document.getElementById("searchKeywordLimitSelect");
  searchResultsMeta = document.getElementById("searchResultsMeta");
  searchResultsTableBody = document.getElementById("searchResultsTableBody");
  searchAskForm = document.getElementById("searchAskForm");
  searchAskQuestion = document.getElementById("searchAskQuestion");
  searchAskNewChatBtn = document.getElementById("searchAskNewChatBtn");
  searchAskThreadSearch = document.getElementById("searchAskThreadSearch");
  searchAskThreadList = document.getElementById("searchAskThreadList");
  searchAskThreadTitle = document.getElementById("searchAskThreadTitle");
  searchAskModelLabel = document.getElementById("searchAskModelLabel");
  searchAskTokenUsage = document.getElementById("searchAskTokenUsage");
  searchAskMessages = document.getElementById("searchAskMessages");
  searchAskHints = document.getElementById("searchAskHints");
}

function renderSearchResultsMeta(message) {
  if (!searchResultsMeta) {
    return;
  }
  searchResultsMeta.textContent = message;
}

function renderSearchResultsTable(payload) {
  renderSearchResultsTableInto(payload, searchResultsTableBody, navigateToDocument);
}

function appendSearchAskMessage(role, content, options = {}) {
  const normalizedRole = role === "user" || role === "status" ? role : "assistant";
  const message = {
    id: `chat-message-${++searchAskMessageSeq}`,
    role: normalizedRole,
    content: String(content || "").trim(),
    pending: Boolean(options.pending),
    toolCalls: Array.isArray(options.toolCalls) ? options.toolCalls : [],
    citations: Array.isArray(options.citations) ? options.citations : [],
    statusKind: String(options.statusKind || "").trim(),
    statusSummary: String(options.statusSummary || "").trim(),
    statusDetail: String(options.statusDetail || "").trim(),
    expanded: Boolean(options.expanded),
    activity: Boolean(options.activity),
    activityRounds: Array.isArray(options.activityRounds) ? options.activityRounds : [],
  };
  if (!message.content && !message.pending) {
    return null;
  }
  searchAskMessagesState.push(message);
  renderSearchAskMessages();
  return message;
}

function updatePendingSearchAskMessage(message, content, options = {}) {
  if (!message) {
    return;
  }
  message.content = String(content || "").trim();
  message.pending = false;
  message.toolCalls = Array.isArray(options.toolCalls) ? options.toolCalls : [];
  message.citations = Array.isArray(options.citations) ? options.citations : [];
  renderSearchAskMessages();
}

function appendSearchAskStatus(label, detail = "", options = {}) {
  const summary = String(options.summary || label || "Working").trim();
  const fullDetail = String(options.detail || detail || "").trim();
  const compactDetail = String(detail || "").trim();
  const parts = [summary, compactDetail].filter(Boolean);
  return appendSearchAskMessage("status", parts.join(": "), {
    statusKind: options.statusKind || "",
    statusSummary: parts.join(": "),
    statusDetail: fullDetail,
  });
}

function appendSearchAskActivity() {
  return appendSearchAskMessage("status", "Working through document tools.", {
    statusKind: "activity",
    statusSummary: "Working through document tools.",
    activity: true,
    activityRounds: [],
  });
}

function hasActiveSearchAskRound() {
  return searchAskMessagesState.some(
    (message) =>
      message.activity &&
      Array.isArray(message.activityRounds) &&
      message.activityRounds.some((round) => round.startedAt && !round.endedAt),
  );
}

function syncSearchAskTimer() {
  if (hasActiveSearchAskRound()) {
    if (!searchAskTimerId) {
      searchAskTimerId = window.setInterval(() => {
        if (!hasActiveSearchAskRound()) {
          syncSearchAskTimer();
          return;
        }
        renderSearchAskMessages();
      }, 1000);
    }
    return;
  }
  if (searchAskTimerId) {
    window.clearInterval(searchAskTimerId);
    searchAskTimerId = 0;
  }
}

function finishActiveSearchAskRound(activityMessage) {
  if (!activityMessage || !Array.isArray(activityMessage.activityRounds)) {
    return;
  }
  const round = activityMessage.activityRounds.at(-1);
  if (round?.startedAt && !round.endedAt) {
    round.endedAt = Date.now();
  }
  syncSearchAskTimer();
}

function finishAllSearchAskRounds(activityMessage) {
  if (!activityMessage || !Array.isArray(activityMessage.activityRounds)) {
    syncSearchAskTimer();
    return;
  }
  const now = Date.now();
  for (const round of activityMessage.activityRounds) {
    if (round.startedAt && !round.endedAt) {
      round.endedAt = now;
    }
  }
  syncSearchAskTimer();
}

function formatTokenCount(value) {
  const count = Number(value || 0);
  if (!Number.isFinite(count) || count <= 0) {
    return "0";
  }
  return Math.round(count).toLocaleString();
}

function renderSearchAskTokenUsage() {
  if (!searchAskTokenUsage) {
    return;
  }
  const tokenLabel = searchAskCurrentTokens === 1 ? "token" : "tokens";
  searchAskTokenUsage.textContent = `${formatTokenCount(searchAskCurrentTokens)} ${tokenLabel}`;
}

function renderSearchAskHeader() {
  if (searchAskThreadTitle) {
    searchAskThreadTitle.textContent = getSearchAskThreadTitle(searchAskThreadId) || "Ask Your Docs";
  }
  if (searchAskModelLabel) {
    const settings = getResolvedTaskSettings("grounded_qa");
    const parts = [settings?.provider, settings?.model].filter(Boolean);
    searchAskModelLabel.textContent = parts.length ? parts.join(" · ") : "Model not configured";
  }
  renderSearchAskTokenUsage();
}

function updateSearchAskTokenUsage(tokenUsage) {
  const nextTotal = Number(tokenUsage?.total_tokens || 0);
  if (!Number.isFinite(nextTotal) || nextTotal < 0) {
    return;
  }
  searchAskCurrentTokens = nextTotal;
  renderSearchAskTokenUsage();
}

function syncSearchAskThreadSelect() {
  if (!searchAskThreadList) {
    return;
  }
  for (const item of searchAskThreadList.querySelectorAll(".thread-item")) {
    const button = item.querySelector("[data-thread-id]");
    item.classList.toggle("active", button?.dataset.threadId === searchAskThreadId);
  }
  for (const button of searchAskThreadList.querySelectorAll("[data-delete-thread-id]")) {
    button.disabled = searchAskInFlight;
  }
}

function getSearchAskThreadTitle(threadId) {
  for (const button of searchAskThreadList?.querySelectorAll("[data-thread-id]") || []) {
    if (button.dataset.threadId === threadId) {
      return button.querySelector(".thread-title")?.textContent?.trim() || "";
    }
  }
  return "";
}

function renderSearchAskThreadSelect() {
  syncSearchAskThreadSelect();
  renderSearchAskHeader();
}

function applySearchAskThreadsPartial(payload) {
  applyHtmlPartialTarget(searchAskThreadList, payload);
  syncSearchAskThreadSelect();
}

async function loadSearchAskThreads() {
  if (!searchAskThreadList) {
    return;
  }
  const initialData = readInitialData();
  if (
    !initialChatThreadsConsumed &&
    initialData.authenticated === true &&
    Array.isArray(initialData.chat_threads)
  ) {
    initialChatThreadsConsumed = true;
    syncSearchAskThreadSelect();
    return;
  }
  const query = new URLSearchParams();
  if (searchAskThreadId) {
    query.set("active_thread_id", searchAskThreadId);
  }
  const search = String(searchAskThreadSearch?.value || "").trim();
  if (search) {
    query.set("q", search);
  }
  const suffix = query.toString() ? `?${query.toString()}` : "";
  let payload;
  try {
    payload = await fetchHtmlPartial(`/ui/partials/chat-threads${suffix}`);
  } catch (error) {
    logActivity(`Chat history failed: ${error.message}`);
    return;
  }
  applySearchAskThreadsPartial(payload);
}

function hydrateSearchAskMessages(messages) {
  searchAskMessagesState = [];
  searchAskMessageSeq = 0;
  for (const item of Array.isArray(messages) ? messages : []) {
    const role = String(item?.role || "").trim().toLowerCase();
    const content = String(item?.content || "").trim();
    if (!content || !["user", "assistant"].includes(role)) {
      continue;
    }
    searchAskMessagesState.push({
      id: `chat-message-${++searchAskMessageSeq}`,
      role,
      content,
      pending: false,
      toolCalls: [],
      citations: Array.isArray(item?.citations) ? item.citations : [],
      statusKind: "",
      statusSummary: "",
      statusDetail: "",
      expanded: false,
      activity: false,
      activityRounds: [],
    });
  }
  renderSearchAskMessages();
}

async function loadSearchAskThread(threadId) {
  const id = String(threadId || "").trim();
  if (!id || searchAskInFlight) {
    return;
  }
  const response = await apiFetch(`/query/chat/threads/${encodeURIComponent(id)}`);
  const payload = await response.json();
  if (!response.ok) {
    logActivity(`Load chat failed: ${payload.detail || response.statusText}`);
    renderSearchAskThreadSelect();
    return;
  }
  searchAskThreadId = payload.id || "";
  updateSearchAskTokenUsage(payload.token_usage);
  hydrateSearchAskMessages(payload.messages || []);
  await loadSearchAskThreads();
  logActivity(`Loaded chat: ${payload.title || "Untitled chat"}`);
}

async function deleteSearchAskThread(threadId) {
  const id = String(threadId || "").trim();
  if (!id || searchAskInFlight) {
    return;
  }
  const title = getSearchAskThreadTitle(id) || "this chat";
  const confirmed = window.confirm(`Delete "${title}" from chat history?`);
  if (!confirmed) {
    return;
  }
  const response = await apiFetch(`/query/chat/threads/${encodeURIComponent(id)}`, {
    method: "DELETE",
  });
  if (!response.ok) {
    const payload = await response.json().catch(() => ({}));
    logActivity(`Delete chat failed: ${payload.detail || response.statusText}`);
    renderSearchAskThreadSelect();
    return;
  }
  if (searchAskThreadId === id) {
    resetSearchAskChat();
  } else {
    syncSearchAskThreadSelect();
  }
  await loadSearchAskThreads();
  logActivity(`Deleted chat: ${title}`);
}

function renderSearchAskMessages() {
  renderSearchAskHeader();
  const hasChatMessages = searchAskMessagesState.some((message) => ["user", "assistant"].includes(message.role));
  if (searchAskHints instanceof HTMLElement) {
    searchAskHints.hidden = hasChatMessages;
  }
  if (!hasChatMessages && searchAskHints instanceof HTMLElement && searchAskMessages instanceof HTMLElement) {
    searchAskMessages.replaceChildren();
    return;
  }
  renderChatTranscript({
    container: searchAskMessages,
    messages: searchAskMessagesState,
    currentUser: appState.currentUser,
    navigateToDocument,
  });
}

function resetSearchAskChat() {
  if (searchAskInFlight) {
    return;
  }
  searchAskMessagesState = [];
  searchAskMessageSeq = 0;
  searchAskCurrentTokens = 0;
  searchAskThreadId = "";
  syncSearchAskTimer();
  renderSearchAskTokenUsage();
  renderSearchAskThreadSelect();
  renderSearchAskMessages();
  if (searchAskQuestion) {
    searchAskQuestion.value = "";
    autoResizeChatTextarea(searchAskQuestion);
    searchAskQuestion.focus();
  }
}

export function clearSessionState() {
  searchAskMessagesState = [];
  searchAskMessageSeq = 0;
  searchAskCurrentTokens = 0;
  searchAskThreadId = "";
  initialChatThreadsConsumed = false;
  syncSearchAskTimer();
  renderSearchAskTokenUsage();
  renderSearchAskThreadSelect();
  replaceElementHtml(searchResultsTableBody, '<tr><td colspan="6">No matches found.</td></tr>');
  renderSearchResultsMeta("No search run yet.");
  renderSearchAskMessages();
}

function setButtonBusy(button, busy, busyLabel = "Loading...") {
  if (!button) {
    return;
  }
  if (busy) {
    if (!button.dataset.originalLabel) {
      button.dataset.originalLabel = button.textContent || "";
    }
    button.textContent = busyLabel;
    button.disabled = true;
    return;
  }
  button.disabled = false;
  if (button.dataset.originalLabel) {
    button.textContent = button.dataset.originalLabel;
  }
}

async function runKeywordSearch() {
  const query = String(searchKeywordInput?.value || "").trim();
  if (!query) {
    renderSearchResultsMeta("Enter a query.");
    return;
  }
  const limit = Math.max(1, Math.min(100, Number(searchKeywordLimitSelect?.value || 20)));
  renderTableLoading(searchResultsTableBody, 6, "Searching...");
  renderSearchResultsMeta("Searching...");
  setButtonBusy(searchKeywordForm?.querySelector("button[type='submit']"), true, "Searching...");
  try {
    const response = await apiFetch("/collections/search", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ query, limit }),
    });
    const payload = await response.json();
    if (!response.ok) {
      logActivity(`Search failed: ${payload.detail || response.statusText}`);
      renderSearchResultsTable({ hits: [] });
      renderSearchResultsMeta("Search failed.");
      return;
    }
    renderSearchResultsTable(payload);
    const totalHits = Number(payload.total_hits || 0);
    renderSearchResultsMeta(`Found ${totalHits} result(s).`);
    logActivity(`Search completed: ${totalHits} result(s).`);
  } finally {
    setButtonBusy(searchKeywordForm?.querySelector("button[type='submit']"), false);
  }
}

function getSearchAskActivityRound(activityMessage) {
  if (!activityMessage) {
    return null;
  }
  if (!Array.isArray(activityMessage.activityRounds)) {
    activityMessage.activityRounds = [];
  }
  let round = activityMessage.activityRounds.at(-1);
  if (!round) {
    round = {
      index: 1,
      summary: "LLM request",
      details: [],
      toolCallCount: 0,
      resultCount: 0,
      startedAt: Date.now(),
      expanded: false,
    };
    activityMessage.activityRounds.push(round);
  }
  if (!Array.isArray(round.details)) {
    round.details = [];
  }
  return round;
}

function appendSearchAskActivityRound(activityMessage, data) {
  if (!activityMessage) {
    appendSearchAskStatus(data.label || "Working", data.detail || "", {
      statusKind: "request",
      detail: data.detail || "",
    });
    return;
  }
  finishActiveSearchAskRound(activityMessage);
  const round = {
    index: activityMessage.activityRounds.length + 1,
    summary: data.detail || data.label || "LLM request",
    details: [data.detail || data.label || "LLM request"],
    toolCallCount: 0,
    resultCount: 0,
    startedAt: Date.now(),
    expanded: false,
  };
  activityMessage.activityRounds.push(round);
  syncSearchAskTimer();
  renderSearchAskMessages();
}

function appendSearchAskRoundDetail(round, label, detail) {
  if (!round) {
    return;
  }
  const parts = [String(label || "").trim(), String(detail || "").trim()].filter(Boolean);
  if (parts.length) {
    round.details.push(parts.join("\n"));
  }
}

function handleSearchAskStreamEvent(eventType, data, pendingMessage, activityMessage = null) {
  if (eventType === "status") {
    appendSearchAskActivityRound(activityMessage, data);
    return null;
  }
  if (eventType === "llm_response") {
    const toolCallCount = Number(data.tool_call_count || 0);
    updateSearchAskTokenUsage(data.token_usage);
    const round = getSearchAskActivityRound(activityMessage);
    if (round) {
      round.toolCallCount = toolCallCount;
      round.finalReady = toolCallCount === 0;
      round.summary = toolCallCount ? `${toolCallCount} tool call(s) requested` : "answer ready";
      if (toolCallCount === 0 && !round.endedAt) {
        round.endedAt = Date.now();
        syncSearchAskTimer();
      }
      appendSearchAskRoundDetail(round, "LLM response", formatChatEventDetail(data));
      renderSearchAskMessages();
    }
    return null;
  }
  if (eventType === "token_usage") {
    updateSearchAskTokenUsage(data);
    return null;
  }
  if (eventType === "tool_call") {
    const round = getSearchAskActivityRound(activityMessage);
    if (round) {
      round.toolCallCount = Math.max(Number(round.toolCallCount || 0), Number(round.toolCalls?.length || 0) + 1);
      round.toolCalls = [...(round.toolCalls || []), data.name || "tool"];
      appendSearchAskRoundDetail(round, `Tool call: ${data.name || "tool"}`, formatChatEventDetail(data.arguments || {}));
      renderSearchAskMessages();
    }
    return null;
  }
  if (eventType === "tool_result") {
    const resultCount = Number(data.result_count || 0);
    const round = getSearchAskActivityRound(activityMessage);
    if (round) {
      round.resultCount = Number(round.resultCount || 0) + resultCount;
      appendSearchAskRoundDetail(round, `Tool result: ${data.name || "tool"}`, formatChatEventDetail(data));
      renderSearchAskMessages();
    }
    return null;
  }
  if (eventType === "error") {
    finishAllSearchAskRounds(activityMessage);
    const detail = data.detail || "Chat failed.";
    updatePendingSearchAskMessage(pendingMessage, detail);
    return { error: detail };
  }
  if (eventType === "final") {
    finishAllSearchAskRounds(activityMessage);
    updateSearchAskTokenUsage(data?.token_usage);
    updatePendingSearchAskMessage(
      pendingMessage,
      data?.message?.content || "No answer returned.",
      { citations: data?.citations || [], toolCalls: data?.tool_calls || [] },
    );
    return { final: data };
  }
  return null;
}

async function runSearchAskStream(requestBody, pendingMessage, activityMessage) {
  const response = await apiFetch("/query/chat/stream", {
    method: "POST",
    headers: { "Content-Type": "application/json", Accept: "text/event-stream" },
    body: JSON.stringify(requestBody),
  });
  if (!response.ok || !response.body) {
    return null;
  }
  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  let finalPayload = null;
  while (true) {
    const { value, done } = await reader.read();
    buffer += decoder.decode(value || new Uint8Array(), { stream: !done });
    const events = buffer.split(/\n\n/);
    buffer = events.pop() || "";
    for (const rawEvent of events) {
      if (!rawEvent.trim()) {
        continue;
      }
      const { eventType, data } = parseChatStreamEvent(rawEvent);
      const handled = handleSearchAskStreamEvent(eventType, data, pendingMessage, activityMessage);
      if (handled?.error) {
        throw new Error(handled.error);
      }
      if (handled?.final) {
        finalPayload = handled.final;
      }
    }
    if (done) {
      break;
    }
  }
  if (buffer.trim()) {
    const { eventType, data } = parseChatStreamEvent(buffer);
    const handled = handleSearchAskStreamEvent(eventType, data, pendingMessage, activityMessage);
    if (handled?.error) {
      throw new Error(handled.error);
    }
    if (handled?.final) {
      finalPayload = handled.final;
    }
  }
  return finalPayload;
}

async function runAsk() {
  const question = String(searchAskQuestion?.value || "").trim();
  if (searchAskInFlight) {
    appendSearchAskStatus("Still working", "Wait for the current request to finish.");
    return;
  }
  if (!question) {
    appendSearchAskMessage("assistant", "Enter a question.");
    return;
  }
  const topK = normalizeGroundedQaTopK(appState.groundedQaTopK);
  const maxDocuments = normalizeGroundedQaMaxDocuments(appState.groundedQaMaxDocuments);
  appendSearchAskMessage("user", question);
  const activityMessage = appendSearchAskActivity();
  const pendingMessage = appendSearchAskMessage("assistant", "", { pending: true });
  if (searchAskQuestion) {
    searchAskQuestion.value = "";
    autoResizeChatTextarea(searchAskQuestion);
  }
  setButtonBusy(searchAskForm?.querySelector("button[type='submit']"), true, "Asking...");
  searchAskInFlight = true;
  renderSearchAskThreadSelect();
  const requestBody = {
    thread_id: searchAskThreadId || null,
    messages: searchAskMessagesState
      .filter((message) => !message.pending && ["user", "assistant"].includes(message.role))
      .map((message) => ({ role: message.role, content: message.content })),
    scope: {
      tag: [],
      document_type: [],
      correspondent: [],
    },
    top_k_chunks: topK,
    max_documents: maxDocuments,
    debug: false,
  };
  try {
    const streamedPayload = await runSearchAskStream(requestBody, pendingMessage, activityMessage);
    if (streamedPayload) {
      searchAskThreadId = streamedPayload.thread_id || searchAskThreadId;
      await loadSearchAskThreads();
      logActivity("Ask Your Docs chat completed.");
      return;
    }
    const response = await apiFetch("/query/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(requestBody),
    });
    const payload = await response.json();
    if (!response.ok) {
      updatePendingSearchAskMessage(pendingMessage, payload.detail || response.statusText);
      logActivity(`Ask failed: ${payload.detail || response.statusText}`);
      return;
    }
    updateSearchAskTokenUsage(payload?.token_usage);
    searchAskThreadId = payload?.thread_id || searchAskThreadId;
    updatePendingSearchAskMessage(
      pendingMessage,
      payload?.message?.content || "No answer returned.",
      { citations: payload?.citations || [], toolCalls: payload?.tool_calls || [] },
    );
    await loadSearchAskThreads();
    logActivity("Ask Your Docs chat completed.");
  } catch (error) {
    finishAllSearchAskRounds(activityMessage);
    const message = error instanceof Error ? error.message : String(error || "Chat failed.");
    updatePendingSearchAskMessage(pendingMessage, message);
    logActivity(`Ask failed: ${message}`);
  } finally {
    searchAskInFlight = false;
    syncSearchAskTimer();
    renderSearchAskThreadSelect();
    setButtonBusy(searchAskForm?.querySelector("button[type='submit']"), false);
  }
}

function autoResizeChatTextarea(el) {
  el.style.height = "auto";
  el.style.height = Math.min(el.scrollHeight, 200) + "px";
}

function bindSearchEvents() {
  if (searchEventsBound) {
    return;
  }
  searchKeywordForm?.addEventListener("submit", async (event) => {
    event.preventDefault();
    await runKeywordSearch();
  });

  searchAskForm?.addEventListener("submit", async (event) => {
    event.preventDefault();
    await runAsk();
  });

  searchAskNewChatBtn?.addEventListener("click", () => {
    resetSearchAskChat();
    logActivity("Ask Your Docs chat reset.");
  });

  searchAskThreadSearch?.addEventListener("input", () => {
    loadSearchAskThreads().catch((error) => {
      logActivity(`Chat history failed: ${error.message}`);
    });
  });

  searchAskThreadList?.addEventListener("click", async (event) => {
    const deleteButton = event.target instanceof Element ? event.target.closest("[data-delete-thread-id]") : null;
    if (deleteButton instanceof HTMLElement) {
      await deleteSearchAskThread(deleteButton.dataset.deleteThreadId || "");
      return;
    }
    const threadButton = event.target instanceof Element ? event.target.closest("[data-thread-id]") : null;
    if (threadButton instanceof HTMLElement) {
      await loadSearchAskThread(threadButton.dataset.threadId || "");
    }
  });

  searchAskQuestion?.addEventListener("keydown", async (event) => {
    if (event.key !== "Enter" || event.shiftKey || event.metaKey || event.ctrlKey || event.altKey) {
      return;
    }
    event.preventDefault();
    await runAsk();
  });

  searchAskQuestion?.addEventListener("input", () => autoResizeChatTextarea(searchAskQuestion));

  searchAskHints?.addEventListener("click", async (event) => {
    const hint = event.target instanceof Element ? event.target.closest("[data-ask-hint]") : null;
    if (!(hint instanceof HTMLElement) || !(searchAskQuestion instanceof HTMLTextAreaElement) || searchAskInFlight) {
      return;
    }
    searchAskQuestion.value = hint.dataset.askHint || "";
    autoResizeChatTextarea(searchAskQuestion);
    searchAskQuestion.focus();
    await runAsk();
  });

  searchAskMessages?.addEventListener("click", (event) => {
    const button = event.target instanceof Element ? event.target.closest(".chat-status-summary") : null;
    if (!(button instanceof HTMLElement)) {
      return;
    }
    const message = searchAskMessagesState.find((item) => item.id === button.dataset.messageId);
    if (!message) {
      return;
    }
    if (message.activity) {
      const roundIndex = Number(button.dataset.roundIndex || 0);
      const round = message.activityRounds.find((item) => Number(item.index) === roundIndex);
      if (!round || !round.details?.length) {
        return;
      }
      round.expanded = !round.expanded;
      renderSearchAskMessages();
      return;
    }
    if (!message.statusDetail) {
      return;
    }
    message.expanded = !message.expanded;
    renderSearchAskMessages();
  });

  searchEventsBound = true;
}

export async function initializePage({ authenticated }) {
  if (authenticated !== true) {
    return;
  }
  bindSearchElements();
  bindSearchEvents();
  await loadSearchAskThreads();
  renderSearchResultsMeta("Ready.");
}
