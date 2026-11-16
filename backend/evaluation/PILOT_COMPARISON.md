# So sánh chất lượng testset — 12/11/2026

Đã tạo 15 câu mới bằng Ragas và giữ riêng dữ liệu sinh thô, đánh giá và bản được
trợ lý chỉnh sửa. Đây là đánh giá chất lượng testset, chưa chạy retrieval benchmark.

## Thay đổi đã thực hiện

- Giữ `gpt-4o-mini`, Ragas 0.4.3 và tích hợp LangChain hiện có.
- Dùng keyphrase để chọn ý định câu hỏi thay cho entity mặc định; persona là nhân
  viên GitLab, phong cách PERFECT_GRAMMAR và độ dài MEDIUM.
- Prompt yêu cầu câu hỏi cụ thể và đáp án giữ điều kiện, ngoại lệ, chủ thể, mức độ
  bắt buộc và không suy diễn nội dung sau liên kết. Có ví dụ về điều kiện cần làm rõ.
- Lượt thử đầu dùng 5 chunk và sinh nhiều câu trùng. Giữ lại ở `pilot_v2/`.
- Lượt tinh chỉnh dùng 15 chunk khác nhau thuộc 5 document, mỗi chunk một câu.
  Ba chunk của pilot đầu vẫn có trong tập này; phần còn lại mở rộng ngữ cảnh.
- Chỉ dùng transform trích keyphrase cần cho single-hop, không gọi embedding
  hoặc xây quan hệ similarity không được dùng trong lượt này.

## Kết quả trên dữ liệu sinh thô

- Pilot đầu: 6 câu; 2 giữ, 2 cần sửa, 2 loại; 6 câu khác nhau.
- Lượt cải thiện đầu: 15 câu; 6 giữ, 3 cần sửa, 6 loại; chỉ 11 câu khác nhau
  sau chuẩn hóa chữ hoa/khoảng trắng, và 6 mẫu trùng ý định được đánh dấu.
- Lượt tinh chỉnh: 15 câu; 10 giữ (66,7%), 5 cần sửa, 0 loại; 15 câu khác nhau.

Tất cả được chấm lại bằng cùng rubric trong `review_annotations.json`. Nhãn
pilot đầu khác báo cáo lịch sử 1/6: câu 02 thực tế vẫn dùng 'beneficial' và giữ
các điều kiện quan trọng, nên được nâng từ 'revise' lên 'accept'. Đánh giá cũ quá
nghiêm ở câu này; dữ liệu gốc và đánh giá lịch sử vẫn được giữ để đối chiếu.

Các lỗi còn lại ở lượt tinh chỉnh:

- Câu 02: bỏ điều kiện khi khuyên thêm lời giải thích mục đích AMA vào agenda.
- Câu 05: gắn điều kiện được yêu cầu vào việc trả tài sản khi nghỉ việc, trong
  khi nguồn quy định trả computing resources khi nghỉ việc là yêu cầu chung.
- Câu 07: suy diễn AP là bên gắn cờ và bỏ điều kiện khi AP liên hệ làm rõ.
- Câu 08: gọi mốc đặt vé nội địa lý tưởng là requirement.
- Câu 15: câu hỏi chưa chỉ rõ bối cảnh nghỉ quân sự hơn 31 ngày và đáp án chưa
  thực sự trả lời câu hỏi về điều kiện.

## Bộ dữ liệu có thể dùng tiếp

- `pilot_v2_refined/testset_raw.json`: 15 mẫu nguyên gốc do Ragas sinh.
- `pilot_v2_refined/testset_accepted_raw.json`: 10 mẫu được trợ lý đánh giá có
  thể giữ mà không sửa. Không có mẫu nào được chuyên gia nghiệp vụ phê duyệt.
- `pilot_v2_refined/testset_curated.json`: đủ 15 mẫu; 5 mẫu trên đã được trợ lý
  chỉnh câu hỏi hoặc đáp án trực tiếp theo bằng chứng nguồn. Có trường trước/sau
  chỉnh sửa và `edited_by_assistant`; không được mô tả là 15/15 sinh tự động đạt.
- Mỗi mẫu có document ID, chunk ID, section và đoạn nguồn để kiểm chứng.

## Chi phí callback ghi nhận

- Lượt cải thiện đầu: 25 request OpenAI thành công, 17.338 token input và 1.389
  token output; ước tính 0,00343410 USD.
- Lượt tinh chỉnh: 45 request OpenAI thành công, 25.775 token input và 1.852
  token output; ước tính 0,00497745 USD.
- Tổng công việc lần này: khoảng 0,00841155 USD; không gọi Voyage embedding.
- Lượt pilot đầu thành công trước đây: khoảng 0,00307845 USD OpenAI; tổng gồm
  hai lượt lỗi trước đó khoảng 0,00619575 USD OpenAI, chưa tính Voyage.

Các số này là ước tính từ usage của request thành công do callback quan sát được,
không phải hóa đơn cuối. Có thể khác số tiền bị trừ thực tế do cache/credit hoặc
request không được ghi nhận. Không lấy tổng có retry của pilot cũ làm chi phí
đại diện cho mỗi lần sinh testset.

## Giới hạn khi kết luận

Chất lượng tổng thể và độ đa dạng đã tốt hơn trên tập nhỏ này, nhưng nguồn và
prompt thay đổi cùng lúc nên chưa thể quy cải thiện cho riêng prompt. Chỉ xét
ba chunk cũ, pilot đầu có 2/6 mẫu được giữ còn lượt tinh chỉnh có 1/3; các chi
tiết chính sách có điều kiện vẫn là điểm yếu. Không có kiểm định thống kê hay
thẩm định độc lập của chuyên gia. Các câu mới đều là single-hop, không đại diện
đầy đủ 163 tài liệu hoặc truy vấn thực tế. Nên duyệt 15 mẫu curated trước khi
dùng làm ground truth và bổ sung dần câu hỏi thực tế.
