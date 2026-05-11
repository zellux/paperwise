import { escapeHtml } from "../ui/escape.js";

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

export function renderMarkdown(markdown) {
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
