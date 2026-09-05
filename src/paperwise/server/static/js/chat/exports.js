import { scopeLabel } from "./scope.js";

export function answerExportText(message) {
  const answer = String(message.content || "").replace(/\[\[citation:(\d+)\]\]/g, "[$1]");
  const sources = (message.citations || []).map((c, index) => `[${index + 1}] ${c.title}\n${c.quote || ""}\nDocument: ${c.document_id}`);
  const coverage = message.coverage;
  return [answer, `Scope: ${scopeLabel(message.scope)}`, coverage ? `${coverage.retrieved_documents} documents retrieved. Completeness has not been verified.` : "", sources.length ? `Sources\n${sources.join("\n\n")}` : ""].filter(Boolean).join("\n\n");
}
export function csvCell(value) {
  const text = String(value ?? "");
  const safe = /^[\s]*[=+@-]/.test(text) || /^[\t\r]/.test(text) ? `'${text}` : text;
  return `"${safe.replaceAll('"', '""')}"`;
}
export function tableExportRows(table, message) {
  const rows = [...table.rows].map((row) => [...row.cells].map((cell) => cell.textContent));
  rows.push([], ["Scope", scopeLabel(message.scope)], ["Coverage", "Based on retrieved evidence; completeness not verified."], [], ["Source", "Document", "Excerpt"]);
  (message.citations || []).forEach((c, index) => rows.push([`[${index + 1}] ${c.title}`, c.document_id, c.quote || ""]));
  return rows;
}
export function rowsToCsv(rows) {
  return rows.map((row) => row.map(csvCell).join(",")).join("\r\n");
}
export function downloadCsv(rows) {
  const blob = new Blob(["\uFEFF", rowsToCsv(rows)], { type: "text/csv;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = "paperwise-answer.csv";
  document.body.append(link);
  link.click();
  link.remove();
  window.setTimeout(() => URL.revokeObjectURL(url), 1000);
}
export async function copyText(text, status) {
  try {
    await navigator.clipboard.writeText(text);
    status.textContent = "Copied";
  } catch {
    status.textContent = "Copy unavailable. Select the answer text to copy it.";
  }
}
