# Kiểm tra Embedding và dữ liệu trước index — 07/11/2026

> Cập nhật 08/11/2026: đã sửa 9 file nguồn Markdown bằng cách thay những đường
> phân cách `---` gây lỗi thành `***`, giữ nguyên cách hiển thị. Báo cáo chạy
> lại `backend/storage/processed/token-estimate-voyage4-markdown-fixed.json`:
> 163 file, 3.705 chunk, không còn file lỗi Chunking; còn 2 chunk placeholder
> ở `cadence.md` và `values.md`. Các số liệu bên dưới là kết quả trước khi sửa.

## Embedding

- Chạy `embed_chunks` qua LangChain và Voyage thật với 2 chunk mẫu; cả hai
  `EmbeddedPoint` có 1.024 chiều và giữ đúng ID, text gốc và metadata.
- So sánh vector chunk đầu tiên trong batch với cùng chunk embedding riêng:
  cosine 0,999987; vector này khớp chunk thứ nhất hơn chunk thứ hai. Đây là
  kiểm tra mẫu nhỏ, không phải bảo đảm thứ tự trong mọi tình huống.
- `embed_query` qua `voyage-4-lite` trả vector 1.024 chiều; trong hai mẫu, câu
  hỏi về làm việc từ xa gần chunk tương ứng nhất.
- Lần chạy đầu gặp HTTP 429 do tài khoản đang ở hạn mức 3 request/phút. Sau khi
  chờ, kiểm tra mẫu thành công. Lỗi API được báo lên; hiện chưa có cơ chế retry
  ở pipeline của dự án.
- 52 test liên quan Embedding và Chunking đạt. Đã sửa một kỳ vọng thông báo
  lỗi `source_end=0` trong test cho khớp validation hiện có.

Không gửi tài liệu handbook thật đến Voyage trong đợt kiểm tra này. Không có
kiểm thử API thật cho đầu vào vượt giới hạn hoặc key sai; những tình huống đó
cần kiểm tra riêng nếu cần trước khi vận hành.

## Báo cáo corpus

Đã chạy `estimate_embedding_tokens` trên `content/handbook`, tokenizer
`voyageai/voyage-4`, chunk size 700, overlap 70. Báo cáo chi tiết:
`backend/storage/processed/token-estimate-voyage4.json`. Báo cáo cũ BGE-M3
được giữ nguyên. Token chỉ là ước lượng nội dung, không tính prompt/API overhead.

- 163 file nguồn: 152 thành công, 2 xử lý một phần và 9 thất bại.
- 3.537 chunk được tạo: 3.362 text, 146 table, 23 code, 6 Mermaid.
- 483.970 token đầu vào embedding ước lượng; có 2 chunk rỗng sau cleaner.
- Số token và chunk chỉ bao gồm phần xử lý thành công, không đại diện toàn bộ
  corpus do 9 file chưa qua chunking.

Hai file xử lý một phần vì mỗi file có một chunk chỉ chứa placeholder nội dung
động không có trong nguồn: `company/cadence.md` (section Gantt Chart) và
`values/values.md` (section Playing politics is counter to GitLab values).
Không embedding placeholder là hợp lý; cần xem nguồn gốc nếu nội dung động
này quan trọng đối với retrieval.

Chín file gặp lỗi căn chỉnh Markdown section khi chunking:

1. `company/culture/exec-connect.md`
2. `company/operating-principles.md`
3. `people-group/givelab-volunteer-initiatives.md`
4. `people-group/learning-and-development/level-up/level-up.md`
5. `total-rewards/benefits/benefits.md`
6. `total-rewards/benefits/general-and-entity-benefits/bv-benefits-belgium.md`
7. `total-rewards/benefits/general-and-entity-benefits/bv-benefits-finland.md`
8. `total-rewards/benefits/general-and-entity-benefits/canada-corp-benefits.md`
9. `total-rewards/benefits/general-and-entity-benefits/financial-wellness.md`

Kiểm tra sơ bộ 3 file cho thấy bước căn chỉnh nhận diện một số dòng văn bản
như heading trong output splitter nhưng không khớp heading của tài liệu nguồn.
Chưa sửa lỗi; cần tái hiện và kiểm tra cấu trúc Markdown trước khi chọn cách sửa.

## Mẫu đã kiểm tra cục bộ

- `communication/communication.md`: 134 chunk, 14 bảng và 1 Mermaid; không có
  chunk bị loại bởi cleaner.
- `finance/expenses.md`: 109 chunk text; không có chunk bị loại.
- `company/culture/all-remote/mental-health.md`: 34 chunk, gồm 1 bảng; không có
  chunk bị loại.
- `company/culture/all-remote/remote-benefits.md`: 19 chunk text; không có
  chunk bị loại.
- `values/values.md`: 56 chunk, gồm 1 bảng; 1 chunk chỉ có placeholder bị loại.

Với các chunk hợp lệ trong 5 file trên, ID, document ID và khoảng vị trí nguồn
đều qua kiểm tra cơ bản; `storage_key` không được đưa vào metadata đầu ra.
Đã xem đầu một số bảng; đây chưa phải kiểm tra thủ công toàn bộ nội dung hay
chứng minh citation/retrieval chính xác. Bốn file đầu là ứng viên index thử;
`values.md` có thể thử với lưu ý nội dung động của một section chưa có.

## Còn lại trước khi index toàn corpus

1. Xác nhận nội dung động của 2 chunk bị loại có cần cho ứng dụng không.
2. Sửa/loại có chủ đích 9 file lỗi chunking, rồi chạy lại báo cáo.
3. Xây dựng lưu vector Qdrant, gắn indexing vào upload/import và kiểm tra quyền
   truy cập khi retrieval; các phần này chưa được triển khai trong đợt kiểm tra.
