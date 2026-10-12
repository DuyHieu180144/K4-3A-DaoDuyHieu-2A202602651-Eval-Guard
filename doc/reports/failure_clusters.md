# Phân tích lỗi Phase A

Người thực hiện batch: Hiếu. MSSV: xem `doc/TEAM.md`.

Nguồn: `artifacts/ragas_50q.json`; run kind: `live`; thời điểm: 2026-10-12 21:23:15 Asia/Ho_Chi_Minh.
Answers: 50 câu, generation mode `llm` cho 50/50 câu. Model generation: `google/gemini-3.1-flash-lite-preview`.
Evaluator models: `BAAI/bge-m3`, `google/gemini-3.1-flash-lite-preview`. Bộ test: factual 20, multi_hop 20, adversarial 10. SHA-256 nguồn answers/test set được lưu trong metadata artifact.

## Điểm theo distribution

| Metric | factual (20) | multi_hop (20) | adversarial (10) |
|---|---:|---:|---:|
| faithfulness | 0.9833 | 0.8333 | 0.9500 |
| answer_relevancy | 0.8884 | 0.6843 | 0.8523 |
| context_precision | 0.9500 | 0.4167 | 0.7333 |
| context_recall | 0.8500 | 0.6708 | 0.6333 |
| avg_score | 0.9179 | 0.6513 | 0.7922 |

## Bottom 10 và nguyên nhân

| Rank | ID | Distribution | Avg score | Worst metric | Question | Diagnosis | Suggested fix |
|---:|---:|---|---:|---|---|---|---|
| 1 | 22 | multi_hop | 0.3333 | answer_relevancy | Nếu cần mua một chiếc laptop 30 triệu cho nhân viên mới, ai phê duyệt và cần gì từ phòng CNTT? | Answer doesn't match question | Improve prompt template |
| 2 | 27 | multi_hop | 0.3750 | answer_relevancy | Nhân viên có thâm niên 7 năm theo v2024 được nghỉ bao nhiêu ngày phép? Nếu bị trừ thêm 4 ngày ốm không có giấy y tế thì còn lại bao nhiêu? | Answer doesn't match question | Improve prompt template |
| 3 | 30 | multi_hop | 0.3750 | answer_relevancy | So sánh quyền lợi bảo hiểm giữa nhân viên thử việc và nhân viên chính thức. | Answer doesn't match question | Improve prompt template |
| 4 | 33 | multi_hop | 0.3750 | answer_relevancy | Nhân viên Manager có thâm niên 12 năm: tổng phụ cấp hàng tháng và số ngày phép năm theo v2024 là bao nhiêu? | Answer doesn't match question | Improve prompt template |
| 5 | 5 | factual | 0.4408 | context_precision | Muốn mua thiết bị trị giá 55 triệu cần ai phê duyệt? | Too many irrelevant chunks | Add reranking or metadata filter |
| 6 | 49 | adversarial | 0.4550 | context_precision | Theo chính sách nghỉ phép cũ (v2023), nhân viên được nghỉ bao nhiêu ngày? Còn chính sách nào đang có hiệu lực hiện tại? | Too many irrelevant chunks | Add reranking or metadata filter |
| 7 | 39 | multi_hop | 0.4597 | context_precision | So sánh yêu cầu mật khẩu giữa policy v1.0 và v2.0 về độ dài tối thiểu, thời hạn đổi và MFA. | Too many irrelevant chunks | Add reranking or metadata filter |
| 8 | 26 | multi_hop | 0.4852 | context_precision | Nhân viên vừa kết hôn và cùng tuần đó có con kết hôn. Tổng số ngày nghỉ đặc biệt có lương là bao nhiêu? | Too many irrelevant chunks | Add reranking or metadata filter |
| 9 | 35 | multi_hop | 0.5220 | context_precision | Nhân viên Junior P1 có lương cơ bản 12 triệu vừa vào thử việc: nhận lương bao nhiêu và phụ cấp gì tháng đầu tiên? | Too many irrelevant chunks | Add reranking or metadata filter |
| 10 | 21 | multi_hop | 0.5244 | context_precision | Một nhân viên Senior có 9 năm thâm niên được nghỉ bao nhiêu ngày phép năm và lương trong khoảng nào? | Too many irrelevant chunks | Add reranking or metadata filter |

### Đối chiếu answer, context và ground truth

- **ID 22 (multi-hop, avg 0.3333):** câu trả lời nêu được xác nhận cấu hình từ CNTT nhưng nói không tìm thấy người phê duyệt. Ground truth yêu cầu Director cho laptop 30 triệu và ít nhất ba báo giá, ngoài xác nhận CNTT. Ba context có đoạn mua sắm CNTT nhưng lẫn nội dung đào tạo; truy xuất không phủ đủ các vế, rồi answer kết luận thiếu căn cứ.
- **ID 27 (multi-hop, avg 0.3750):** context có chính sách v2024: 15 ngày cơ bản và +1 ngày cho mỗi 3 năm. Answer tính một mốc thay vì hai mốc ở 7 năm, ra 16 thay vì 17; đồng thời không tính 4 ngày ốm như ground truth yêu cầu. Có lỗi tính toán/generation và thiếu context cho điều kiện nghỉ ốm.
- **ID 39 (multi-hop, avg 0.4597):** answer tìm đúng yêu cầu v2.0 nhưng báo không thấy v1.0 và MFA. Context đầu chỉ có v2.0; truy xuất không đưa đủ phiên bản để so sánh, dẫn đến câu trả lời thiếu hai vế.
- **ID 5 (factual, avg 0.4408):** context có bảng ngưỡng mua sắm nhưng đoạn được đưa vào kết thúc tại hàng “trên 50 triệu” mà không có chức danh. Answer nói chức danh không rõ, trong khi ground truth là CEO. Cần giữ hàng bảng qua ranh giới chunk và truy xuất đoạn kế tiếp.
- **ID 49 (adversarial, avg 0.4550):** answer phân biệt đúng 12 ngày của v2023 và 15 ngày v2024. Context precision bằng 0 cho thấy có nhiều nội dung không cần thiết/đối nghịch; điểm thấp không đồng nghĩa answer đã nhầm phiên bản.

## Matrix lỗi và nhóm yếu nhất

| Worst metric | factual | multi_hop | adversarial |
|---|---:|---:|---:|
| faithfulness | 1 | 3 | 1 |
| context_recall | 4 | 3 | 3 |
| context_precision | 2 | 8 | 4 |
| answer_relevancy | 13 | 6 | 2 |

Nhóm yếu nhất theo mean: **multi_hop (0.6513)**. Worst metric xuất hiện nhiều nhất: **answer_relevancy (21 câu)**.

Multi-hop thấp chủ yếu vì context precision chỉ 0.4167 và answer relevancy 0.6843: truy xuất top-k thường bỏ mất một trong nhiều điều kiện/version, trong khi đưa thêm chunk không liên quan. Ưu tiên sửa chunking bảng (giữ header + hàng), truy vấn từng vế multi-hop và kiểm tra đủ nguồn trước khi đổi prompt. Với phép tính/điều kiện nghỉ phép, yêu cầu answer nêu từng bước và nói rõ dữ kiện chưa tìm thấy thay vì tự suy diễn.

## Bẫy adversarial và giới hạn

Adversarial có mean 0.7922, cao hơn multi-hop nhưng thấp hơn factual; context recall 0.6333 là thấp nhất. ID 49 cho thấy model xử lý đúng xung đột v2023/v2024 khi cả hai nguồn được truy xuất, nhưng context precision 0.0000 cảnh báo retrieval còn đưa kèm chunk dư. Không suy ra toàn bộ bẫy adversarial đã được phát hiện chỉ từ mean của 10 câu.

Batch dùng Qdrant in-memory vì Qdrant local không kết nối được; kết quả chưa đo hành vi server Qdrant. Hai PDF scan (`BCTC.pdf` và nghị định dữ liệu cá nhân) không có text layer nên bị bỏ qua, làm giảm coverage nguồn. Embedding/reranker chạy local; Hugging Face không có token nên tải model ở chế độ unauthenticated. RAGAS là evaluator tự động trên 50 câu, chưa thay thế review nhãn người; cần kiểm tra thủ công các ca tính toán/version trước khi kết luận chất lượng.

## Hành động đề xuất cho lượt tiếp theo

1. Sửa table-aware chunking để không tách hàng phê duyệt khỏi header/chức danh; thêm regression cho ID 5 và ID 22.
2. Với multi-hop, truy vấn từng điều kiện/version, hợp nhất rồi rerank; kiểm tra đủ nguồn trong context trước khi sinh answer.
3. Thêm kiểm tra số học và yêu cầu answer trả lời riêng từng vế; với ngày ốm cần truy xuất policy đúng hoặc nói rõ thiếu dữ kiện.
4. OCR hai PDF scan nếu chúng thuộc corpus cần đánh giá; chạy lại cùng 50 câu rồi so sánh per-question và matrix.