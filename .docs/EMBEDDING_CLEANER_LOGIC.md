Logic hiện tại của [`Embedding/cleaner.py`](<C:\Users\tuanh\Downloads\Personal Project  new\backend\app\rag\Embedding\cleaner.py>) gồm các bước sau.

## 1. Validate input

```python
validate_embedding_item(item)
```

Được gọi đầu tiên để kiểm tra:

- `item` có đúng kiểu `EmbeddingItem`.
- `point_id` hợp lệ.
- `text` không rỗng.
- Metadata đầy đủ.
- `point_id` khớp `metadata.chunk_id`.
- Không chứa `storage_key`.

Nếu input không hợp lệ, quá trình dừng ngay bằng `EmbeddingInputValidationError`.

## 2. Bỏ qua code và Mermaid

```python
if item.metadata.get("block_type") in {"code", "mermaid"}:
    return item
```

Các chunk code và Mermaid được Chunking tách riêng nên Embedding Cleaner không xử lý tiếp. Table chunk đi qua cùng các bước clean như text chunk; chỉ `EmbeddingItem.text` thay đổi, còn bảng gốc được giữ để truy xuất.

Mục đích:

- Table vẫn giữ dấu `|`, hàng và cột khi clean text cho embedding.
- Không thay đổi code.
- Không thay đổi Mermaid.
- Giữ nguyên nội dung code và Mermaid để đảm bảo tính chính xác.

Điều này có nghĩa là placeholder hoặc Markdown syntax bên trong code và Mermaid cũng được giữ nguyên.

## 3. Xóa dynamic placeholder

Hàm:

```python
_remove_dynamic_placeholders(text)
```

Có hai trường hợp:

### Placeholder đứng riêng trên một dòng

```text
Some text

[Embedded or dynamic content unavailable in source]

More text
```

Kết quả:

```text
Some text

More text
```

`_PLACEHOLDER_LINE` xóa cả placeholder và newline của dòng đó.

### Placeholder nằm giữa câu

```text
The team has [Embedded or dynamic content unavailable in source] members.
```

Kết quả tạm thời:

```text
The team has   members.
```

Placeholder được thay bằng một khoảng trắng. Khoảng trắng dư sẽ được xử lý ở bước normalize whitespace.

## 4. Chuẩn hóa Markdown image

Hàm:

```python
_remove_markdown_images(text)
```

Nhận diện dạng:

```markdown
![alt text](image-url)
```

và thay toàn bộ image syntax bằng alt text:

```markdown
![Password policy diagram](/images/password-policy.png)
```

thành:

```text
Password policy diagram
```

Nếu alt text rỗng:

```markdown
![](/images/decorative.png)
```

thì image bị xóa hoàn toàn.

Lý do:

- URL ảnh không có nhiều giá trị cho Embedding.
- Alt text thường chứa mô tả nội dung ảnh.
- Ingestion đã xử lý HTML image, phần này chủ yếu xử lý Markdown image còn sót lại.

## 5. Chuẩn hóa Markdown link

Hàm:

```python
_remove_markdown_link_syntax(text)
```

Sử dụng `_MARKDOWN_LINK` để nhận diện:

```markdown
[label](url)
```

Điều kiện `(?<!\!)` đảm bảo không xử lý nhầm Markdown image.

### Link có label

```markdown
[Password Policy](/policy)
```

thành:

```text
Password Policy
```

### Link nằm trong inline code

```markdown
`[#thanks](https://gitlab.slack.com/archives/...)`
```

thành:

```text
`#thanks`
```

Link syntax được xử lý như text thông thường.

### Link không có label

```markdown
[](https://example.com/docs)
```

thành:

```text
example.com/docs
```

### Link có label là URL

```markdown
[https://gitlab.com](https://gitlab.com)
```

thành:

```text
gitlab.com
```

Hàm `_normalize_url()` chỉ bỏ scheme `http://` hoặc `https://`, không xóa domain/path.

## 6. Chuẩn hóa template expression

Hàm:

```python
_normalize_template_variables(text)
```

Nhận diện các biểu thức dạng:

```markdown
{{JOB_TITLE}}
{{START_DATE}}
{{Original Hire Date}}
```

và chuyển thành text dễ đọc:

```text
JOB TITLE
START DATE
Original Hire Date
```

Các dấu `_` hoặc `-` liên tiếp được thay bằng khoảng trắng.

Các shortcode dạng:

```markdown
{{< shortcode >}}
{{% shortcode %}}
```

không bị xử lý lại vì đã được Ingestion Cleaner xử lý trước đó.

## 7. Chuẩn hóa Markdown formatting

Hàm:

```python
_normalize_markdown_formatting(text)
```

Thực hiện theo thứ tự:

### Xóa heading marker

```markdown
## Password Policy
```

thành:

```text
Password Policy
```

Nội dung heading được giữ lại vì có giá trị ngữ nghĩa cho Retrieve.

### Xóa list marker

```markdown
- Use strong passwords.
1. Enable MFA.
```

thành:

```text
Use strong passwords.
Enable MFA.
```

### Xóa backtick inline code

```markdown
`check_password`
```

thành:

```text
check_password
```

Chỉ xóa dấu backtick, giữ nội dung bên trong.

### Xóa bold

```markdown
**Important policy**
```

thành:

```text
Important policy
```

### Xóa italic

```markdown
*strong password*
```

thành:

```text
strong password
```

Regex italic có điều kiện biên từ để hạn chế ảnh hưởng đến các identifier có dấu `_`.

Sau Markdown formatting, cleaner bỏ icon trong `EmbeddingItem.text` của text và table. `page_content` gốc vẫn giữ icon; code và Mermaid không bị tác động.

## 8. Chuẩn hóa whitespace

Hàm:

```python
_normalize_whitespace(text)
```

Thực hiện:

- `CRLF` và `CR` → `LF`.
- Xóa khoảng trắng cuối dòng.
- Gom nhiều space/tab liên tiếp thành một space.
- Gom từ ba newline trở lên thành tối đa hai newline.
- Xóa whitespace ở đầu/cuối toàn bộ text.

Ví dụ:

```text
Keep   credentials   private.



Next paragraph.
```

thành:

```text
Keep credentials private.

Next paragraph.
```

## 9. Kiểm tra text rỗng

Sau toàn bộ cleanup:

```python
if not cleaned:
    raise EmbeddingInputValidationError(...)
```

Nếu nội dung chỉ chứa placeholder, image không có alt hoặc Markdown syntax, hệ thống báo lỗi thay vì gửi text rỗng tới Embedding Model.

## 10. Trả về object mới

```python
return replace(item, text=cleaned)
```

Hàm:

- Không mutate `item` gốc.
- Giữ nguyên `point_id`.
- Giữ nguyên metadata.
- Chỉ thay đổi trường `text`.

Luồng tổng quát:

```text
Validate
→ Bỏ qua code/mermaid; table đi cùng luồng text
→ Xóa placeholder
→ Xử lý image
→ Xử lý link
→ Xử lý template
→ Xóa Markdown formatting
→ Bỏ icon
→ Chuẩn hóa whitespace
→ Kiểm tra rỗng
→ Trả về EmbeddingItem mới
```
