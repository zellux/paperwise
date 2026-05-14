import { readInitialData } from "../state/initialData.js";

const FALLBACK_TAG_COLOR_SET = [
  "#8e5bcb",
  "#1d6a55",
  "#b0552f",
  "#c47a2a",
  "#2c6488",
  "#7a5c2e",
  "#8b4778",
  "#3d7a66",
  "#9f4a28",
  "#4f6f9f",
  "#6b5b95",
  "#2f7a8a",
];

export function tagColorSet() {
  const palette = readInitialData().tag_color_set;
  if (!Array.isArray(palette) || palette.length === 0) {
    return FALLBACK_TAG_COLOR_SET;
  }
  return palette.map((color) => String(color || "").trim()).filter(Boolean);
}

export function stableTagColor(value) {
  const normalized = String(value || "").trim().toLowerCase();
  if (!normalized) {
    return "#7c8783";
  }
  let hashValue = 0;
  for (const char of normalized) {
    hashValue = ((hashValue * 33) + char.codePointAt(0)) % 2147483647;
  }
  const palette = tagColorSet();
  return palette[hashValue % palette.length] || "#7c8783";
}
