async function apiFetch(url, options = {}) {
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

async function fetchUiPartial(url) {
  const response = await apiFetch(url);
  const payload = await response.json();
  if (!response.ok) {
    throw new Error(payload.detail || response.statusText);
  }
  return payload;
}

function replaceElementHtml(element, html) {
  if (!element) {
    return;
  }
  element.innerHTML = String(html || "");
}

function renderTableLoading(tbody, colspan, message) {
  if (!tbody) {
    return;
  }
  tbody.innerHTML = `<tr><td colspan="${colspan}">${message}</td></tr>`;
}

async function loadTablePartial({ url, tbody, loadingColspan, loadingMessage }) {
  renderTableLoading(tbody, loadingColspan, loadingMessage);
  return fetchUiPartial(url);
}

function applyTableBodyPartial(tbody, payload) {
  replaceElementHtml(tbody, payload?.table_body_html);
}
