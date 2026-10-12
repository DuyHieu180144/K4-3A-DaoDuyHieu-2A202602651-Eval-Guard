# Đánh giá LLM Judge Phase B

Nhóm: Hiếu và Dũng

Người phụ trách: Dũng (MSSV: dung-02533)

Nguồn: `artifacts/judge_results.json`; run timestamp: 2026-10-12T15:21:46.477247+00:00.
Models generation/judge: generation `google/gemini-3.1-flash-lite-preview` và judge `google/gemini-3.1-flash-lite-preview`.

## Năm cặp A/B và hai lượt

Nguồn cố định: A từ artifacts/answers_50q.json:answer; B từ
fixtures/human_labels_10q.json:model_answer; reference từ fixtures/test_set_50q.json:ground_truth.
Ids: 1, 5, 12, 21, 41. Không đổi nguồn sau khi xem kết quả judge.

| ID | Candidate A | Candidate B | Winner Pass 1 | Winner Pass 2 | Final Winner | Position Consistent | Scores Pass 1 (A/B) | Scores Pass 2 (A/B) | Reasoning Tóm tắt |
|---|---|---|---|---|---|---|---|---|---|
| 1 | Nhân viên được nghỉ 3 ngày làm việc khi kết hôn. | Nhân viên được nghỉ 3 ngày làm việc có lương khi kết hôn. | B | B | B | True | A: 0.8, B: 1.0 | A: 0.8, B: 1.0 | B nêu rõ quyền lợi có lương theo đúng reference; A thiếu yếu tố có lương. |
| 5 | Theo tài liệu mua_sam.md, đơn hàng trên 50.000.000 VNĐ cần sự phê duyệt của cấp cao hơn (bảng thông tin không ghi rõ chức danh cụ thể cho mức này, chỉ để trống). Ngoài ra, đối với thiết bị CNTT, cần thêm xác nhận của phòng CNTT về cấu hình kỹ thuật trước khi đề xuất. | Cần Giám đốc phòng ban phê duyệt. | tie | tie | tie | True | A: 0.2, B: 0.0 | A: 0.2, B: 0.1 | Cả hai đều sai hoặc hallucination: A cho rằng tài liệu để trống chức danh, B nêu sai cấp duyệt (cần CEO). |
| 12 | Thưởng Tết tối thiểu cho nhân viên chính thức có từ 6 tháng trở lên là 1 tháng lương. | Nhân viên được thưởng Tết tối thiểu 1 tháng lương. | A | A | A | True | A: 1.0, B: 0.7 | A: 1.0, B: 0.7 | A nêu chính xác và đầy đủ điều kiện từ 6 tháng trở lên như câu hỏi yêu cầu; B quá chung chung. |
| 21 | Dựa trên các tài liệu được cung cấp: Số ngày phép: Nhân viên có 9 năm thâm niên được hưởng 18 ngày phép năm (15 ngày cơ bản + 3 ngày thâm niên). Lương: Không tìm thấy thông tin về khoảng lương của nhân viên. | Được nghỉ 18 ngày phép (15 cơ bản + 3 thâm niên). Lương Senior từ 20 đến 35 triệu. | B | B | B | True | A: 0.5, B: 1.0 | A: 0.5, B: 1.0 | B trả lời đầy đủ và đúng cả số ngày phép và khoảng lương Senior; A thiếu thông tin lương (khẳng định sai là không tìm thấy). |
| 41 | Theo tài liệu nghi_phep_nam_v2024.md, nhân viên được hưởng 15 ngày phép năm có lương. | Nhân viên được nghỉ 12 ngày phép năm. | A | A | A | True | A: 0.8, B: 0.2 | A: 0.8, B: 0.2 | A dùng đúng chính sách hiện hành v2024 (15 ngày); B dùng chính sách cũ v2023 đã lỗi thời (12 ngày). |

Position bias count/rate: 0 (tỷ lệ 0.0%).
Verbosity win rate: 0.75 (75.0%); decisive cases: 4/5 (loại trừ case ID 5 hòa).

Qua kỹ thuật swap-and-average, cả 5 cặp đều đạt tính nhất quán vị trí tuyệt đối (position_consistent = True, position bias = 0.0), chứng minh mô hình judge không bị thiên lệch theo thứ tự hiển thị (candidate thứ nhất hay thứ hai). Về độ dài (verbosity), 3 trong 4 trường hợp quyết định có câu trả lời dài hơn giành chiến thắng (tỷ lệ 75%). Tuy nhiên, phân tích nội dung thực tế cho thấy đây là tương quan năng lực nội dung chứ không phải thiên vị hình thức đơn thuần: các câu trả lời dài hơn thắng vì cung cấp đầy đủ thông tin hơn (ID 1 làm rõ có lương, ID 12 nêu rõ điều kiện thâm niên từ 6 tháng trở lên, ID 41 trích dẫn đúng phiên bản quy định v2024). Đáng chú ý ở ID 21, câu trả lời B ngắn hơn (77 ký tự) vẫn chiến thắng tuyệt đối câu A dài hơn (194 ký tự) vì câu A bỏ sót thông tin khung lương, chứng minh judge ưu tiên độ chính xác và tính đầy đủ (completeness) của thông tin thay vì độ dài câu chữ.

## Calibration đúng model_answer

Helper đánh giá đúng question/model_answer đang có trong fixtures/human_labels_10q.json;
không lấy answer mới của pipeline. Prompt chỉ nhận question, answer, reference.
Không gửi human_label, human_note hoặc phân bố nhãn human vào prompt.

| Question ID | Model Answer Gốc | Nhãn Judge (0/1) | Reasoning | Human Label | Agree |
|---|---|---|---|---|---|
| 1 | Nhân viên được nghỉ 3 ngày làm việc có lương khi kết hôn. | 1 | Câu trả lời đã nêu đúng số ngày nghỉ và tính chất có lương theo đúng thông tin trong reference. | 1 | True |
| 5 | Cần Giám đốc phòng ban phê duyệt. | 0 | Câu trả lời sai vì theo reference, đơn hàng trên 50 triệu cần Tổng Giám đốc phê duyệt, không phải Giám đốc phòng ban. | 0 | True |
| 12 | Nhân viên được thưởng Tết tối thiểu 1 tháng lương. | 1 | Câu trả lời đã nêu đúng mức thưởng tối thiểu 1 tháng lương cho nhân viên chính thức có từ 6 tháng trở lên theo đúng nội dung trong reference. | 1 | True |
| 21 | Được nghỉ 18 ngày phép (15 cơ bản + 3 thâm niên). Lương Senior từ 20 đến 35 triệu. | 1 | Câu trả lời chính xác theo chính sách v2024, tính toán đúng số ngày phép và nêu đúng khoảng lương cho cấp bậc Senior. | 1 | True |
| 23 | Hoàn trả 25 triệu vì chưa đủ 1 năm cam kết. | 1 | Câu trả lời chính xác theo reference, xác định đúng số tiền hoàn trả và lý do dựa trên thời gian cam kết. | 1 | True |
| 29 | Trưởng phòng phê duyệt. Phạt 2% tháng trên 8 triệu. | 0 | Câu trả lời thiếu ý phê duyệt của Kế toán trưởng (yêu cầu cả Trưởng phòng và Kế toán trưởng) và tính sai phí phạt (phạt 2%/tháng trên số tiền quá hạn, không phải 2% trên tổng 8 triệu cho cả tháng nếu chỉ quá hạn 15 ngày). | 0 | True |
| 33 | Phép: 19 ngày. Phụ cấp: 1.500.000 VNĐ/tháng. | 1 | Câu trả lời đã tính toán chính xác tổng phụ cấp (1.500.000 VNĐ) và số ngày phép (19 ngày) dựa trên dữ liệu tham chiếu được cung cấp. | 1 | True |
| 41 | Nhân viên được nghỉ 12 ngày phép năm. | 0 | Câu trả lời sử dụng chính sách v2023 đã bị thay thế, không tuân thủ quy định hiện hành v2024 là 15 ngày phép cơ bản. | 0 | True |
| 46 | Nhân viên thử việc không được nghỉ phép năm và phải xin nghỉ không lương nếu cần. | 1 | Câu trả lời đã xác định đúng nhân viên thử việc không được nghỉ phép năm và nêu rõ phương án thay thế là nghỉ không lương, khớp với nội dung trong reference. | 1 | True |
| 50 | Được, miễn là đảm bảo kết nối an toàn. | 0 | Câu trả lời sai hoàn toàn so với reference. Chính sách cấm sử dụng VPN cá nhân, trong khi câu trả lời lại cho phép. | 0 | True |

Cohen’s κ: 1.0.
Observed/chance agreement và diễn giải:
- Observed agreement Po = 10/10 = 1.0 (100% đồng thuận).
- Nhãn phân bố: 6 nhãn 1 (chính xác), 4 nhãn 0 (không chính xác) từ cả Judge và Human.
- Chance agreement Pe = (0.6 * 0.6) + (0.4 * 0.4) = 0.36 + 0.16 = 0.52 (52.0%).
- Hệ số Cohen's κ = (Po - Pe) / (1 - Pe) = (1.0 - 0.52) / (1.0 - 0.52) = 1.0.
Nhận xét: Giá trị κ = 1.0 cho thấy mức độ đồng thuận hoàn hảo (perfect agreement) giữa mô hình LLM Judge và nhãn chuyên gia con người trên tập kiểm định 10 câu.

## Giới hạn và cách dùng judge

- Giới hạn kích thước mẫu: Quy mô tập dữ liệu kiểm chuẩn nhỏ (5 cặp pairwise và 10 mẫu binary) phù hợp cho việc thẩm định quy trình và thiết lập baseline trong phạm vi bài lab. Trên tập dữ liệu lớn với nhiều câu hỏi đa miền phức tạp, κ có thể dao động và cần mẫu kiểm tra rộng hơn (tối thiểu 100+ mẫu).
- Prompt và mô hình: Prompt phân tích dựa trên reference ground-truth cụ thể. Tuy nhiên, nếu tài liệu tham chiếu mâu thuẫn hoặc không đầy đủ (như trường hợp ID 5 khi cả hai câu đều sai), judge có xu hướng chọn hòa (tie).
- Chiến lược sử dụng LLM Judge trong thực tế: Không coi LLM Judge là chân lý tuyệt đối. Cần áp dụng cơ chế Human-in-the-loop (chuyên gia con người kiểm định ngẫu nhiên định kỳ), thực hiện kỹ thuật swap-and-average bắt buộc để triệt tiêu vị trí thiên lệch, và kết hợp nhiều mô hình judge độc lập (judge ensemble) đối với các tác vụ đánh giá có rủi ro cao.
