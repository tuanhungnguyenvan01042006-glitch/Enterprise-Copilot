"""Extract useful text from raw HTML while retaining surrounding Markdown."""

from __future__ import annotations

import re

from bs4 import BeautifulSoup, Comment, NavigableString, Tag
from markdown_it.token import Token

from app.RAG.Ingestion.CleanernParser.common_markdown import parse_markdown_tokens


_REMOVED_TAGS = {
    "script", "style", "svg", "iframe", "video", "audio", "object", "embed", "input",
}
_BLOCK_TAGS = {
    "article", "blockquote", "body", "div", "figure", "figcaption", "footer",
    "form", "header", "html", "label", "main", "nav", "ol", "p", "section", "ul",
}
_INLINE_HTML_TAGS = _REMOVED_TAGS | _BLOCK_TAGS | {
    "a", "b", "br", "button", "code", "details", "em", "h1", "h2", "h3",
    "h4", "h5", "h6", "hr", "i", "img", "li", "pre", "small", "span",
    "strong", "summary", "table", "tbody", "td", "th", "thead", "tr",
}
_TAG_NAME = re.compile(r"</?([A-Za-z][\w-]*)\b")
_INLINE_CODE = re.compile(r"(?<!`)(?P<ticks>`+)(?!`).*?(?P=ticks)(?!`)", re.DOTALL)
_POSSIBLE_TAG = re.compile(r"</?([A-Za-z][\w-]*)\b[^>]*>")


def _children_text(node: Tag, br_separator: str) -> str:
    return "".join(_node_text(child, br_separator) for child in node.children)


def _table_text(table: Tag) -> str:
    rows = []
    headers: list[str] = []
    for row in table.find_all("tr"):
        cells = row.find_all(["th", "td"], recursive=False)
        values = [re.sub(r"\s+", " ", _children_text(cell, "; ")).strip() for cell in cells]
        if not values:
            continue
        if not headers and all(cell.name == "th" for cell in cells):
            headers = values
            continue
        if headers:
            parts = [
                f"{headers[index] if index < len(headers) else f'Column {index + 1}'}: {value}"
                for index, value in enumerate(values) if value
            ]
            rows.append("- " + "; ".join(parts))
        else:
            rows.append("- " + " | ".join(values))
    return "\n".join(rows)
"""
Hàm này đang chuyển table HTML (chứ ko phải table Markdown) thành dạng text, 
cụ thể thì nó sẽ xử lý từng thẻ như <tr> : chỉ hàng,  <td> : chỉ cột,... để chuyển sang dạng text
mỗi hàng sẽ giữ nguyên, tên cột được loại bỏ, và trở thành attribute tại mỗi hàng.
vdu : 
- Tên: An; Phòng ban: Kỹ thuật; Địa điểm: Hà Nội
- Tên: Bình; Phòng ban: Kinh doanh; Địa điểm: Đà Nẵng
- Tên: Chi; Phòng ban: Nhân sự; Địa điểm: TP. Hồ Chí Minh
"""

# Hàm key : Quy định cách xử lý : Chuyển từ HTML sang text của từng loại thẻ 
def _node_text(node: Tag | NavigableString, br_separator: str) -> str:
    if isinstance(node, Comment):
        return ""
    if isinstance(node, NavigableString):
        return str(node)

    name = node.name.lower()
    if name in _REMOVED_TAGS:
        return ""
    if name == "br":
        return br_separator
    if name == "hr":
        return "\n\n"
    if name == "img":
        label = (node.get("alt") or node.get("title") or "").strip()
        return f" {label} " if label else ""
    if name == "table":
        return f"\n\n{_table_text(node)}\n\n"   # Thẻ table này chuyển sang text phức

    content = _children_text(node, br_separator)
    # Phía dưới đây là các Tags, mà giữa cặp thẻ sẽ có nội dung content mà ta cần giữ lại
    # hàm children text để lấy ra content ở giữa các cặp thẻ 
    if name == "a":
        label = content.strip() or (node.get("title") or "").strip()
        href = (node.get("href") or "").strip()
        if label and href and not href.lower().startswith(("javascript:", "data:", "vbscript:")):
            return f"[{label}]({href})"
        return label
    # ở đây chỉ có thẻ a là xử lý đặc biệt nhất, bởi thẻ này sẽ kèm theo 2 thuộc tính là tilte và href 
    # Ta sẽ lấy thuộc tính title làm label và href làm url, 2 cái này đều quan trọng, nên ta phải giữ lại 
    if name == "summary":
        return f"\n\n### {content.strip()}\n\n" if content.strip() else ""
    if name.startswith("h") and len(name) == 2 and name[1] in "123456":
        return f"\n\n{'#' * int(name[1])} {content.strip()}\n\n" if content.strip() else ""
    if name == "li":
        return f"\n- {content.strip()}" if content.strip() else ""
    if name in _BLOCK_TAGS or name == "details":
        return f"\n\n{content.strip()}\n\n" if content.strip() else ""
    return content

   #hàm này nhận vào 1 đoạn HTML --> Chuyển nó về dạng chuẩn mà ta muốn. Tuy nhiên cụ thể như thế nào do _node_text quyết định ( hàm này là nơi gọi hàm node text)
def extract_html_fragment(fragment: str, *, br_separator: str = "\n") -> str:
    soup = BeautifulSoup(fragment, "html.parser")
    extracted = "".join(_node_text(node, br_separator) for node in soup.contents)
    extracted = re.sub(r"[ \t]+\n", "\n", extracted)
    return re.sub(r"\n{3,}", "\n\n", extracted).strip()


# thật sự là logic hàm này lằng nhằng khó hiểu vl 
# tóm lại là nó sẽ che đi các thành phần nhìn giống thẻ HTML, nhưng thực chất là text, hoặc placeholder, còn các Incode thực tế thì vẫn được giữ nguyên để xử lý ở bước sau 
# ta cần che các cái này,tránh để beautySoup nhận diện là khối HTML và xử lý 
def _protect_markdown_literals(fragment: str) -> tuple[str, list[str]]:
    literals: list[str] = []
    # lưu đoạn text gốc mà bị che , thứ tự lưu cũng là thứ tự đánh số dấu giữ chỗ 
    def remember(match: re.Match[str]) -> str:
        literals.append(match.group())
        return f"\ue000{len(literals) - 1}\ue001"
    # hàm này sẽ được regex gọi mỗi khi tìm thấy 1 đoạn cần che 

    fragment = _INLINE_CODE.sub(remember, fragment)
    # Hàm sub (vt tắt cho substitute), là hàm của regex, regex sẽ tìm trong fragment có đoạn nào giống regex, nó sẽ lấy đoạn đó ra, đưa vào hàm remember, kết quả của hàm remember sẽ được thay thế vào Fragment
    def protect_unknown(match: re.Match[str]) -> str:
        if match.group(1).lower() in _INLINE_HTML_TAGS:  
            return match.group()
        return remember(match)

    return _POSSIBLE_TAG.sub(protect_unknown, fragment), literals


def _has_known_inline_html(token: Token) -> bool:
    for child in token.children or ():   
        if child.type != "html_inline":
            continue
        match = _TAG_NAME.match(child.content)
        if match and match.group(1).lower() in _INLINE_HTML_TAGS:   # Xác nhận xem inline đó có nằm trong danh sách inline mà cleaner đã biết cách xử lý hay không
            return True
    return False


def clean_html(page_content: str) -> str:
    """Replace only Markdown spans containing actual HTML; leave code blocks intact."""
    if "<" not in page_content:
        return page_content

    lines = page_content.splitlines(keepends=True)
    targets: list[tuple[int, int, bool]] = []  
    # Target là danh sách các đoạn code HTML. Trường bool để xác định đây có phải HTML block ko, hay là HTML Inline 
    # sở dĩ phải chia ra 2 loại là vì mỗi loại có cách xử lý khác nhau
    table_ranges: list[tuple[int, int]] = []
    for token in parse_markdown_tokens(page_content):   # hàm Parse này trả về danh sách token 
        if token.map is None:
            continue
        start, end = token.map
        if token.type == "html_block":
            targets.append((start, end, True))
        elif token.type == "inline" and _has_known_inline_html(token):
            targets.append((start, end, False))
        elif token.type == "table_open":
            table_ranges.append((start, end))


    for start, end in table_ranges:
        for line_number in range(start, end):
            if "<br" in lines[line_number].lower():
                targets.append((line_number, line_number + 1, False))

    if not targets:
        return page_content

    output: list[str] = []
    cursor = 0    # vị trí cuối cùng được xử lý 
    for start, end, is_block in sorted(set(targets)):
        if start < cursor:
            continue
        output.extend(lines[cursor:start])  #  Thêm các dòng từ vị trí cuối cùng được xử lý đến vị trí sắp tới cần xử lý
        fragment = "".join(lines[start:end])
        in_table = any(table_start <= start < table_end for table_start, table_end in table_ranges)
        # kiểm tra xem code này có nằm trong table hay ko (nếu có thì đây chính là thẻ br)
        if not is_block:
            fragment, literals = _protect_markdown_literals(fragment)
        else:
            literals = []
        cleaned = extract_html_fragment(fragment, br_separator="; " if in_table else "\n")
        for index, literal in enumerate(literals):
            cleaned = cleaned.replace(f"\ue000{index}\ue001", literal)
        if cleaned:
            output.append(f"\n\n{cleaned}\n\n" if is_block else cleaned + ("\n" if fragment.endswith("\n") else ""))
        cursor = end
    output.extend(lines[cursor:])
    return "".join(output)
