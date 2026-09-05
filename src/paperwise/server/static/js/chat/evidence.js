import { apiFetch } from "../shared.js";

let sourceRequest = 0;
let sourceTrigger = null;

export function closeEvidence() {
  sourceRequest += 1;
  const panel = document.getElementById("chatEvidence");
  if (panel) panel.hidden = true;
  if (sourceTrigger?.isConnected) sourceTrigger.focus();
}

export async function openEvidence(citation, number, trigger) {
  const panel = document.getElementById("chatEvidence");
  if (!panel) return;
  const request = ++sourceRequest;
  sourceTrigger = trigger;
  panel.hidden = false;
  const title = panel.querySelector("h3");
  const quote = panel.querySelector("blockquote");
  const status = panel.querySelector("[data-evidence-status]");
  const link = panel.querySelector("a");
  title.textContent = `[${number}] ${citation.title || "Source document"}`;
  quote.textContent = citation.quote || "No saved excerpt.";
  status.textContent = "Checking the current source…";
  const url = new URL("/ui/document", window.location.origin);
  url.searchParams.set("id", citation.document_id);
  url.searchParams.set("quote", (citation.quote || "").split("\n").find((line) => line.trim())?.slice(0, 160) || "");
  link.href = url.pathname + url.search;
  panel.querySelector("button").focus();
  try {
    const response = await apiFetch(`/query/chat/evidence/${encodeURIComponent(citation.document_id)}/${encodeURIComponent(citation.chunk_id)}`);
    const payload = await response.json();
    if (request !== sourceRequest) return;
    if (!response.ok) throw new Error(payload.detail || "Source unavailable.");
    quote.textContent = payload.content;
    url.searchParams.set("quote", payload.content.split("\n").find((line) => line.trim())?.slice(0, 160) || "");
    link.href = url.pathname + url.search;
    status.textContent = "Original extracted text. Open the document to see the highlighted passage.";
  } catch (error) {
    if (request === sourceRequest) status.textContent = `${error.message} Showing the excerpt saved with this answer.`;
  }
}

export function bindEvidence() {
  document.getElementById("chatEvidenceClose")?.addEventListener("click", closeEvidence);
  document.getElementById("chatEvidence")?.addEventListener("keydown", (event) => {
    if (event.key === "Escape") closeEvidence();
  });
}

export function linkInlineCitations(body, citations) {
  const walker = document.createTreeWalker(body, NodeFilter.SHOW_TEXT);
  const nodes = [];
  while (walker.nextNode()) nodes.push(walker.currentNode);
  for (const node of nodes) {
    if (node.parentElement?.closest("code, pre")) continue;
    const text = node.textContent;
    const matches = [...text.matchAll(/\[\[citation:(\d+)\]\]/g)];
    if (!matches.length) continue;
    const fragment = document.createDocumentFragment();
    let cursor = 0;
    for (const match of matches) {
      fragment.append(text.slice(cursor, match.index));
      const number = Number(match[1]);
      const citation = citations[number - 1];
      if (citation?.cited) {
        const button = document.createElement("button");
        button.type = "button";
        button.className = "chat-inline-citation";
        button.textContent = `[${number}]`;
        button.setAttribute("aria-label", `View source ${number}: ${citation.title}`);
        button.addEventListener("click", () => openEvidence(citation, number, button));
        fragment.append(button);
      } else {
        fragment.append("[source unavailable]");
      }
      cursor = match.index + match[0].length;
    }
    fragment.append(text.slice(cursor));
    node.replaceWith(fragment);
  }
}
