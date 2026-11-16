from langchain_core.documents import Document

from app.RAG.Ingestion.CleanernParser.common_markdown import (
    clean_common_markdown,
    strip_front_matter,
)
from app.RAG.Ingestion.CleanernParser.html_cleaner import clean_html
from app.RAG.Ingestion.CleanernParser.shortcode_cleaner import clean_shortcodes


def clean_document(document: Document) -> Document:
    content_without_front_matter = strip_front_matter(document.page_content)   # xóa phần front matter trước
    content_without_html = clean_html(content_without_front_matter)            # trích xuất nội dung HTML : hiểu dơn giản là xóa các cặp thẻ, lấy nội dung bên trong 
    content_without_shortcodes = clean_shortcodes(content_without_html)        # xóa shortcode/ include ko thể resolve (vẫn giữ lại nội dung giữa cặp thẻ shortcode) 
    cleaned_content = clean_common_markdown(content_without_shortcodes)        # xóa các thẻ chắc chắn là noise như : HTML noise, thẻ style.
    return document.model_copy(update={"page_content": cleaned_content})       

# Lý do cần phải theo thứ tự thế này : nếu để shortcode lên trước html, thì sẽ xóa shortcode trong 1 đoạn html, tạo ra 1 khoảng trắng giữa đoạn HTML, sẽ khiến Markdown-it-py ko nhận diện được khối HTML phía dưới, và ko xử lý, ko loại bỏ các tag
