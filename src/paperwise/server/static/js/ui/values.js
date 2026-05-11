export function splitTags(value) {
  return value
    .split(",")
    .map((part) => part.trim())
    .filter((part) => part.length > 0);
}

export function unique(values) {
  return [...new Set(values.filter((item) => item && item.trim()))];
}

export function sortValues(values) {
  return [...values].sort((a, b) => a.localeCompare(b, undefined, { sensitivity: "base" }));
}
