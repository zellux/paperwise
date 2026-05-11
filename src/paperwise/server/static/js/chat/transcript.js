import { renderMarkdown } from "./markdown.js";

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
  if (round.finalReady) {
    return `Round ${round.index}: answer ready${elapsedText}`;
  }
  if (toolCount > 0) {
    const resultText = resultCount > 0 ? `, ${resultCount} result(s)` : "";
    return `Round ${round.index}: ${toolCount} tool call(s)${resultText}${elapsedText}`;
  }
  return `Round ${round.index}: ${round.summary || "LLM request"}${elapsedText}`;
}

function renderActivityMessage(message, item) {
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
      detail.textContent = round.details.join("\n\n");
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

export function renderChatTranscript({ container, messages, currentUser, navigateToDocument }) {
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
    body.innerHTML = renderMarkdown(message.pending ? "Working..." : message.content || "No response.");
    appendRoleMeta(item, message, currentUser);
    item.appendChild(body);
    renderCitations(message, item, navigateToDocument);
    container.appendChild(item);
  }
  if (shouldStickToBottom) {
    container.scrollTop = container.scrollHeight;
  }
}
