const searchKeywordForm = document.getElementById("searchKeywordForm");
const searchKeywordInput = document.getElementById("searchKeywordInput");
const searchKeywordLimitSelect = document.getElementById("searchKeywordLimitSelect");
const searchResultsMeta = document.getElementById("searchResultsMeta");
const searchResultsTableBody = document.getElementById("searchResultsTableBody");
const searchAskForm = document.getElementById("searchAskForm");
const searchAskQuestion = document.getElementById("searchAskQuestion");
const searchAskNewChatBtn = document.getElementById("searchAskNewChatBtn");
const searchAskThreadSearch = document.getElementById("searchAskThreadSearch");
const searchAskThreadList = document.getElementById("searchAskThreadList");
const searchAskTokenUsage = document.getElementById("searchAskTokenUsage");
const searchAskMessages = document.getElementById("searchAskMessages");

let searchAskMessagesState = [];
let searchAskInFlight = false;
let searchAskMessageSeq = 0;
let searchAskCurrentTokens = 0;
let searchAskTimerId = 0;
let searchAskThreadId = "";
let searchAskThreads = [];
let initialChatThreadsConsumed = false;

function normalizeChatThreadSummary(thread) {
  return {
    id: String(thread?.id || ""),
    title: String(thread?.title || "Untitled chat"),
    message_count: Number(thread?.message_count || 0),
    created_at: String(thread?.created_at || ""),
    updated_at: String(thread?.updated_at || ""),
  };
}

function renderSearchResultsMeta(message) {
  if (!searchResultsMeta) {
    return;
  }
  searchResultsMeta.textContent = message;
}

function renderSearchResultsTable(payload) {
  if (!searchResultsTableBody) {
    return;
  }
  const hits = Array.isArray(payload?.hits) ? payload.hits : [];
  if (!hits.length) {
    searchResultsTableBody.innerHTML = '<tr><td colspan="6">No matches found.</td></tr>';
    return;
  }
  searchResultsTableBody.innerHTML = "";
  for (const hit of hits) {
    const row = document.createElement("tr");

    const titleCell = document.createElement("td");
    titleCell.setAttribute("data-label", "Title");
    const titleBtn = document.createElement("button");
    titleBtn.type = "button";
    titleBtn.className = "link-button";
    titleBtn.textContent = hit.title || hit.filename || hit.document_id;
    titleBtn.addEventListener("click", () => navigateToDocument(hit.document_id));
    titleCell.appendChild(titleBtn);

    const typeCell = document.createElement("td");
    typeCell.setAttribute("data-label", "Type");
    typeCell.textContent = hit.document_type || "-";

    const correspondentCell = document.createElement("td");
    correspondentCell.setAttribute("data-label", "Correspondent");
    correspondentCell.textContent = hit.correspondent || "-";

    const tagsCell = document.createElement("td");
    tagsCell.setAttribute("data-label", "Tags");
    tagsCell.textContent = Array.isArray(hit.tags) && hit.tags.length ? hit.tags.join(", ") : "-";

    const scoreCell = document.createElement("td");
    scoreCell.setAttribute("data-label", "Score");
    scoreCell.textContent = Number(hit.score || 0).toFixed(3);

    const snippetCell = document.createElement("td");
    snippetCell.setAttribute("data-label", "Snippet");
    snippetCell.textContent = hit.snippet || "-";

    row.appendChild(titleCell);
    row.appendChild(typeCell);
    row.appendChild(correspondentCell);
    row.appendChild(tagsCell);
    row.appendChild(scoreCell);
    row.appendChild(snippetCell);
    searchResultsTableBody.appendChild(row);
  }
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

function formatElapsedTime(ms) {
  const totalSeconds = Math.max(0, Math.floor(Number(ms || 0) / 1000));
  const minutes = Math.floor(totalSeconds / 60);
  const seconds = totalSeconds % 60;
  if (minutes > 0) {
    return `${minutes}m ${seconds}s`;
  }
  return `${seconds}s`;
}

function getRoundElapsedLabel(round) {
  if (!round?.startedAt) {
    return "";
  }
  const end = round.endedAt || Date.now();
  return formatElapsedTime(end - round.startedAt);
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
  searchAskTokenUsage.textContent = `Tokens: ${formatTokenCount(searchAskCurrentTokens)}`;
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

function renderSearchAskThreadSelect() {
  syncSearchAskThreadSelect();
}

function applySearchAskThreadsPartial(payload) {
  searchAskThreads = Array.isArray(payload.chat_threads)
    ? payload.chat_threads.map(normalizeChatThreadSummary).filter((thread) => thread.id)
    : [];
  replaceElementHtml(searchAskThreadList, payload.thread_list_html);
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
    searchAskThreads = initialData.chat_threads
      .map(normalizeChatThreadSummary)
      .filter((thread) => thread.id);
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
    payload = await fetchUiPartial(`/ui/partials/chat-threads${suffix}`);
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
  const thread = searchAskThreads.find((item) => item.id === id);
  const title = thread?.title || "this chat";
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

function formatSearchAskJsonDetail(value) {
  try {
    return JSON.stringify(value || {}, null, 2);
  } catch {
    return String(value || "");
  }
}

function renderSearchAskStatusMessage(message, item) {
  const summaryButton = document.createElement("button");
  summaryButton.type = "button";
  summaryButton.className = "chat-status-summary";
  summaryButton.setAttribute("aria-expanded", message.expanded ? "true" : "false");
  summaryButton.dataset.messageId = message.id;

  const marker = document.createElement("span");
  marker.className = "chat-status-marker";
  marker.setAttribute("aria-hidden", "true");
  marker.textContent = message.expanded ? "v" : ">";

  const text = document.createElement("span");
  text.className = "chat-status-summary-text";
  text.textContent = message.statusSummary || message.content || "Working...";

  summaryButton.appendChild(marker);
  summaryButton.appendChild(text);
  item.appendChild(summaryButton);

  if (message.expanded && message.statusDetail) {
    const detail = document.createElement("pre");
    detail.className = "chat-status-detail";
    detail.textContent = message.statusDetail;
    item.appendChild(detail);
  }
}

function formatSearchAskRoundSummary(round) {
  const toolCount = Number(round.toolCallCount || 0);
  const resultCount = Number(round.resultCount || 0);
  const elapsed = getRoundElapsedLabel(round);
  const elapsedText = elapsed ? ` · ${elapsed}` : "";
  if (round.finalReady) {
    return `Round ${round.index}: answer ready${elapsedText}`;
  }
  if (toolCount > 0) {
    const resultText = resultCount > 0 ? `, ${resultCount} result(s)` : "";
    return `Round ${round.index}: ${toolCount} tool call(s)${resultText}${elapsedText}`;
  }
  return `Round ${round.index}: ${round.summary || "LLM request"}${elapsedText}`;
}

function renderSearchAskActivityMessage(message, item) {
  const rounds = message.activityRounds.length
    ? message.activityRounds
    : [{ index: 1, summary: message.statusSummary || message.content || "Working", details: [] }];
  for (const round of rounds) {
    const summaryButton = document.createElement("button");
    summaryButton.type = "button";
    summaryButton.className = "chat-status-summary";
    summaryButton.setAttribute("aria-expanded", round.expanded ? "true" : "false");
    summaryButton.dataset.messageId = message.id;
    summaryButton.dataset.roundIndex = String(round.index);

    const marker = document.createElement("span");
    marker.className = "chat-status-marker";
    marker.setAttribute("aria-hidden", "true");
    marker.textContent = round.expanded ? "v" : ">";

    const text = document.createElement("span");
    text.className = "chat-status-summary-text";
    text.textContent = formatSearchAskRoundSummary(round);

    summaryButton.appendChild(marker);
    summaryButton.appendChild(text);
    if (round.startedAt && !round.endedAt) {
      const live = document.createElement("span");
      live.className = "chat-status-live";
      live.setAttribute("aria-hidden", "true");
      summaryButton.appendChild(live);
    }
    item.appendChild(summaryButton);

    if (round.expanded && round.details?.length) {
      const detail = document.createElement("pre");
      detail.className = "chat-status-detail";
      detail.textContent = round.details.join("\n\n");
      item.appendChild(detail);
    }
  }
}

function renderChatCitations(message, item) {
  if (!Array.isArray(message.citations) || !message.citations.length) {
    return;
  }
  const details = document.createElement("details");
  details.className = "chat-citations";
  const summary = document.createElement("summary");
  summary.textContent = `Sources (${message.citations.length})`;
  details.appendChild(summary);

  const list = document.createElement("div");
  list.className = "chat-citation-list";
  for (const citation of message.citations) {
    const source = document.createElement("button");
    source.type = "button";
    source.className = "chat-citation-source";
    source.textContent = citation.title || citation.document_id || "Source";
    source.addEventListener("click", () => navigateToDocument(citation.document_id));
    list.appendChild(source);
  }
  details.appendChild(list);
  item.appendChild(details);
}

function getCurrentUserInitials() {
  const source = String(currentUser?.full_name || currentUser?.email || "You").trim();
  const parts = source
    .replace(/@.*/, "")
    .split(/[\s._-]+/)
    .filter(Boolean);
  const initials = parts.slice(0, 2).map((part) => part.charAt(0).toUpperCase()).join("");
  return initials || "Y";
}

function appendSearchAskRoleMeta(item, message) {
  const role = document.createElement("div");
  role.className = "chat-message-role";
  const dot = document.createElement("span");
  dot.className = "chat-role-dot";
  dot.textContent = message.role === "user" ? getCurrentUserInitials() : "P";
  const label = document.createElement("span");
  label.textContent = message.role === "user" ? "You" : "Paperwise";
  role.appendChild(dot);
  role.appendChild(label);
  item.appendChild(role);
}

function renderSearchAskMessages() {
  if (!searchAskMessages) {
    return;
  }
  const shouldStickToBottom =
    searchAskMessages.scrollHeight - searchAskMessages.scrollTop - searchAskMessages.clientHeight < 24;
  if (!searchAskMessagesState.length) {
    searchAskMessages.innerHTML = `
      <div class="chat-message chat-message-assistant">
        <div class="chat-message-role"><span class="chat-role-dot">P</span><span>Paperwise</span></div>
        <div class="chat-message-body markdown-output">Ask a question to begin.</div>
      </div>
    `;
    return;
  }
  searchAskMessages.innerHTML = "";
  for (const message of searchAskMessagesState) {
    const item = document.createElement("div");
    item.className = `chat-message chat-message-${message.role}`;
    if (message.statusKind) {
      item.classList.add(`chat-message-status-${message.statusKind}`);
    }
    if (message.role === "status") {
      if (message.activity) {
        renderSearchAskActivityMessage(message, item);
      } else {
        renderSearchAskStatusMessage(message, item);
      }
      searchAskMessages.appendChild(item);
      continue;
    }
    const body = document.createElement("div");
    body.className = "chat-message-body markdown-output";
    body.innerHTML = renderMarkdown(message.pending ? "Working..." : message.content || "No response.");
    appendSearchAskRoleMeta(item, message);
    item.appendChild(body);
    renderChatCitations(message, item);
    searchAskMessages.appendChild(item);
  }
  if (shouldStickToBottom) {
    searchAskMessages.scrollTop = searchAskMessages.scrollHeight;
  }
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

function clearSearchStateForSession() {
  searchAskMessagesState = [];
  searchAskMessageSeq = 0;
  searchAskCurrentTokens = 0;
  searchAskThreadId = "";
  searchAskThreads = [];
  initialChatThreadsConsumed = false;
  syncSearchAskTimer();
  renderSearchAskTokenUsage();
  renderSearchAskThreadSelect();
  replaceElementHtml(searchResultsTableBody, '<tr><td colspan="6">No matches found.</td></tr>');
  renderSearchResultsMeta("No search run yet.");
  renderSearchAskMessages();
}

function renderInlineMarkdown(text) {
  let rendered = escapeHtml(text);
  rendered = rendered.replace(/`([^`]+)`/g, "<code>$1</code>");
  rendered = rendered.replace(/\*\*([^*]+)\*\*/g, "<strong>$1</strong>");
  rendered = rendered.replace(/(^|[\s(])\*([^*]+)\*(?=$|[\s).,!?;:])/g, "$1<em>$2</em>");
  return rendered;
}

function flushMarkdownParagraph(buffer, html) {
  if (!buffer.length) {
    return;
  }
  html.push(`<p>${buffer.map((line) => renderInlineMarkdown(line)).join("<br>")}</p>`);
  buffer.length = 0;
}

function splitMarkdownTableRow(line) {
  const trimmed = String(line || "").trim();
  const normalized = trimmed.replace(/^\|/, "").replace(/\|$/, "");
  return normalized.split("|").map((cell) => cell.trim());
}

function isMarkdownTableSeparator(line) {
  const cells = splitMarkdownTableRow(line);
  if (!cells.length) {
    return false;
  }
  return cells.every((cell) => /^:?-{3,}:?$/.test(cell));
}

function renderMarkdownTable(headerLine, bodyLines) {
  const headers = splitMarkdownTableRow(headerLine);
  const bodyRows = bodyLines.map((line) => splitMarkdownTableRow(line));
  const thead = `<thead><tr>${headers.map((cell) => `<th>${renderInlineMarkdown(cell)}</th>`).join("")}</tr></thead>`;
  const tbody = `<tbody>${bodyRows
    .map((cells) => `<tr>${cells.map((cell) => `<td>${renderInlineMarkdown(cell)}</td>`).join("")}</tr>`)
    .join("")}</tbody>`;
  return `<table>${thead}${tbody}</table>`;
}

function getMarkdownListKind(line) {
  if (/^\s*[-*]\s+/.test(line)) {
    return "ul";
  }
  if (/^\s*\d+\.\s+/.test(line)) {
    return "ol";
  }
  return "";
}

function findNextNonEmptyMarkdownLine(lines, startIndex) {
  for (let index = startIndex; index < lines.length; index += 1) {
    const line = String(lines[index] || "").trim();
    if (line) {
      return line;
    }
  }
  return "";
}

function renderMarkdown(markdown) {
  const lines = String(markdown || "").replace(/\r\n/g, "\n").split("\n");
  const html = [];
  const paragraph = [];
  let listKind = "";

  const closeList = () => {
    if (listKind) {
      html.push(listKind === "ol" ? "</ol>" : "</ul>");
      listKind = "";
    }
  };

  for (let index = 0; index < lines.length; index += 1) {
    const rawLine = lines[index];
    const line = rawLine.trimEnd();
    const nextLine = index + 1 < lines.length ? lines[index + 1].trim() : "";
    const headingMatch = line.match(/^(#{1,3})\s+(.+)$/);
    const ulMatch = line.match(/^[-*]\s+(.+)$/);
    const olMatch = line.match(/^(\d+)\.\s+(.+)$/);
    const quoteMatch = line.match(/^>\s+(.+)$/);
    const looksLikeTable = line.includes("|") && nextLine.includes("|") && isMarkdownTableSeparator(nextLine);

    if (!line.trim()) {
      flushMarkdownParagraph(paragraph, html);
      const nextListKind = getMarkdownListKind(findNextNonEmptyMarkdownLine(lines, index + 1));
      if (listKind && nextListKind === listKind) {
        continue;
      }
      closeList();
      continue;
    }

    if (headingMatch) {
      closeList();
      flushMarkdownParagraph(paragraph, html);
      const level = headingMatch[1].length;
      html.push(`<h${level}>${renderInlineMarkdown(headingMatch[2])}</h${level}>`);
      continue;
    }

    if (quoteMatch) {
      closeList();
      flushMarkdownParagraph(paragraph, html);
      html.push(`<blockquote>${renderInlineMarkdown(quoteMatch[1])}</blockquote>`);
      continue;
    }

    if (looksLikeTable) {
      closeList();
      flushMarkdownParagraph(paragraph, html);
      const bodyLines = [];
      index += 2;
      while (index < lines.length) {
        const row = lines[index].trim();
        if (!row || !row.includes("|")) {
          index -= 1;
          break;
        }
        bodyLines.push(row);
        index += 1;
      }
      html.push(renderMarkdownTable(line, bodyLines));
      continue;
    }

    if (ulMatch) {
      flushMarkdownParagraph(paragraph, html);
      if (listKind !== "ul") {
        closeList();
        html.push("<ul>");
        listKind = "ul";
      }
      html.push(`<li>${renderInlineMarkdown(ulMatch[1])}</li>`);
      continue;
    }

    if (olMatch) {
      flushMarkdownParagraph(paragraph, html);
      if (listKind !== "ol") {
        closeList();
        const start = Number(olMatch[1] || 1);
        html.push(start > 1 ? `<ol start="${start}">` : "<ol>");
        listKind = "ol";
      }
      html.push(`<li>${renderInlineMarkdown(olMatch[2])}</li>`);
      continue;
    }

    closeList();
    paragraph.push(line);
  }

  closeList();
  flushMarkdownParagraph(paragraph, html);
  if (!html.length) {
    return "<p>No answer returned.</p>";
  }
  return html.join("");
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

function parseSearchAskStreamEvent(rawEvent) {
  const lines = String(rawEvent || "").split(/\r?\n/);
  let eventType = "message";
  const dataLines = [];
  for (const line of lines) {
    if (line.startsWith("event:")) {
      eventType = line.slice("event:".length).trim() || "message";
      continue;
    }
    if (line.startsWith("data:")) {
      dataLines.push(line.slice("data:".length).trimStart());
    }
  }
  const dataText = dataLines.join("\n");
  let data = {};
  if (dataText) {
    try {
      data = JSON.parse(dataText);
    } catch {
      data = { detail: dataText };
    }
  }
  return { eventType, data };
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
      appendSearchAskRoundDetail(round, "LLM response", formatSearchAskJsonDetail(data));
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
      appendSearchAskRoundDetail(round, `Tool call: ${data.name || "tool"}`, formatSearchAskJsonDetail(data.arguments || {}));
      renderSearchAskMessages();
    }
    return null;
  }
  if (eventType === "tool_result") {
    const resultCount = Number(data.result_count || 0);
    const round = getSearchAskActivityRound(activityMessage);
    if (round) {
      round.resultCount = Number(round.resultCount || 0) + resultCount;
      appendSearchAskRoundDetail(round, `Tool result: ${data.name || "tool"}`, formatSearchAskJsonDetail(data));
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
      const { eventType, data } = parseSearchAskStreamEvent(rawEvent);
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
    const { eventType, data } = parseSearchAskStreamEvent(buffer);
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
  const topK = normalizeGroundedQaTopK(groundedQaTopK);
  const maxDocuments = normalizeGroundedQaMaxDocuments(groundedQaMaxDocuments);
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

async function initializeSearchView() {
  await loadSearchAskThreads();
  renderSearchResultsMeta("Ready.");
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

function autoResizeChatTextarea(el) {
  el.style.height = "auto";
  el.style.height = Math.min(el.scrollHeight, 200) + "px";
}

if (searchAskQuestion) {
  searchAskQuestion.addEventListener("input", () => autoResizeChatTextarea(searchAskQuestion));
}

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
