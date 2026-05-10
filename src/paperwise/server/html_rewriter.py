from html import escape
import re

_TABLE_BODY_RE_TEMPLATE = (
    r'(<tbody id="{element_id}"[^>]*>)'
    r'.*?'
    r'(</tbody>)'
)
_ACTIVITY_TOKEN_RE = re.compile(
    r'(<p id="activityTokenTotal" class="activity-token-total">)'
    r'.*?'
    r"(</p>)",
    re.DOTALL,
)
_NAV_LINK_RE = re.compile(
    r'(<a\b(?=[^>]*\bclass="(?P<class>[^"]*\bnav-link\b[^"]*)")'
    r'(?=[^>]*\bhref="(?P<href>[^"]+)")[^>]*>)',
    re.DOTALL,
)


def replace_table_body(html: str, element_id: str, rows_html: str) -> str:
    pattern = re.compile(_TABLE_BODY_RE_TEMPLATE.format(element_id=re.escape(element_id)), re.DOTALL)
    return pattern.sub(rf"\1\n{rows_html}\n              \2", html, count=1)


def replace_element_text(html: str, element_id: str, value: str) -> str:
    pattern = re.compile(
        rf'(<(?P<tag>[a-z0-9]+)\b[^>]*\bid="{re.escape(element_id)}"[^>]*>).*?(</(?P=tag)>)',
        re.DOTALL | re.IGNORECASE,
    )
    escaped_value = escape(value)
    return pattern.sub(lambda match: f"{match.group(1)}{escaped_value}{match.group(3)}", html, count=1)


def replace_element_html(html: str, element_id: str, value: str) -> str:
    pattern = re.compile(
        rf'(<(?P<tag>[a-z0-9]+)\b[^>]*\bid="{re.escape(element_id)}"[^>]*>).*?(</(?P=tag)>)',
        re.DOTALL | re.IGNORECASE,
    )
    return pattern.sub(lambda match: f"{match.group(1)}{value}{match.group(3)}", html, count=1)


def replace_input_value(html: str, element_id: str, value: str) -> str:
    pattern = re.compile(
        rf'(<input\b(?=[^>]*\bid="{re.escape(element_id)}")[^>]*)(\s*/?>)',
        re.DOTALL | re.IGNORECASE,
    )
    escaped_value = escape(value, quote=True)

    def replace(match: re.Match[str]) -> str:
        start = re.sub(r'\svalue="[^"]*"', "", match.group(1), count=1)
        return f'{start} value="{escaped_value}"{match.group(2)}'

    return pattern.sub(replace, html, count=1)


def replace_activity_token_total(html: str, total_tokens: int) -> str:
    return _ACTIVITY_TOKEN_RE.sub(
        rf"\1LLM tokens processed: {int(total_tokens or 0):,}\2",
        html,
        count=1,
    )


def render_active_nav(html: str, active_href: str) -> str:
    def replace_link(match: re.Match[str]) -> str:
        tag = match.group(0)
        original_classes = match.group("class")
        classes = [class_name for class_name in original_classes.split() if class_name != "active"]
        if match.group("href") == active_href:
            classes.append("active")
        return tag.replace(f'class="{original_classes}"', f'class="{" ".join(classes)}"', 1)

    return _NAV_LINK_RE.sub(replace_link, html)
