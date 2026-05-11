export async function apiFetch(url, options = {}) {
  const headers = new Headers(options.headers || {});
  const allowUnauthorized = options.allowUnauthorized === true;
  const { allowUnauthorized: _allowUnauthorized, ...fetchOptions } = options;
  const response = await window.fetch(url, { credentials: "same-origin", ...fetchOptions, headers });
  if (response.status === 401 && !allowUnauthorized) {
    clearSession();
    throw new Error("Authentication required");
  }
  return response;
}

export async function fetchHtmlPartial(url) {
  const response = await apiFetch(url, { headers: { Accept: "text/html" } });
  const html = await response.text();
  if (!response.ok) {
    throw new Error(html.trim() || response.statusText);
  }
  return parseHtmlPartial(html);
}

export function parseHtmlPartial(html) {
  const template = document.createElement("template");
  template.innerHTML = String(html || "").trim();
  const root = template.content.firstElementChild;
  return root instanceof HTMLElement ? root : document.createElement("div");
}

export function replaceElementHtml(element, html) {
  if (!element) {
    return;
  }
  element.innerHTML = String(html || "");
}

export function renderTableLoading(tbody, colspan, message) {
  if (!tbody) {
    return;
  }
  tbody.innerHTML = `<tr><td colspan="${colspan}">${message}</td></tr>`;
}

export async function loadTablePartial({ url, tbody, loadingColspan, loadingMessage }) {
  renderTableLoading(tbody, loadingColspan, loadingMessage);
  return fetchHtmlPartial(url);
}

export function getPartialTemplate(partialRoot, targetId, attribute = "data-partial-target") {
  if (!(partialRoot instanceof Element) || !targetId) {
    return null;
  }
  return Array.from(partialRoot.querySelectorAll(`template[${attribute}]`)).find(
    (template) => template.getAttribute(attribute) === targetId,
  ) || null;
}

export function applyHtmlPartialTarget(target, partialRoot, attribute = "data-partial-target") {
  if (!target) {
    return;
  }
  const template = getPartialTemplate(partialRoot, target.id, attribute);
  replaceElementHtml(target, template ? template.innerHTML : "");
}

export function applyTableBodyPartial(tbody, partialRoot) {
  applyHtmlPartialTarget(tbody, partialRoot);
}
