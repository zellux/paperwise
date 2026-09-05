import { renderMarkdown } from "./markdown.js";
import { linkInlineCitations, openEvidence } from "./evidence.js";
import { scopeLabel } from "./scope.js";
import { answerExportText, tableExportRows, downloadCsv, copyText } from "./exports.js";

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

function renderStatusMessage(message, item) {
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

function formatRoundSummary(round) {
  const toolCount = Number(round.toolCallCount || 0);
  const resultCount = Number(round.resultCount || 0);
  const elapsed = getRoundElapsedLabel(round);
  const elapsedText = elapsed ? ` · ${elapsed}` : "";
  if (round.finalReady) return `Answer ready${elapsedText}`;
  if (round.endedAt && round.stopped) return `Stopped${elapsedText}`;
  if (resultCount > 0) return `Reviewing retrieved evidence${elapsedText}`;
  if (toolCount > 0) return `Finding relevant documents${elapsedText}`;
  return `${round.stage || "Searching your documents"}${elapsedText}`;
}

function renderActivityMessage(message, item) {
  const rounds = message.activityRounds.length
    ? message.activityRounds
    : [{ index: 1, summary: message.statusSummary || message.content || "Working", details: [] }];
  for (const round of rounds.slice(-1)) {
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
    text.textContent = formatRoundSummary(round);

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
      detail.textContent = rounds.flatMap((item) => item.details || []).join("\n\n");
      item.appendChild(detail);
    }
  }
}

function renderCitations(message, item, navigateToDocument) {
  if (!Array.isArray(message.citations) || !message.citations.length) {
    return;
  }
  const details = document.createElement("details");
  details.className = "chat-citations";
  details.open = true;
  const summary = document.createElement("summary");
  summary.textContent = `Evidence (${message.citations.length})`;
  details.appendChild(summary);

  const list = document.createElement("div");
  list.className = "chat-citation-list";
  for (const [index, citation] of message.citations.entries()) {
    const source = document.createElement("button");
    source.type = "button";
    source.className = "chat-citation-source";
    source.textContent = `[${index + 1}] ${citation.title || "Source"}${citation.cited ? "" : " · retrieved"}`;
    source.addEventListener("click", () => openEvidence(citation, index + 1, source));
    list.appendChild(source);
  }
  details.appendChild(list);
  item.appendChild(details);
}

function getCurrentUserInitials(currentUser) {
  const source = String(currentUser?.full_name || currentUser?.email || "You").trim();
  const parts = source
    .replace(/@.*/, "")
    .split(/[\s._-]+/)
    .filter(Boolean);
  const initials = parts.slice(0, 2).map((part) => part.charAt(0).toUpperCase()).join("");
  return initials || "Y";
}

function appendRoleMeta(item, message, currentUser) {
  const role = document.createElement("div");
  role.className = "chat-message-role";
  const dot = document.createElement("span");
  dot.className = "chat-role-dot";
  dot.textContent = message.role === "user" ? getCurrentUserInitials(currentUser) : "P";
  const label = document.createElement("span");
  label.textContent = message.role === "user" ? "You" : "Paperwise";
  role.appendChild(dot);
  role.appendChild(label);
  item.appendChild(role);
}

export function renderChatTranscript({ container, messages, currentUser, navigateToDocument, onEdit, onRetry, onBroaden, busy = false }) {
  if (!container) {
    return;
  }
  const shouldStickToBottom =
    container.scrollHeight - container.scrollTop - container.clientHeight < 24;
  if (!messages.length) {
    container.innerHTML = `
      <div class="chat-message chat-message-assistant">
        <div class="chat-message-role"><span class="chat-role-dot">P</span><span>Paperwise</span></div>
        <div class="chat-message-body markdown-output">Ask a question to begin.</div>
      </div>
    `;
    return;
  }
  container.innerHTML = "";
  for (const message of messages) {
    const item = document.createElement("div");
    item.className = `chat-message chat-message-${message.role}`;
    if (message.statusKind) {
      item.classList.add(`chat-message-status-${message.statusKind}`);
    }
    if (message.role === "status") {
      if (message.activity) {
        renderActivityMessage(message, item);
      } else {
        renderStatusMessage(message, item);
      }
      container.appendChild(item);
      continue;
    }
    const body = document.createElement("div");
    body.className = "chat-message-body markdown-output";
    const visibleContent = message.pending ? String(message.content || "").replace(/\[\[(?:source|citation):[^\]\n]*(?:\]\])?/g, "[source]") || "Finding evidence for your answer…" : message.content || "No response.";
    body.innerHTML = renderMarkdown(visibleContent);
    if (message.error || message.stopped) item.classList.add("chat-message-error");
    if (!message.pending) linkInlineCitations(body, message.citations || []);
    body.querySelectorAll("table").forEach((table) => {
      const scroll = document.createElement("div");
      scroll.className = "chat-table-scroll";
      table.before(scroll);
      scroll.append(table);
    });
    appendRoleMeta(item, message, currentUser);
    item.appendChild(body);
    if (message.role === "user" && message.scope) {
      const scope = document.createElement("small");
      scope.className = "chat-answer-scope";
      scope.textContent = scopeLabel(message.scope);
      item.append(scope);
    }
    renderCitations(message, item, navigateToDocument);
    if (!message.pending && message.role === "assistant" && message.coverage && !message.error && !message.stopped) {
      renderCoverage(message, item);
    }
    if (!message.pending) {
      const actions = document.createElement("div");
      actions.className = "chat-answer-actions";
      const status = document.createElement("span");
      status.setAttribute("role", "status");
      const addAction = (label, action, disabled = false) => {
        const button = document.createElement("button");
        button.type = "button";
        button.className = "btn";
        button.textContent = label;
        button.disabled = disabled;
        button.addEventListener("click", action);
        actions.append(button);
      };
      const latestUser = messages.filter((m) => m.role === "user").at(-1);
      if (message === latestUser && onEdit) addAction("Edit question", () => onEdit(message), busy);
      if (message.role === "assistant") {
        if (message.error || message.stopped) {
          if (onRetry && message === messages.filter((m) => m.role === "assistant").at(-1)) addAction("Retry question", () => onRetry(message), busy);
          if (onEdit && latestUser) addAction("Edit question", () => onEdit(latestUser), busy);
        } else {
          addAction("Copy answer", () => copyText(answerExportText(message), status));
          body.querySelectorAll("table").forEach((table, index) => {
            const label = index ? ` ${index + 1}` : "";
            addAction(`Copy table${label}`, () => copyText(tableExportRows(table, message).map((row) => row.join("\t")).join("\n"), status));
            addAction(`Download CSV${label}`, () => downloadCsv(tableExportRows(table, message)));
          });
          if (!message.citations?.length && !message.coverage?.metadata_documents && onBroaden) addAction("Broaden scope", () => onBroaden(message), busy);
        }
      }
      actions.append(status);
      if (actions.children.length > 1) item.append(actions);
    }
    container.appendChild(item);
  }
  if (shouldStickToBottom) {
    container.scrollTop = container.scrollHeight;
  }
}

function renderCoverage(message, item) {
  const coverage = message.coverage;
  const details = document.createElement("details");
  details.className = "chat-coverage";
  const summary = document.createElement("summary");
  const searches = coverage.searches || [];
  const scoped = searches[0]?.scope_documents;
  summary.textContent = `${scoped == null ? "" : `${scoped} in scope · `}${coverage.retrieved_documents || 0} documents with text evidence${coverage.metadata_documents ? ` · ${coverage.metadata_documents} metadata records` : ""} · ${coverage.cited_documents || 0} cited · Completeness not verified`;
  const description = document.createElement("p");
  const unavailable = Math.max(0, ...searches.map((search) => Number(search.unready_documents || 0)));
  description.textContent = `${scopeLabel(message.scope)}. Answers use retrieved excerpts, not an exhaustive review. Totals should be treated as subtotals. ${unavailable ? `${unavailable} documents in a searched scope are processing or need attention. ` : ""}${coverage.limited ? "Retrieval limits were reached; some evidence may be omitted." : "Missing periods and duplicate documents have not been checked."}`;
  details.append(summary, description);
  for (const [index, search] of searches.entries()) {
    if (!search.filters || !Object.keys(search.filters).length) continue;
    const filters = document.createElement("p");
    filters.textContent = `Search ${index + 1} narrowed to: ${Object.entries(search.filters).map(([key, value]) => `${key.replaceAll("_", " ")}: ${Array.isArray(value) ? value.join(", ") : value}`).join(" · ")}`;
    details.append(filters);
  }
  item.append(details);
}
