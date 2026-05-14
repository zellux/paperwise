TAG_COLOR_SET = (
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
)


def stable_tag_color(value: str) -> str:
    normalized = str(value or "").strip().casefold()
    if not normalized:
        return "#7c8783"
    hash_value = 0
    for char in normalized:
        hash_value = ((hash_value * 33) + ord(char)) % 2147483647
    return TAG_COLOR_SET[hash_value % len(TAG_COLOR_SET)]
