# Blueprint CI/CD cho RAG và guardrails

Nhóm: Hiếu và Dũng

Người phụ trách: Đào Duy Hiếu (2A202602651) và Dũng (dung-02533)

Đây là **đề xuất CI/CD**, không phải workflow đã được triển khai/chạy.
Nguồn kết quả: artifacts/ragas_50q.json, judge_results.json, guard_results.json.
Run timestamp: 2026-10-12T15:41:29.120977+00:00; guard models: openai/gpt-4o-mini.
Models generation/evaluator/judge từ A/B: generation google/gemini-3.1-flash-lite-preview (nguồn answers_50q.json, ragas_50q.json), evaluator BAAI/bge-m3 và google/gemini-3.1-flash-lite-preview (nguồn ragas_50q.json), judge google/gemini-3.1-flash-lite-preview (nguồn judge_results.json).

## Kiến trúc và failure action

Input → Presidio → NeMo input → RAG → NeMo output → response.
Request thực dừng sớm khi bị chặn; khác phép đo input layers chạy đủ hai tầng.

Kiến trúc bảo vệ bao gồm hai chặng kiểm soát chính:
1. Input Guard (Pre-RAG):
   - Chặng 1: Presidio PII Scanner kiểm tra các thực thể nhạy cảm định danh (CCCD 12 số, CMND 9 số, số điện thoại Việt Nam, địa chỉ email). Nếu phát hiện PII trái phép, hệ thống lập tức short-circuit dừng xử lý (blocked) và trả về thông báo từ chối tiêu chuẩn, không kích hoạt LLM hay vector database.
   - Chặng 2: NeMo Guardrails Input Rail (self_check_input) kiểm tra các rủi ro bảo mật như prompt injection, jailbreak, giả mạo danh tính, truy xuất dữ liệu ngoài phạm vi IT/HR policy. Nếu phát hiện vi phạm, request dừng ngay lập tức.
2. RAG Pipeline: Chỉ khi vượt qua cả hai tầng input guard, truy vấn mới được đưa vào hệ thống RAG (hybrid search BM25 + Qdrant dense vector, bge-reranker và LLM generation).
3. Output Guard (Post-RAG):
   - NeMo Guardrails Output Rail (self_check_output) quét phản hồi của mô hình để ngăn chặn rò rỉ dữ liệu nhạy cảm của cá nhân, thông tin lương riêng tư hoặc mật khẩu hệ thống. Nếu phản hồi vi phạm, output rail thay thế bằng thông điệp an toàn từ chối trước khi trả về cho người dùng.
4. Quản lý Secrets, Logging và Fallback:
   - Toàn bộ API keys (OPENROUTER_API_KEY, HF_TOKEN) được lưu trữ an toàn trong Secret Store (ví dụ: GitHub Secrets, AWS Secrets Manager hoặc HashiCorp Vault), không ghi vào log hay mã nguồn.
   - Logging tuân thủ nguyên tắc Privacy-by-Design: toàn bộ dữ liệu người dùng được redact PII trước khi đưa vào audit log.
   - Khi remote API gặp sự cố timeout hoặc quá tải (5xx), hệ thống fallback về thông báo bảo trì hoặc từ chối an toàn thay vì bypass guardrails (fail-closed).

## Phạm vi và số đo latency

Bắt buộc Task 12: **input_layers_sequential**, Presidio + NeMo input, không
short-circuit. Engines tạo trước đo; có hai warm-up thật không tính vào mẫu.
Percentile nội suy tuyến tính từ raw samples; tổng từ tổng từng sample.

Số mẫu timed: 20; warm-up: 2;
phương pháp: linear.

| Layer / scope | P50 ms | P95 ms | P99 ms | Tình trạng |
|---|---|---|---|---|
| Presidio | 7.63 | 8.99 | 9.27 | Đạt budget target (xử lý regex cục bộ cực nhanh dưới 10ms) |
| NeMo input | 1773.39 | 2711.32 | 2850.02 | Vượt budget do latency gọi LLM qua OpenRouter API từ xa |
| Input guard sequential | 1781.02 | 2719.97 | 2856.90 | Vượt budget 500ms (P95 = 2719.97 ms > 500 ms) |
| RAG | chưa đo | chưa đo | chưa đo | Ngoài phạm vi bắt buộc |
| NeMo output | chưa đo | chưa đo | chưa đo | Ngoài phạm vi bắt buộc |
| Full guard / short-circuit request | chưa đo | chưa đo | chưa đo | Không suy từ input_guard_ms |

Input-layer budget target: 500ms; kết quả thực tế/budget_ok: P95 = 2719.97 ms; False.
Điểm nghẽn độ trễ (bottleneck) nằm hoàn toàn ở NeMo input rail: việc gọi mô hình LLM qua OpenRouter từ xa tiêu tốn từ 1.0 đến 2.8 giây cho mỗi lượt phân loại, trong khi Presidio chỉ mất dưới 9ms. Để đưa độ trễ toàn tầng input về dưới ngân sách 500ms trong môi trường production, đề xuất thay thế remote LLM bằng mô hình phân loại nhỏ chạy on-premise/local (ví dụ: DeBERTa-v3-small hoặc Llama-3.2-1B quantized với vLLM) kết hợp caching các mẫu truy vấn phổ biến.
Đối với các thành phần ngoài phạm vi bắt buộc (RAG, NeMo output, full short-circuit request), hệ thống hiện giữ nguyên trạng thái chưa đo theo đúng quy định bài lab. Kế hoạch đo trong tương lai sẽ bổ sung ít nhất 50 mẫu ngẫu nhiên trên pipeline hoàn chỉnh có ghi timestamp chi tiết (t0 đến t4) sau khi hệ thống staging được thiết lập đầy đủ.

## CI gates đề xuất

- RAGAS faithfulness ≥0.75, avg_score ≥0.65 trên 50 câu.
- Attacks ≥18/20 cho CI đề xuất; clean 8/8 allowed; output cases đúng.
- Full guard P95 <500ms chỉ áp dụng sau khi thực sự đo full guard.

Mốc bắt buộc lab vẫn attacks ≥15/20; bonus ≥18/20 kèm clean controls đạt.
Đề xuất triển khai GitHub Actions workflow chạy tự động trên pull requests:
- Job 1: python -m pytest tests/ -q (kiểm tra toàn bộ 97 unit tests offline, fail nếu exit code != 0).
- Job 2: python scripts/check_lab.py --with-tests (kiểm tra toàn bộ ràng buộc schema, contracts và provenance).
- Script kiểm tra chất lượng sẽ parse các artifact JSON và trả về exit code 1 nếu:
  + ragas_report avg_score < 0.65 hoặc ragas_report faithfulness < 0.75
  + guard_report adversarial passed < 18 hoặc guard_report clean false_positive_rate > 0
Workflow này được thiết kế theo dạng đề xuất kiến trúc CI/CD phục vụ bài báo cáo và kiểm tra chất lượng tự động; nhóm chưa triển khai workflow tự động trên cloud runner do việc chạy thực nghiệm live phụ thuộc vào tài nguyên API có phí.

## Monitoring và cải tiến

Chiến lược giám sát production đề xuất:
- Giám sát độ trễ (Latency tracking): Đo lường P50/P95/P99 trên từng tầng (Presidio, NeMo, Retrieval, Generation). Cảnh báo nếu P95 input guard vượt quá 3000ms trong 5 phút liên tục.
- Giám sát an toàn và False Positives: Tỷ lệ chặn đầu vào (block rate) bình thường dự kiến dưới 5%. Cảnh báo khẩn cấp tới đội ngũ bảo mật và AI Ops nếu tỷ lệ chặn tăng đột biến (> 15%), đồng thời lưu vết các truy vấn bị chặn (đã che giấu PII) để đội ngũ con người rà soát false positives hàng ngày.
- Giám sát Drift và chất lượng câu trả lời: Lấy mẫu ngẫu nhiên 5% traffic thực tế để chạy định kỳ qua LLM Judge và chuyên gia con người đánh giá chất lượng; theo dõi độ tương quan Cohen's κ để phát hiện suy giảm năng lực phán đoán.
- Giới hạn của bộ dữ liệu thực nghiệm: Bộ benchmark hiện tại (50 câu RAG, 20 attacks, 8 clean controls, 4 output cases) có phạm vi bao phủ còn hạn hẹp đối với các tình huống biên phức tạp trong đời thực.

RAGAS mean/worst distribution: RAGAS mean score toàn bộ 50 câu đạt 0.786; worst distribution là multi_hop với điểm trung bình 0.651 (so với factual 0.918 và adversarial 0.792).
Cohen’s κ: 1.0 (đồng thuận hoàn hảo giữa Judge và Human trên 10 câu calibration).
Attacks passed: 20/20; clean false_positive_rate: 0.0 (8/8 clean inputs được cho phép an toàn).

3–5 giải pháp cải tiến có thể kiểm chứng dựa trên bằng chứng thực nghiệm của nhóm:
1. Nâng cao chất lượng multi-hop retrieval: Dữ liệu RAGAS cho thấy multi_hop là phân bố yếu nhất (0.651) do retrieval không bao quát đủ các tài liệu liên quan (như case ID 22 mua laptop 30 triệu). Giải pháp là triển khai query decomposition (phân rã câu hỏi phức tạp thành các sub-queries) để cải thiện context recall từ 0.7 lên trên 0.9.
2. Tối ưu hóa độ trễ guardrails bằng local classifier: Thay thế NeMo OpenRouter API bằng mô hình phân loại cục bộ DeBERTa fine-tuned trên dữ liệu jailbreak/policy tiếng Việt nhằm giảm P95 từ 2719.97 ms xuống dưới ngân sách 500 ms.
3. Mở rộng bộ nhận diện PII tiếng Việt: Mặc dù Presidio đạt 100% độ chính xác trên bộ kiểm thử, cần bổ sung thêm nhận diện số tài khoản ngân hàng và mã số thuế cá nhân tiếng Việt bằng custom PatternRecognizer để tăng độ bao phủ bảo vệ quyền riêng tư.
4. Mở rộng tập dữ liệu LLM Judge: Tăng kích thước tập calibration từ 10 mẫu lên ít nhất 100 mẫu bao quát nhiều chủ đề chính sách để đảm bảo tính khái quát hóa của hệ thống đánh giá tự động trong môi trường vận hành lớn.
