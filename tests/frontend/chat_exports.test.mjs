import test from "node:test";
import assert from "node:assert/strict";
import { answerExportText, rowsToCsv } from "../../src/paperwise/server/static/js/chat/exports.js";
import { scopeLabel } from "../../src/paperwise/server/static/js/chat/scope.js";

test("CSV preserves quotes and multiline evidence and escapes spreadsheet formulas", () => {
  assert.equal(rowsToCsv([["A,B", 'He said "yes"', "line 1\nline 2", "=SUM(A1)", "+cmd", "@cmd", "正常"]]),
    '"A,B","He said ""yes""","line 1\nline 2","\'=SUM(A1)","\'+cmd","\'@cmd","正常"');
});

test("copied answers retain scope, coverage limits, numbered sources and original excerpts", () => {
  const text = answerExportText({ content: "Total $52 [[citation:1]]", scope: {tag:["Utilities"], date_from:"2026-01-01"}, coverage: {retrieved_documents:1}, citations:[{title:"Invoice", document_id:"doc-1", quote:"Amount $52"}] });
  assert.ok(text.includes("Total $52 [1]"));
  assert.ok(text.includes("Utilities"));
  assert.ok(text.includes("2026-01-01"));
  assert.ok(text.includes("Completeness has not been verified"));
  assert.ok(text.includes("[1] Invoice\nAmount $52\nDocument: doc-1"));
});

test("scope labels distinguish all documents from explicit filters", () => {
  assert.equal(scopeLabel(), "All documents");
  assert.equal(scopeLabel({tag:["Medical"], document_type:["Bill"], correspondent:["Clinic"], date_from:"2026-01-01",date_to:"2026-03-31"}), "Tag: Medical · Type: Bill · From: Clinic · 2026-01-01 → 2026-03-31");
});
