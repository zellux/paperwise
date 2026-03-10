from typing import Any

SYSTEM_PROMPT = (
    "You extract metadata for scanned documents. "
    "Return strict JSON with keys: suggested_title, document_date, "
    "correspondent, document_type, tags, language. "
    "document_date must be YYYY-MM-DD or null. "
    "If multiple dates are present, select the date most relevant to the document itself "
    "(typically issue/statement date over due/payment dates unless context strongly indicates otherwise). "
    "language must be a BCP-47 style language code such as 'en' or 'de'; use 'und' if unclear. "
    "correspondent must be the sender/issuer of the document "
    "(for example bank, utility, insurer, lab, credit bureau, clinic), "
    "not the recipient/customer. "
    "If sender is ambiguous, choose the strongest issuer signal from letterhead, "
    "logo, signature block, or footer and avoid generic placeholders. "
    "Correspondent must use the shortest clear organization form "
    "(for example 'Amazon' instead of long legal entity suffixes). "
    "If a current correspondent/document_type is already provided and is plausible, "
    "keep it unchanged. Only update when it is clearly wrong, contradicts the document, "
    "or is an unknown placeholder (for example: Unknown Sender, Unknown, General Document). "
    "tags must be an array of 1 to 5 strings and prioritize existing tags when relevant. "
    "Use natural casing: title case for normal words, but preserve acronyms in uppercase "
    "(for example: PPMG Pediatrics, IRS Notice). "
    "Keep original casing when already meaningful; only normalize when text is all lowercase. "
    "When reusing existing taxonomy names, copy the existing names exactly."
)

USER_GUIDANCE = (
    "Prefer existing taxonomy names when appropriate. "
    "Only propose new names when no existing option is a good match. "
    "Return 1 to 5 tags maximum. "
    "For correspondent/document_type, keep current values by default. "
    "Change only when clearly incorrect or when current values are unknown placeholders "
    "(for example 'Unknown Sender', 'Unknown', 'General Document'). "
    "Use title case for normal words in document_type/tags, "
    "but keep acronyms uppercase (for example: PPMG Pediatrics, IRS). "
    "Keep original casing when already meaningful; only normalize casing when all words are lowercase. "
    "For correspondent: normalize punctuation/suffixes (e.g. 'Experian.' -> 'Experian'), "
    "prefer the shortest organization name over legal suffixes/departments, "
    "and never return the document owner. "
    "For document_date: choose the most document-relevant date when multiple are present."
)


def build_user_prompt(
    *,
    filename: str,
    text_preview: str,
    current_correspondent: str | None,
    current_document_type: str | None,
    existing_correspondents: list[str],
    existing_document_types: list[str],
    existing_tags: list[str],
) -> dict[str, Any]:
    return {
        "filename": filename,
        "text_preview": text_preview,
        "current_correspondent": current_correspondent,
        "current_document_type": current_document_type,
        "existing_correspondents": existing_correspondents,
        "existing_document_types": existing_document_types,
        "existing_tags": existing_tags,
        "guidance": USER_GUIDANCE,
    }


def extract_metadata_result(parsed: dict[str, Any]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    suggested_title = parsed.get("suggested_title")
    if isinstance(suggested_title, str) and suggested_title.strip():
        result["suggested_title"] = suggested_title.strip()
    if "document_date" in parsed:
        result["document_date"] = parsed.get("document_date")
    correspondent = parsed.get("correspondent")
    if isinstance(correspondent, str) and correspondent.strip():
        result["correspondent"] = correspondent.strip()
    document_type = parsed.get("document_type")
    if isinstance(document_type, str) and document_type.strip():
        result["document_type"] = document_type.strip()
    tags = parsed.get("tags")
    if isinstance(tags, list):
        result["tags"] = [str(tag) for tag in tags if str(tag).strip()]
    return result
