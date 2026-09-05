import { apiFetch } from "../shared.js";

const fields = { tag: "chatScopeTag", document_type: "chatScopeType", correspondent: "chatScopeCorrespondent", date_from: "chatScopeFrom", date_to: "chatScopeTo" };
export function readScope() {
  const result = {};
  for (const [key, id] of Object.entries(fields)) {
    const value = document.getElementById(id)?.value || "";
    result[key] = key.startsWith("date_") ? value || null : value ? [value] : [];
  }
  return result;
}
export function scopeLabel(scope = {}) {
  const labels = [...(scope.tag || []).map((v) => `Tag: ${v}`), ...(scope.document_type || []).map((v) => `Type: ${v}`), ...(scope.correspondent || []).map((v) => `From: ${v}`)];
  if (scope.date_from || scope.date_to) labels.push(`${scope.date_from || "Any date"} → ${scope.date_to || "Today and later"}`);
  return labels.join(" · ") || "All documents";
}
export function updateScopeSummary() {
  const label = scopeLabel(readScope());
  for (const id of ["chatScopeSummary", "chatScopeChips"]) {
    const element = document.getElementById(id);
    if (element) element.textContent = label;
  }
  const from = document.getElementById(fields.date_from);
  const to = document.getElementById(fields.date_to);
  to?.setCustomValidity(from?.value && to.value && from.value > to.value ? "End date must be on or after start date." : "");
}
export function restoreScope(scope = {}) {
  for (const [key, id] of Object.entries(fields)) {
    const el = document.getElementById(id);
    if (!el) continue;
    const value = key.startsWith("date_") ? scope[key] || "" : scope[key]?.[0] || "";
    if (el instanceof HTMLSelectElement && value && ![...el.options].some((o) => o.value === value)) el.add(new Option(value, value));
    el.value = value;
  }
  updateScopeSummary();
}
export function bindScope() {
  document.getElementById("chatScopeFields")?.addEventListener("change", updateScopeSummary);
  document.getElementById("chatScopeClear")?.addEventListener("click", () => restoreScope());
  updateScopeSummary();
}
export async function loadLibraryPrompts() {
  const status = document.getElementById("chatLibraryStatus");
  const prompts = document.getElementById("chatLibraryPrompts");
  if (!status || !prompts) return;
  try {
    const response = await apiFetch("/query/chat/library");
    if (!response.ok) throw new Error("Library information is unavailable. You can still ask a question.");
    const library = await response.json();
    for (const [key, id] of [["tags", fields.tag], ["document_types", fields.document_type], ["correspondents", fields.correspondent]]) {
      const select = document.getElementById(id);
      for (const item of library[key] || []) {
        if (item.name && ![...select.options].some((o) => o.value === item.name)) select.add(new Option(`${item.name} (${item.document_count})`, item.name));
      }
    }
    const total = library.scope_documents;
    const pending = library.unready_documents;
    status.textContent = total === 0 ? "Your library is empty. Upload documents to start asking questions." : pending === total ? `${total} documents are still processing or need attention. Answers may not have usable text yet.` : `${total} documents in your library${pending ? ` · ${pending} processing or needing attention` : ""}. Choose a question to edit, then ask.`;
    document.getElementById("chatLibraryUpload").hidden = total > 0;
    const questions = [];
    const correspondent = library.correspondents?.find((item) => item.name && item.document_count > 1);
    const type = library.document_types?.find((item) => item.name);
    const tag = library.tags?.find((item) => item.name);
    if (total && pending !== total) {
      if (correspondent) questions.push(["Compare documents", `Compare my most recent documents from ${correspondent.name}. Show key differences and cite the evidence.`]);
      if (type) questions.push(["Summarize a document type", `Summarize my ${type.name} documents. Highlight key dates and amounts, where available, with sources.`]);
      if (tag) questions.push(["Explore a topic", `What do my documents tagged "${tag.name}" say? Summarize the key points with sources.`]);
      if (!questions.length) questions.push(["Explore your library", "List my most recent documents and their dates."]);
    }
    prompts.replaceChildren();
    for (const [label, question] of questions.slice(0, 3)) {
      const button = document.createElement("button");
      button.type = "button";
      button.className = "ask-hint-card";
      button.dataset.askHint = question;
      const text = document.createElement("span");
      const strong = document.createElement("strong");
      strong.textContent = label;
      const small = document.createElement("small");
      small.textContent = question;
      text.append(strong, small);
      button.append(text);
      prompts.append(button);
    }
  } catch (error) {
    status.textContent = error.message;
  }
}
