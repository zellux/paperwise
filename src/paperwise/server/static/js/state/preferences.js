export function normalizePageSize(value) {
  const size = Number(value);
  if (!Number.isInteger(size) || size <= 0) {
    return 20;
  }
  return size;
}

export function normalizeSortDirection(value) {
  const normalized = String(value || "").trim().toLowerCase();
  if (normalized === "asc" || normalized === "desc") {
    return normalized;
  }
  return "";
}

export function normalizeSortField(value, allowedFields) {
  const normalized = String(value || "").trim();
  if (allowedFields.has(normalized)) {
    return normalized;
  }
  return "";
}

export function normalizeSortState(value, allowedFields) {
  const field = normalizeSortField(value?.field, allowedFields);
  const direction = normalizeSortDirection(value?.direction);
  if (!field || !direction) {
    return { field: "", direction: "" };
  }
  return { field, direction };
}

export function getNextSortState(currentState, field) {
  if (currentState.field !== field || !currentState.direction) {
    return { field, direction: "asc" };
  }
  if (currentState.direction === "asc") {
    return { field, direction: "desc" };
  }
  return { field: "", direction: "" };
}

export function normalizeGroundedQaTopK(value) {
  const size = Number(value);
  if (!Number.isInteger(size)) {
    return 18;
  }
  return Math.max(2, Math.min(48, size));
}

export function normalizeGroundedQaMaxDocuments(value) {
  const size = Number(value);
  if (!Number.isInteger(size)) {
    return 12;
  }
  return Math.max(1, Math.min(24, size));
}

export function normalizeOcrImageDetail(value) {
  const normalized = String(value || "").trim().toLowerCase();
  if (["auto", "low", "high"].includes(normalized)) {
    return normalized;
  }
  return "auto";
}

export function normalizeOcrAutoSwitch(value) {
  if (typeof value === "boolean") {
    return value;
  }
  const normalized = String(value || "").trim().toLowerCase();
  return normalized === "true" || normalized === "1" || normalized === "on" || normalized === "yes";
}
