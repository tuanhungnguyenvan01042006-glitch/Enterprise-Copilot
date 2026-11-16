# Roadmap Cleaner / Parser cho GitLab Handbook RAG

Ngày rà soát: 2026-10-13  
Thư mục nguồn: `.external/gitlab-handbook/content/handbook/`  
Mục tiêu: xác định tài liệu được phép vào vector index, sau đó tạo nội dung ổn định để đưa sang Chunking và Embedding.

## 1. Phạm vi và nguyên tắc

Rà soát workspace hiện tại có **170 file Markdown**, tổng dung lượng khoảng **3,001,471 bytes**. Lần thống kê trước ghi nhận 172 file; số liệu roadmap này dùng inventory hiện có trong workspace. Các bộ đếm markup là kết quả dò mẫu, có thể chồng lấp.

| Dấu hiệu | Số file / lần xuất hiện |
|---|---:|
| Markdown không phát hiện HTML thô hoặc shortcode | 69 file |
| Có HTML thô sau khi loại fenced code khỏi phép dò | 50 file |
| Có shortcode | 63 file; 239 thẻ mở, 352 delimiter mở/đóng |
| Vừa có HTML vừa có shortcode | 12 file |
| Có include shortcode | 20 file, 24 lần gọi |
| Có shortcode video YouTube/Vimeo | 33 file |
| Có HTML `<details>` hoặc shortcode `details` | 26 file |
| Có Markdown table | 47 file |
| Có hình ảnh Markdown hoặc HTML | 46 file |
| Có fenced code | 9 file; trong đó 6 file có Mermaid |
| Có `<br>` | 9 file |
| Có dòng “Return to the main…” | 32 file |
| Có “Contribute your lessons” | 20 file |
| Có HTML comment | 13 file |
| Có `{style=...}` | 29 file |

Mỗi file có `title` và `category`; 137 file có `description`. Một file dùng key `Title` viết hoa: `company/company.md`. Có 3 file mang `controlled_document`/nhãn Visibility Audit.

**Ràng buộc nguồn:** shortcode, include và nội dung động không được resolve hoặc gọi Hugo để render. Cleaner chỉ có thể giữ nội dung tĩnh có mặt trong file, bỏ cú pháp wrapper đã biết, và đánh dấu phần nội dung có thể bị thiếu. Không suy diễn nội dung bị thiếu từ tên shortcode hay URL.

**Nguyên tắc triển khai:**

1. Giữ file Markdown gốc làm nguồn đối chiếu; Cleaner chỉ tạo `page_content` dùng cho retrieval.
2. Dùng một pipeline chung trên LangChain `Document`. Parser chuyên biệt chỉ xử lý phần markup tương ứng.
3. Không biến mọi Markdown thành HTML rồi viết lại. Giữ cấu trúc bảng/code/heading khi không cần chuyển đổi.
4. Không dùng LLM để quyết định xóa nội dung. Quy tắc xóa phải xác định, kiểm tra được và có danh sách cho phép.
5. Dùng trạng thái `indexable`, `hold_for_review`, `partial` hoặc `skip` để không đưa nội dung không đầy đủ vào vector index như thể hoàn chỉnh.

## 2. Pipeline đích

```text
Load UTF-8 Markdown
    ↓
Parse front matter → metadata chuẩn hóa
    ↓
Index gate → skip / hold / tiếp tục
    ↓
Bảo vệ code fence → bỏ boilerplate chính xác → xử lý shortcode không resolve
    ↓
Parse HTML khi cần → giữ text/structure có nghĩa, bỏ presentation markup
    ↓
Normalize → quality gate → LangChain Document sạch
    ↓
Chunking → Embedding
```

Không cần thêm một framework orchestration. Có thể giữ logic ở một `cleaner.py` với một entry point và một số hàm nhỏ; `pipeline.py` chỉ gọi Cleaner sau Loader.

## 3. Roadmap theo bước

### Bước 1 — Xác định file được index, giữ lại chờ review, hoặc bỏ khỏi index

**Vấn đề:** nguồn có file rỗng, trang trỏ đến handbook nội bộ không nằm trong corpus, trang placeholder, shortcode sinh nội dung cốt lõi và include không thể resolve. Nếu đưa nguyên trạng vào vector store, retriever có thể tìm thấy một tài liệu thiếu phần trả lời.

**Quyết định khởi đầu:**

| Trạng thái | Quy tắc | File | 
|---|---|---|
| `skip` | Body rỗng sau front matter | `company/company.md` |
| `skip` | Chỉ là pointer đến nội dung nội bộ không có trong corpus; không embed như policy đầy đủ | `finance/payroll.md`, `finance/authorization-matrix.md`, `finance/sales-comp-plan.md` |
| `skip` | Nội dung chính cần tìm nằm trong shortcode `misused-terms`, không có trong file tĩnh | `communication/top-misused-terms.md` |
| `skip` đến khi nguồn được cập nhật | Placeholder hoặc trang đang xây dựng, chưa có hướng dẫn dùng được | `company/culture/all-remote/guide/legal.md`, `people-group/learning-and-development/learning-initiatives/learning-initiatives.md` |
| `hold_for_review` | Include không thể resolve; mặc định chưa đưa vào index cho đến khi kiểm tra thấy phần tĩnh còn lại đủ độc lập | 20 file ở [Phụ lục C](#phụ-lục-c--20-file-có-include-không-thể-resolve) |
| `hold_for_review` theo ACL | Không xóa như noise. Chỉ index sau khi xác định scope/visibility và bộ lọc quyền truy cập | `people-policies/people-policies.md`, `people-group/acceptable-use-policy.md`, `people-group/offboarding/offboarding_standards.md` |
| `partial` | Giữ text tĩnh, bỏ vùng sinh động không có trong nguồn; đánh dấu metadata thiếu nội dung | `company/kpis.md`, `company/team.md`, `company/culture/all-remote/gitlab-for-remote.md`, `company/culture/all-remote/terminology.md`, `people-group/contracts-probation-periods.md`, `people-group/learning-and-development/mentor/mentor.md` |


Với file `partial`, Cleaner không tự điền phần thiếu. Nếu câu trả lời quan trọng nằm trong đoạn động (ví dụ KPI list hoặc danh sách misused terms), không index đoạn đó. Nếu không thể tách phần động khỏi câu trả lời an toàn bằng quy tắc đơn giản, chuyển cả file sang `hold_for_review`.

**Công cụ:** logic gating nhỏ bằng Python và metadata của `Document`; không cần thêm thư viện.

**Đầu ra:** báo cáo ingest ghi số file theo trạng thái và lý do; không âm thầm bỏ file.

### Bước 2 — Parse front matter và chuẩn hóa metadata

**Vấn đề:** front matter cần tách khỏi body; key `Title` không cùng chữ hoa/thường; metadata là dữ liệu phục vụ filter/citation, không nên đi vào embedding như văn xuôi.

**Cách xử lý:** dùng `python-frontmatter` để parse YAML front matter thành metadata + body. Chuẩn hóa tên key về lowercase. Giữ tối thiểu `title`, `category`, `description`, `source_path`, `controlled_document`, `public`, `status`, `date`, `canonical_path` nếu có. Không bỏ các trường visibility/kiểm soát.

**File cần kiểm tra:** áp dụng cho cả 170 file; ngoại lệ chữ hoa là `company/company.md`. Trường mô tả vắng ở 33 file không mặc nhiên là lỗi vì `description` có thể tùy chọn.

**Thư viện:** [`python-frontmatter`](https://python-frontmatter.readthedocs.io/en/latest/) đã cung cấp thao tác parse metadata và content riêng. Nếu format thực tế phát sinh ngoài YAML Jekyll-style, chỉ mở rộng parser sau khi có file đại diện.

**Đầu ra:** `Document.metadata` có `source_path` là đường dẫn tương đối đầy đủ từ handbook root, tránh chỉ dùng basename trùng nhau.

### Bước 3 — Chuẩn hóa Markdown và bỏ noise dùng chung

**Vấn đề:** navigation tail, lời mời đóng góp, HTML comment và style attribute lặp lại; một số quy tắc xóa toàn cục có thể làm hỏng Mermaid/code hoặc xóa nội dung giữa bài.

**Cách xử lý:**

1. Parse block Markdown bằng `markdown-it-py` preset phù hợp GFM để nhận diện fenced code/table/HTML block; không cần render rồi serialize lại toàn bộ tài liệu.
2. Bảo vệ code fence trước mọi thao tác loại comment, tag hoặc shortcode. Điều này đặc biệt cần cho Mermaid có `-->`.
3. Bỏ navigation/footer chỉ khi khớp phrase và vị trí cuối trang; bỏ “Contribute your lessons” theo block chính xác.
4. Bỏ HTML comments ngoài code fence. Comment có hướng dẫn maintainer không cần đưa vào retrieval, nhưng không xóa comment lẫn trong code.
5. Gỡ `{style=...}` và thuộc tính layout nhưng giữ nguyên text đứng cạnh.
6. Chuẩn hóa newline và khoảng trắng liên tiếp; không xóa horizontal rule hàng loạt.

**File gặp boilerplate navigation:** xem danh sách 32 file ở [Phụ lục D](#phụ-lục-d--navigation-footer-và-boilerplate). 20 file có lời mời đóng góp cũng được liệt kê tại đó.

**File có HTML comment:** `communication/communication.md`, `communication/top-misused-terms.md`, `company/culture/culture.md`, `company/culture/all-remote/drawbacks.md`, `company/culture/all-remote/meetings.md`, `company/culture/all-remote/mental-health.md`, `company/culture/all-remote/parenting.md`, `company/culture/all-remote/stages.md`, `people-group/talent-assessment.md`, `people-group/offboarding/offboarding.md`, `people-policies/people-policies.md`, `people-policies/france-sas/right-to-disconnect-charter.md`, `values/values.md`.

**File có `{style=...}`:** 29 file trong cụm `company/culture/all-remote/`; danh sách cụ thể ở Phụ lục D.

**Thư viện:** `markdown-it-py` cung cấp token stream và cấu trúc block; preset GFM-like có hỗ trợ bảng. Dùng parser để bảo vệ/nhận diện cấu trúc, không dùng nó như một bộ viết lại nội dung. [Tài liệu](https://markdown-it-py.readthedocs.io/en/latest/using.html)

### Bước 4 — Xử lý shortcode/include mà không resolve

**Vấn đề:** 63 file có shortcode; 20 file có include. Các macro như YouTube, KPI, team-size và misused-terms không có phần sinh ra trong file nguồn. Không thể giả định nội dung output.

**Chính sách:**

| Dạng shortcode | Xử lý |
|---|---|
| `details`, `panel`, `alert`, `card`, `cardpane` có phần thân tĩnh | Bỏ marker mở/đóng, giữ nguyên phần Markdown ở giữa. Nếu có `summary`/`title` tĩnh dễ lấy, đưa thành heading/nhãn. Không xóa phần thân. |
| `youtube`, `vimeo` | Bỏ player/embed token. Giữ caption/title/link nếu có trong text tĩnh. Không coi video ID là nội dung. |
| `include` | Không resolve. Gắn `has_unresolved_include=true`; file ở `hold_for_review` cho đến khi có đánh giá thủ công về nội dung còn lại. |
| Macro sinh dữ liệu (`kpi`, `team-size`, `misused-terms`, v.v.) | Bỏ token khỏi embedding, ghi tên macro vào metadata/log. Nếu macro là phần cốt lõi thì bỏ file/section khỏi index. |
| Macro chưa biết | Không embed raw syntax; chuyển file sang `hold_for_review`. |
| Template variable như `{{JOB_TITLE}}` | Giữ nguyên; không phải Hugo shortcode. |

Không cần tự viết một bộ phân tích Hugo hoàn chỉnh. Chỉ xử lý danh sách macro đã phát hiện, dùng `re`/Markdown token boundaries; nếu gặp dạng mới thì fail closed và báo file. Shortcode Hugo có thể chứa nội dung tĩnh bên trong hoặc chỉ sinh output từ template; vì vậy phải phân biệt wrapper với dynamic data. [Tài liệu Hugo về shortcode](https://gohugo.io/content-management/shortcodes/)

**Macro dữ liệu cần review:** `company/kpis.md` (KPI Index động), `company/team.md` (team size), `communication/top-misused-terms.md` (danh sách term động), `company/culture/all-remote/gitlab-for-remote.md` và `company/culture/all-remote/terminology.md` (macro all-remote/team-size), `people-group/contracts-probation-periods.md` (macro people-group và template variables), `people-group/learning-and-development/mentor/mentor.md` (group-by-expertise).

**Danh sách đầy đủ file có shortcode:** [Phụ lục B](#phụ-lục-b--63-file-có-shortcode). Danh sách 20 file include ở Phụ lục C là tập con của danh sách này.

### Bước 5 — Parse HTML và loại phần trình bày

**Vấn đề:** 50 file có raw HTML, trong đó có layout/card/button, bảng, iframe, SVG, `<details>` và HTML lỗi. Xóa tag bằng regex có thể làm dính hoặc mất text.

**Cách xử lý:**

1. Chỉ chạy HTML extraction cho tài liệu có HTML; giữ nguyên Markdown thuần.
2. Dùng Beautiful Soup để parse fragment; bỏ `script`, `style`, `svg`, iframe/player và phần tử chỉ có icon/trang trí.
3. Giữ text node, heading, link text và `href` có ích, alt/caption hình, hàng/cột bảng và nội dung `details`.
4. Giữ boundary giữa paragraph/list/table row bằng newline hoặc separator; không dùng một `get_text()` mặc định làm mất quan hệ bảng.
5. Gỡ `class`, `style`, `id`, `data-*` nếu chỉ là presentation; không gỡ nội dung con cùng lúc.
6. Chuẩn hóa `<br>` thành newline.
7. Riêng `bv-benefits-netherlands.md`, xử lý `<details markdown="1"\>` lỗi; kiểm tra output text trước khi chấp nhận.

**File HTML-heavy ưu tiên kiểm tra:**

- `company/culture/all-remote/all-remote.md` — card/layout; 164 HTML tag theo bộ dò hiện tại.
- `company/culture/all-remote/remote-work-report.md` — report + card/CTA; 124 tag.
- `total-rewards/benefits/general-and-entity-benefits/ltd-benefits-uk.md` — 106 tag.
- `company/culture/all-remote/gitlab-for-remote.md` — form/modal/iframe/layout; 90 tag.
- `total-rewards/benefits/general-and-entity-benefits/gitlab-ireland-ltd.md` — 88 tag.
- `total-rewards/benefits/general-and-entity-benefits/global-expansion.md` — 84 tag.
- `total-rewards/benefits/general-and-entity-benefits/bv-benefits-netherlands.md` — 82 tag, malformed `<details>`.
- `people-group/learning-and-development/career-development/career-development.md` — 72 tag, bảng HTML/video.
- `total-rewards/benefits/general-and-entity-benefits/france-sas.md` — 68 tag.
- `total-rewards/benefits/general-and-entity-benefits/inc-benefits-us/inc-benefits-us.md` — 62 tag.
- `total-rewards/benefits/general-and-entity-benefits/pty-benefits-australia.md` — 52 tag.
- `company/culture/all-remote/work-from-home-field-guide.md` — 45 tag.
- `total-rewards/benefits/general-and-entity-benefits/pty-benefits-new-zealand.md` — 42 tag.
- `total-rewards/benefits/general-and-entity-benefits/general-and-entity-benefits.md` — 40 tag.
- `total-rewards/benefits/general-and-entity-benefits/remote-com.md` — 38 tag.

**Thư viện:** [`beautifulsoup4`](https://www.crummy.com/software/BeautifulSoup/bs4/doc/) với parser Python `html.parser` trước. Nếu malformed markup làm cây sai, thử `lxml` cho đúng các file đó; không thêm parser khác nếu không có lỗi thực tế.

**Toàn bộ danh sách HTML-bearing:** [Phụ lục A](#phụ-lục-a--50-file-có-html-thô).

### Bước 6 — Giữ cấu trúc semantic cần cho retrieval

**Bảng:** có 47 file. Giữ nguyên bảng Markdown nếu được; nếu downstream splitter không giữ bảng tốt, chuyển từng row thành dòng có header, ví dụ `Eligibility: ...; Country: ...`. Không tách từng cell thành chunk độc lập.

**Details:** 26 file có HTML hoặc shortcode details. Chuyển `summary` thành heading/label, giữ toàn bộ nội dung mở rộng. Không bỏ chỉ vì mặc định nội dung đang collapsed trên website. Danh sách ở Phụ lục E.

**Code/Mermaid:** giữ fenced block nguyên vẹn; Mermaid có thể chứa `-->` và syntax giống comment. Không nhúng CSS/JS/script. Danh sách file ở Phụ lục F.

**Images:** có 46 file tham chiếu ảnh. Bỏ ảnh trang trí khỏi embedding; giữ alt text/caption nếu mô tả quy trình hoặc nội dung. Không cần OCR ảnh cho corpus này ở giai đoạn đầu.

**Links:** giữ anchor text; giữ URL nội bộ/ngoại bộ nếu giúp nhận diện nguồn hoặc điều hướng. Không tải nội dung link để bù include, vì phạm vi nguồn hiện tại không cho resolve.

### Bước 7 — Chuẩn hóa text và trạng thái đầy đủ

**Encoding:** đã kiểm tra toàn bộ 170 file bằng UTF-8 strict: không có file lỗi decode, không có U+FFFD. Một số output PowerShell trước đó hiển thị ký tự cong/emoji như mojibake; kiểm tra code point trực tiếp xác nhận file chứa Unicode đúng. **Không chạy bước sửa mojibake hàng loạt.** Loader hiện dùng UTF-8-sig là phù hợp với BOM/UTF-8.

**Các quy tắc text:**

- Chuẩn hóa CRLF/LF và khoảng trắng liên tiếp ngoài code.
- Giữ số liệu, ngày tháng, đơn vị, tên quốc gia, tên role, ngoại lệ và điều kiện trong policy.
- Giữ `{{JOB_TITLE}}`, `{{START_DATE}}`, `{{Original Hire Date}}` như template variables; không thay bằng giá trị tưởng tượng.
- Nếu bỏ shortcode, lưu `unresolved_shortcode_names` và `partial_content=true` trong metadata để truy vết nguồn.
- Gắn `source_path` đầy đủ để citation có thể quay về đúng file.

**Controlled documents:** các file `people-policies/people-policies.md`, `people-group/acceptable-use-policy.md`, `people-group/offboarding/offboarding_standards.md` cần kiểm tra access scope trước khi index. Cleaner không quyết định quyền; vector store/retrieval phải lọc theo metadata quyền tương ứng.

### Bước 8 — Quality gate trước Chunking/Embedding

Không tạo embedding nếu bất kỳ điều kiện nào sau đây đúng:

1. File thuộc `skip` hoặc `hold_for_review`.
2. Body rỗng sau khi bỏ front matter/markup.
3. Còn shortcode/include chưa xử lý trong text gửi đi embed.
4. Có HTML extraction làm mất heading, row/cell, summary, anchor text hoặc alt/caption cần thiết.
5. Có code fence/Mermaid bị chỉnh sửa ngoài ý muốn.
6. Metadata thiếu `source_path`, `title`, `category` hoặc visibility cần thiết.
7. Nội dung bị đánh dấu `partial` nhưng phần thiếu là câu trả lời chính của tài liệu.

**Kiểm tra thủ công trên representative set:**

- Markdown thường: `communication/confidentiality-levels.md`.
- Markdown table/policy: `people-group/acceptable-use-policy.md`.
- HTML-heavy: `company/culture/all-remote/all-remote.md`, `company/culture/all-remote/remote-work-report.md`, `total-rewards/benefits/general-and-entity-benefits/bv-benefits-netherlands.md`.
- details: `people-group/time-off-and-absence/time-off-types.md`.
- video shortcode: `company/history.md`.
- unresolved include: `company/culture/all-remote/remote-work-report.md`.
- dynamic data: `company/kpis.md`, `communication/top-misused-terms.md`.
- empty/pointer/placeholder: các file ở Bước 1.

Sau khi Cleaner đạt quality gate, mới dùng LangChain Markdown header splitter hoặc splitter đang có để chunk theo heading; header path và `source_path` phải nằm trong metadata của từng chunk. Không chuyển sang Embedding trước khi kiểm tra chunk preview và retrieval trên một bộ câu hỏi nhỏ bao gồm policy, benefits, quy trình, bảng và chủ đề remote work.

## 4. Tooling tối giản đề xuất

| Công cụ | Vai trò | Quyết định |
|---|---|---|
| LangChain `Document` | Interface chung giữa Loader, Cleaner, chunker và embedding | Giữ nguyên; hiện đã có trong dự án |
| `python-frontmatter` | Parse YAML front matter | Thêm dependency trực tiếp, pin version |
| `markdown-it-py` | Nhận diện block/token Markdown, bảng và code boundary | Dùng nếu parser hiện có chưa đủ; không serialize lại toàn bộ body |
| `beautifulsoup4` + `html.parser` | Parse HTML fragment và bỏ phần tử presentation | Thêm dependency; `lxml` chỉ khi fixture malformed cần |
| Python stdlib `re`, `html`, `pathlib` | Footer chính xác, token shortcode đã biết, normalize | Dùng cho các quy tắc hẹp; không viết parser Hugo tổng quát |
| Hugo CLI | Render Hugo source | **Không dùng** theo ràng buộc nguồn không thể resolve |
| Unstructured / Docling / LLM cleaner | Parse nhiều format hoặc suy luận nội dung | Không dùng; không phù hợp với nhu cầu Markdown hiện tại và làm tăng độ phức tạp |

Nếu `markdown-it-py` được dùng, cấu hình GFM-like cho table nhưng tránh auto-linkify/thay đổi typography không cần thiết. Tài liệu parser mô tả token stream, block rules và table support: [markdown-it-py](https://markdown-it-py.readthedocs.io/en/latest/using.html). LangChain splitter chỉ chạy sau Cleaner; nó phục vụ chunking theo heading, không phải HTML/shortcode cleaner: [MarkdownHeaderTextSplitter](https://reference.langchain.com/python/langchain-text-splitters/markdown/MarkdownHeaderTextSplitter).

## 5. Phụ lục: file paths theo vấn đề

Tất cả path bên dưới tương đối với `.external/gitlab-handbook/content/handbook/`.

### Phụ lục A — 50 file có HTML thô

`communication/chat.md`; `communication/communication.md`; `company/quote-to-cash.md`; `company/culture/culture.md`; `company/culture/all-remote/all-remote.md`; `company/culture/all-remote/drawbacks.md`; `company/culture/all-remote/gitlab-for-remote.md`; `company/culture/all-remote/meetings.md`; `company/culture/all-remote/remote-work-report.md`; `company/culture/all-remote/work-from-home-field-guide.md`; `finance/finance.md`; `finance/payroll.md`; `people-group/engagement.md`; `people-group/organizational-change-management.md`; `people-group/people-group.md`; `people-group/promotions-transfers.md`; `people-group/talent-assessment.md`; `people-group/talent-development-program.md`; `people-group/general-onboarding/general-onboarding.md`; `people-group/general-onboarding/mr-buddies.md`; `people-group/general-onboarding/onboarding-buddies.md`; `people-group/general-onboarding/tanewki-tips.md`; `people-group/learning-and-development/learning-and-development.md`; `people-group/learning-and-development/career-development/career-development.md`; `people-group/learning-and-development/career-development/igp-guide.md`; `people-group/learning-and-development/mentor/mentor.md`; `people-group/time-off-and-absence/leave-types.md`; `people-policies/leave-of-absence/us.md`; `total-rewards/incentives.md`; `total-rewards/benefits/modern-health.md`; `total-rewards/benefits/general-and-entity-benefits/bv-benefits-belgium.md`; `total-rewards/benefits/general-and-entity-benefits/bv-benefits-finland.md`; `total-rewards/benefits/general-and-entity-benefits/bv-benefits-netherlands.md`; `total-rewards/benefits/general-and-entity-benefits/canada-corp-benefits.md`; `total-rewards/benefits/general-and-entity-benefits/financial-wellness.md`; `total-rewards/benefits/general-and-entity-benefits/france-sas.md`; `total-rewards/benefits/general-and-entity-benefits/general-and-entity-benefits.md`; `total-rewards/benefits/general-and-entity-benefits/gitlab-gk.md`; `total-rewards/benefits/general-and-entity-benefits/gitlab-ireland-ltd.md`; `total-rewards/benefits/general-and-entity-benefits/global-expansion.md`; `total-rewards/benefits/general-and-entity-benefits/korea-ltd-benefits.md`; `total-rewards/benefits/general-and-entity-benefits/ltd-benefits-uk.md`; `total-rewards/benefits/general-and-entity-benefits/papaya-global-benefits.md`; `total-rewards/benefits/general-and-entity-benefits/pty-benefits-australia.md`; `total-rewards/benefits/general-and-entity-benefits/pty-benefits-new-zealand.md`; `total-rewards/benefits/general-and-entity-benefits/remote-com.md`; `total-rewards/benefits/general-and-entity-benefits/singapore-pte-ltd.md`; `total-rewards/benefits/general-and-entity-benefits/inc-benefits-us/inc-benefits-us.md`; `total-rewards/compensation/compensation-review-cycle/compensation-review-cycle.md`; `values/values.md`.

### Phụ lục B — 63 file có shortcode

`communication/communication.md`; `communication/top-misused-terms.md`; `company/cadence.md`; `company/history.md`; `company/mission.md`; `company/purpose.md`; `company/stewardship.md`; `company/vision.md`; `company/kpis.md`; `company/team.md`; `company/culture/cross-culture-collaboration-guide.md`; `company/culture/songbook.md`; `company/culture/all-remote/all-remote.md`; `company/culture/all-remote/being-a-great-remote-manager.md`; `company/culture/all-remote/building-culture.md`; `company/culture/all-remote/drawbacks.md`; `company/culture/all-remote/getting-started.md`; `company/culture/all-remote/gitlab-for-remote.md`; `company/culture/all-remote/handbook-first.md`; `company/culture/all-remote/informal-communication.md`; `company/culture/all-remote/internship.md`; `company/culture/all-remote/meetings.md`; `company/culture/all-remote/mental-health.md`; `company/culture/all-remote/non-linear-workday.md`; `company/culture/all-remote/parenting.md`; `company/culture/all-remote/phases-of-remote-adaptation.md`; `company/culture/all-remote/remote-benefits.md`; `company/culture/all-remote/remote-vision.md`; `company/culture/all-remote/remote-work-emergency-plan.md`; `company/culture/all-remote/remote-work-report.md`; `company/culture/all-remote/remote-work-starter-guide.md`; `company/culture/all-remote/scaling.md`; `company/culture/all-remote/stages.md`; `company/culture/all-remote/terminology.md`; `company/culture/all-remote/the-gitlab-test-remote-work.md`; `company/culture/all-remote/what-not-to-do.md`; `company/culture/all-remote/work-from-home-field-guide.md`; `company/culture/all-remote/working-while-traveling.md`; `company/culture/all-remote/workspace.md`; `company/culture/all-remote/collaboration-and-whiteboarding/collaboration-and-whiteboarding.md`; `company/culture/all-remote/guide/guide.md`; `finance/expenses.md`; `people-group/acceptable-use-policy.md`; `people-group/anti-harassment.md`; `people-group/competencies.md`; `people-group/contracts-probation-periods.md`; `people-group/guidance-on-feedback.md`; `people-group/visas.md`; `people-group/learning-and-development/career-development/career-development.md`; `people-group/learning-and-development/career-development/igp-guide.md`; `people-group/learning-and-development/manager-development/manager-development.md`; `people-group/learning-and-development/mentor/mentor.md`; `people-group/offboarding/offboarding_standards.md`; `people-group/time-off-and-absence/time-away-philosophy.md`; `people-group/time-off-and-absence/time-off-types.md`; `people-policies/people-policies.md`; `people-policies/france-sas/remote-work-charter.md`; `people-policies/france-sas/right-to-disconnect-charter.md`; `people-policies/india-ltd/india-ltd.md`; `people-policies/ireland-ltd/right-to-disconnect-policy.md`; `total-rewards/incentives.md`; `total-rewards/total-rewards.md`; `values/values.md`.

Macro subtype examples: 33 video files are `communication/communication.md`, `company/history.md`, `company/culture/cross-culture-collaboration-guide.md`, `company/culture/songbook.md`, 21 all-remote/collaboration/guide files, and `people-group/competencies.md`, `people-group/guidance-on-feedback.md`, `people-group/visas.md`, `people-group/learning-and-development/career-development/career-development.md`, `people-group/learning-and-development/career-development/igp-guide.md`, `people-group/learning-and-development/manager-development/manager-development.md`, `people-group/learning-and-development/mentor/mentor.md`, `values/values.md`.

### Phụ lục C — 20 file có include không thể resolve

`company/cadence.md`; `company/history.md`; `company/mission.md`; `company/purpose.md`; `company/stewardship.md`; `company/vision.md`; `company/culture/all-remote/all-remote.md`; `company/culture/all-remote/building-culture.md`; `company/culture/all-remote/getting-started.md`; `company/culture/all-remote/parenting.md`; `company/culture/all-remote/remote-work-emergency-plan.md`; `company/culture/all-remote/remote-work-report.md`; `company/culture/all-remote/remote-work-starter-guide.md`; `company/culture/all-remote/scaling.md`; `company/culture/all-remote/stages.md`; `company/culture/all-remote/terminology.md`; `company/culture/all-remote/the-gitlab-test-remote-work.md`; `company/culture/all-remote/what-not-to-do.md`; `company/culture/all-remote/work-from-home-field-guide.md`; `company/culture/all-remote/working-while-traveling.md`.

### Phụ lục D — Navigation footer và boilerplate

32 file có “Return to the main…”: `communication/zoom/zoom.md`; `company/culture/all-remote/being-a-great-remote-manager.md`; `company/culture/all-remote/building-culture.md`; `company/culture/all-remote/drawbacks.md`; `company/culture/all-remote/getting-started.md`; `company/culture/all-remote/handbook-first.md`; `company/culture/all-remote/informal-communication.md`; `company/culture/all-remote/internship.md`; `company/culture/all-remote/live-doc-meetings.md`; `company/culture/all-remote/meetings.md`; `company/culture/all-remote/mental-health.md`; `company/culture/all-remote/non-linear-workday.md`; `company/culture/all-remote/onboarding.md`; `company/culture/all-remote/parenting.md`; `company/culture/all-remote/phases-of-remote-adaptation.md`; `company/culture/all-remote/remote-benefits.md`; `company/culture/all-remote/remote-vision.md`; `company/culture/all-remote/remote-work-emergency-plan.md`; `company/culture/all-remote/remote-work-starter-guide.md`; `company/culture/all-remote/scaling.md`; `company/culture/all-remote/stages.md`; `company/culture/all-remote/terminology.md`; `company/culture/all-remote/the-gitlab-test-remote-work.md`; `company/culture/all-remote/what-not-to-do.md`; `company/culture/all-remote/working-while-traveling.md`; `company/culture/all-remote/workspace.md`; `company/culture/all-remote/collaboration-and-whiteboarding/collaboration-and-whiteboarding.md`; `company/culture/all-remote/guide/design.md`; `company/culture/all-remote/guide/finance.md`; `company/culture/all-remote/guide/legal.md`; `company/culture/all-remote/guide/people-operations.md`; `total-rewards/benefits/parental-leave-toolkit.md`.

20 file có “Contribute your lessons”: `company/culture/all-remote/being-a-great-remote-manager.md`; `company/culture/all-remote/building-culture.md`; `company/culture/all-remote/getting-started.md`; `company/culture/all-remote/handbook-first.md`; `company/culture/all-remote/internship.md`; `company/culture/all-remote/mental-health.md`; `company/culture/all-remote/non-linear-workday.md`; `company/culture/all-remote/parenting.md`; `company/culture/all-remote/phases-of-remote-adaptation.md`; `company/culture/all-remote/remote-benefits.md`; `company/culture/all-remote/remote-work-emergency-plan.md`; `company/culture/all-remote/remote-work-starter-guide.md`; `company/culture/all-remote/scaling.md`; `company/culture/all-remote/stages.md`; `company/culture/all-remote/terminology.md`; `company/culture/all-remote/the-gitlab-test-remote-work.md`; `company/culture/all-remote/what-not-to-do.md`; `company/culture/all-remote/working-while-traveling.md`; `company/culture/all-remote/workspace.md`; `company/culture/all-remote/collaboration-and-whiteboarding/collaboration-and-whiteboarding.md`.

29 file có `{style=...}`: `company/culture/all-remote/being-a-great-remote-manager.md`; `company/culture/all-remote/building-culture.md`; `company/culture/all-remote/getting-started.md`; `company/culture/all-remote/handbook-first.md`; `company/culture/all-remote/informal-communication.md`; `company/culture/all-remote/internship.md`; `company/culture/all-remote/live-doc-meetings.md`; `company/culture/all-remote/meetings.md`; `company/culture/all-remote/mental-health.md`; `company/culture/all-remote/non-linear-workday.md`; `company/culture/all-remote/onboarding.md`; `company/culture/all-remote/parenting.md`; `company/culture/all-remote/phases-of-remote-adaptation.md`; `company/culture/all-remote/remote-benefits.md`; `company/culture/all-remote/remote-vision.md`; `company/culture/all-remote/remote-work-emergency-plan.md`; `company/culture/all-remote/remote-work-starter-guide.md`; `company/culture/all-remote/scaling.md`; `company/culture/all-remote/stages.md`; `company/culture/all-remote/terminology.md`; `company/culture/all-remote/the-gitlab-test-remote-work.md`; `company/culture/all-remote/what-not-to-do.md`; `company/culture/all-remote/working-while-traveling.md`; `company/culture/all-remote/workspace.md`; `company/culture/all-remote/collaboration-and-whiteboarding/collaboration-and-whiteboarding.md`; `company/culture/all-remote/collaboration-and-whiteboarding/setups.md`; `company/culture/all-remote/guide/design.md`; `company/culture/all-remote/guide/finance.md`; `company/culture/all-remote/guide/people-operations.md`.

### Phụ lục E — 26 file có HTML/shortcode details

`company/quote-to-cash.md`; `people-group/engagement.md`; `people-group/general-onboarding/onboarding-buddies.md`; `people-group/time-off-and-absence/leave-types.md`; `people-group/time-off-and-absence/time-away-philosophy.md`; `people-group/time-off-and-absence/time-off-types.md`; `people-policies/people-policies.md`; `total-rewards/benefits/modern-health.md`; `total-rewards/benefits/general-and-entity-benefits/bv-benefits-belgium.md`; `total-rewards/benefits/general-and-entity-benefits/bv-benefits-finland.md`; `total-rewards/benefits/general-and-entity-benefits/bv-benefits-netherlands.md`; `total-rewards/benefits/general-and-entity-benefits/canada-corp-benefits.md`; `total-rewards/benefits/general-and-entity-benefits/financial-wellness.md`; `total-rewards/benefits/general-and-entity-benefits/france-sas.md`; `total-rewards/benefits/general-and-entity-benefits/general-and-entity-benefits.md`; `total-rewards/benefits/general-and-entity-benefits/gitlab-gk.md`; `total-rewards/benefits/general-and-entity-benefits/gitlab-ireland-ltd.md`; `total-rewards/benefits/general-and-entity-benefits/global-expansion.md`; `total-rewards/benefits/general-and-entity-benefits/korea-ltd-benefits.md`; `total-rewards/benefits/general-and-entity-benefits/ltd-benefits-uk.md`; `total-rewards/benefits/general-and-entity-benefits/papaya-global-benefits.md`; `total-rewards/benefits/general-and-entity-benefits/pty-benefits-australia.md`; `total-rewards/benefits/general-and-entity-benefits/pty-benefits-new-zealand.md`; `total-rewards/benefits/general-and-entity-benefits/remote-com.md`; `total-rewards/benefits/general-and-entity-benefits/singapore-pte-ltd.md`; `total-rewards/benefits/general-and-entity-benefits/inc-benefits-us/inc-benefits-us.md`.

### Phụ lục F — Semantic structures cần bảo vệ

**47 file có Markdown table:** `communication/chat.md`; `communication/communication.md`; `communication/confidentiality-levels.md`; `company/amas.md`; `company/gitlab-all-company-meetings.md`; `company/quote-to-cash.md`; `company/structure.md`; `company/culture/cross-culture-collaboration-guide.md`; `company/culture/all-remote/mental-health.md`; `company/culture/all-remote/collaboration-and-whiteboarding/setups.md`; `finance/committee-composition.md`; `finance/finance.md`; `finance/spending-company-money.md`; `finance/travel/travel.md`; `people-group/acceptable-use-policy.md`; `people-group/anti-harassment.md`; `people-group/competencies.md`; `people-group/employment-solutions.md`; `people-group/engagement.md`; `people-group/guidance-on-feedback.md`; `people-group/organizational-change-management.md`; `people-group/people-group-program-management.md`; `people-group/people-group.md`; `people-group/promotions-transfers.md`; `people-group/talent-assessment.md`; `people-group/general-onboarding/tanewki-tips.md`; `people-group/learning-and-development/learning-and-development.md`; `people-group/learning-and-development/career-development/career-development.md`; `people-group/learning-and-development/career-development/igp-guide.md`; `people-group/learning-and-development/elevate-programs/elevate-programs.md`; `people-group/learning-and-development/growth-and-development/tax.md`; `people-group/learning-and-development/level-up/level-up.md`; `people-group/learning-and-development/mentor/mentor.md`; `people-group/offboarding/offboarding_standards.md`; `people-policies/people-policies.md`; `people-policies/france-sas/right-to-disconnect-charter.md`; `people-policies/india-ltd/india-ltd.md`; `people-policies/ireland-ltd/right-to-disconnect-policy.md`; `people-policies/leave-of-absence/us.md`; `total-rewards/incentives.md`; `total-rewards/total-rewards.md`; `total-rewards/benefits/general-and-entity-benefits/bv-benefits-belgium.md`; `total-rewards/benefits/general-and-entity-benefits/bv-benefits-netherlands.md`; `total-rewards/benefits/general-and-entity-benefits/general-and-entity-benefits.md`; `total-rewards/benefits/general-and-entity-benefits/ltd-benefits-uk.md`; `total-rewards/benefits/general-and-entity-benefits/pty-benefits-australia.md`; `values/values.md`.

**46 file có ảnh:** `communication/communication.md`; `company/faq-gitlab-licensing-technology-to-independent-chinese-company.md`; `company/quote-to-cash.md`; `company/culture/all-remote/all-remote.md`; `company/culture/all-remote/being-a-great-remote-manager.md`; `company/culture/all-remote/building-culture.md`; `company/culture/all-remote/getting-started.md`; `company/culture/all-remote/gitlab-for-remote.md`; `company/culture/all-remote/handbook-first.md`; `company/culture/all-remote/informal-communication.md`; `company/culture/all-remote/internship.md`; `company/culture/all-remote/live-doc-meetings.md`; `company/culture/all-remote/meetings.md`; `company/culture/all-remote/mental-health.md`; `company/culture/all-remote/non-linear-workday.md`; `company/culture/all-remote/onboarding.md`; `company/culture/all-remote/parenting.md`; `company/culture/all-remote/phases-of-remote-adaptation.md`; `company/culture/all-remote/remote-benefits.md`; `company/culture/all-remote/remote-vision.md`; `company/culture/all-remote/remote-work-emergency-plan.md`; `company/culture/all-remote/remote-work-report.md`; `company/culture/all-remote/remote-work-starter-guide.md`; `company/culture/all-remote/scaling.md`; `company/culture/all-remote/stages.md`; `company/culture/all-remote/terminology.md`; `company/culture/all-remote/the-gitlab-test-remote-work.md`; `company/culture/all-remote/what-not-to-do.md`; `company/culture/all-remote/work-from-home-field-guide.md`; `company/culture/all-remote/working-while-traveling.md`; `company/culture/all-remote/workspace.md`; `company/culture/all-remote/collaboration-and-whiteboarding/collaboration-and-whiteboarding.md`; `company/culture/all-remote/collaboration-and-whiteboarding/setups.md`; `company/culture/all-remote/guide/design.md`; `company/culture/all-remote/guide/finance.md`; `company/culture/all-remote/guide/people-operations.md`; `finance/expenses.md`; `people-group/competencies.md`; `people-group/guidance-on-feedback.md`; `people-group/general-onboarding/tanewki-tips.md`; `people-group/learning-and-development/career-development/career-development.md`; `people-group/learning-and-development/career-development/igp-guide.md`; `people-group/learning-and-development/elevate-programs/elevate/elevate.md`; `people-group/learning-and-development/elevate-programs/elevate-prep/elevate-prep.md`; `people-group/learning-and-development/team-workshops/team-workshops.md`; `values/values.md`.

**9 file có fenced code:** `communication/communication.md`; `company/cadence.md`; `company/quote-to-cash.md`; `company/culture/songbook.md`; `people-group/talent-development-program.md`; `people-group/general-onboarding/mr-buddies.md`; `people-group/offboarding/offboarding.md`; `total-rewards/incentives.md`; `total-rewards/compensation/compensation-review-cycle/compensation-review-cycle.md`.

**6 file có Mermaid:** `communication/communication.md`; `company/cadence.md`; `company/quote-to-cash.md`; `people-group/talent-development-program.md`; `total-rewards/incentives.md`; `total-rewards/compensation/compensation-review-cycle/compensation-review-cycle.md`.

**9 file có `<br>`:** `communication/communication.md`; `people-group/organizational-change-management.md`; `people-group/promotions-transfers.md`; `people-group/talent-assessment.md`; `people-group/talent-development-program.md`; `people-group/learning-and-development/career-development/career-development.md`; `people-policies/leave-of-absence/us.md`; `total-rewards/benefits/general-and-entity-benefits/ltd-benefits-uk.md`; `total-rewards/compensation/compensation-review-cycle/compensation-review-cycle.md`.

## 6. Tiêu chí hoàn thành roadmap

Trước khi bật chunking/embedding cho corpus:

- Mỗi file có trạng thái rõ: indexable, partial, hold hoặc skip, kèm lý do.
- Không còn raw include/shortcode syntax trong `page_content` đưa vào embedding.
- Các file partial không bị hiểu nhầm là nguồn đầy đủ; file hold/skip không sinh vector.
- Front matter chỉ nằm trong metadata; source path đầy đủ được gắn vào từng chunk.
- Bảng, code, Mermaid, details, link text và điều kiện policy còn nguyên nghĩa sau Cleaner.
- Các trang empty/pointer/placeholder và ba tài liệu có access metadata được xử lý theo đúng gate ở Bước 1.
- Preview nội dung sạch và chunk trên representative set trước khi chạy batch embedding toàn corpus.

