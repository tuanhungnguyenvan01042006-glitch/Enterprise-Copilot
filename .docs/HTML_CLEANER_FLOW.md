# HTML cleaner — tóm tắt

## 1. File giải quyết vấn đề gì?

Trong các Document Markdown có thể lẫn HTML thô: thẻ trình bày, script/style hoặc media không hữu ích khi lập chỉ mục; nội dung chữ trong HTML có thể khó đọc; liên kết, heading, danh sách và bảng có thể mất cấu trúc; `<br>` trong bảng có thể làm nội dung bị dính hoặc vỡ dòng. `html_cleaner.py` chuyển các vùng HTML được nhận diện thành văn bản dễ đọc, giữ lại nội dung hữu ích và bỏ một số phần không cần thiết.

Trong `clean_document`, HTML cleaner chạy sau khi tách front matter, xử lý shortcode và chuẩn hóa Markdown chung.

## 2. Luồng hoạt động chính

```text
Document Markdown
  → Markdown parser xác định các vùng HTML và dòng <br> trong bảng
  → che tạm code inline và thẻ lạ ở vùng inline để giữ nguyên văn bản
  → BeautifulSoup đọc HTML; cleaner bỏ nội dung không cần và chuyển phần còn lại thành text/Markdown
  → khôi phục phần đã che, ghép với các dòng không cần xử lý
  → Document đã làm sạch
```

HTML block được ghép lại như một khối; vùng inline được ghép vào dòng hiện có. `<br>` trong bảng dùng dấu `; ` thay vì xuống dòng để không làm vỡ cấu trúc bảng.

## 3. Vai trò từng hàm

| Hàm | Vai trò |
|---|---|
| `clean_html` | Hàm điều phối: tìm vùng cần xử lý, gọi các helper và ghép kết quả với phần Markdown còn lại. |
| `_has_known_inline_html` | Kiểm tra token Markdown inline có chứa thẻ HTML mà cleaner nhận diện hay không. |
| `_protect_markdown_literals` | Che tạm code inline và chuỗi giống thẻ HTML lạ để HTML parser không làm thay đổi chúng; trả lại để khôi phục sau. |
| `extract_html_fragment` | Phân tích một fragment HTML và chuẩn hóa kết quả thành văn bản. |
| `_node_text` | Chuyển từng node HTML thành text/Markdown theo loại thẻ; bỏ các thẻ được quy định là không cần. |
| `_children_text` | Lấy và nối nội dung đã chuyển đổi của các node con. |
| `_table_text` | Chuyển bảng HTML thành các dòng văn bản có nhãn cột hoặc phân cách bằng `|`. |
| `parse_markdown_tokens` *(trong `common_markdown.py`)* | Dùng Markdown parser để cung cấp token và khoảng dòng, giúp cleaner xác định vùng HTML thay vì đoán toàn bộ bằng regex. |

`_REMOVED_TAGS`, `_BLOCK_TAGS`, `_INLINE_HTML_TAGS` và các regex là cấu hình/quy tắc hỗ trợ các hàm trên, không phải hàm xử lý độc lập.

**Lưu ý:** `is_block` mô tả loại vùng nguồn mà Markdown parser tìm thấy và cách ghép kết quả, không phân loại từng thẻ bên trong. Ví dụ, `<a>` có thể nằm trong một target HTML block.
