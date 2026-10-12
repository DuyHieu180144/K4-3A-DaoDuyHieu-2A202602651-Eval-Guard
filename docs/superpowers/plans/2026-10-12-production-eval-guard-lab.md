# Production Eval + Guardrail Stack (Lab Day 24) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Hoàn thiện toàn bộ bài lab K4 Track 3A (Production Eval + Guardrail Stack): implement các hàm trong Phase A, B, C; sinh 50 câu trả lời từ RAG pipeline; chạy thực nghiệm live để tạo 4 artifact JSON; điền đầy đủ 3 báo cáo Markdown và TEAM.md; kiểm tra pass 100% check_lab và unit tests.

**Architecture:**
- Khối Đánh giá (Eval): RAGAS 4 metrics (Faithfulness, Answer Relevancy, Context Precision, Context Recall) trên 50 câu hỏi đa dạng (20 factual, 20 multi-hop, 10 adversarial).
- Khối Giám sát (LLM-as-Judge): Pairwise evaluation với cơ chế Swap-and-Average để khử position bias; tính chỉ số Cohen's Kappa đối chiếu với nhãn chuyên gia con người; đo lường verbosity bias.
- Khối Bảo vệ (Guardrails): Kiến trúc tuần tự gồm Presidio PII Scanner (phát hiện và làm mờ CCCD/CMND, SĐT VN, Email) + NeMo Guardrails Input Rail (chống Prompt Injection, Jailbreak, vi phạm chủ đề) + NeMo Output Rail (chặn rò rỉ dữ liệu nhạy cảm); đo đạc P95 latency (tối thiểu 20 mẫu sau 2 vòng warm-up).

**Tech Stack:** Python 3.12/3.11, Ragas 0.1.22, NeMo Guardrails 0.10.0, Presidio Analyzer/Anonymizer 2.2.364, Sentence-Transformers, OpenAI API (gpt-4o-mini), Scikit-Learn, Pytest.

**Spec:** [doc/ASSIGNMENT.md](file:///d:/Document/Ai_Thuc_Chien/12-10-2026/K4-3A-DaoDuyHieu-2A202602651-Eval-Guard/doc/ASSIGNMENT.md), [doc/CHECKPOINTS.md](file:///d:/Document/Ai_Thuc_Chien/12-10-2026/K4-3A-DaoDuyHieu-2A202602651-Eval-Guard/doc/CHECKPOINTS.md), [doc/RUBRIC.md](file:///d:/Document/Ai_Thuc_Chien/12-10-2026/K4-3A-DaoDuyHieu-2A202602651-Eval-Guard/doc/RUBRIC.md), [doc/REPORT_SCHEMAS.md](file:///d:/Document/Ai_Thuc_Chien/12-10-2026/K4-3A-DaoDuyHieu-2A202602651-Eval-Guard/doc/REPORT_SCHEMAS.md).

## Global Constraints

- Không còn comment `# TODO` trong bất kỳ file nào thuộc `src/phase_*.py`.
- Metadata phải theo chuẩn `format_version: 2`, `run_kind: "live"`, tách biệt rõ ràng 4 vai trò model: `generation`, `evaluator`, `judge`, `guard`.
- Tuyệt đối không hardcode nhãn hay leak `human_label` / `human_note` vào prompt của LLM judge.
- Input Guardrail phải đạt tối thiểu 15/20 attacks bị chặn (hướng tới >=18/20 cho bonus), 8/8 clean inputs được cho phép (0% false positive).
- Output Guardrail phải giữ nguyên 2 outputs an toàn và thay thế/redact 2 outputs nhạy cảm.
- Latency đo tầng input tuần tự (`input_layers_sequential`), loại bỏ 2 lần warm-up đầu, thu thập >= 20 mẫu thực tế.
- Các báo cáo markdown không được chứa bất kỳ placeholder dạng `{{...}}`, `[...]` hay ký tự `?`.

## Review Focus

1. **m4_eval adapter metadata**: `evaluate_ragas` phải trả về `raw["metadata"]["evaluator_models"]` với list model IDs thực tế (ví dụ: `["gpt-4o-mini", "BAAI/bge-m3"]`), không để trống và không fallback sang JUDGE_MODEL.
2. **DenseSearch fallback khi Docker tắt**: `m2_search.py` phải bắt cả `Exception` tổng quát khi kết nối Qdrant thất bại để fallback sang `QdrantClient(":memory:")` mượt mà không crash script.
3. **Cohen's Kappa Edge cases**: Khi tính $\kappa$, xử lý mẫu chuẩn xác để đạt kết quả tương thích `sklearn.metrics.cohen_kappa_score` trên 10 nhãn nhị phân.
4. **Presidio & NeMo Input Rails**: Đảm bảo regex cho CCCD (12 số), CMND (9 số) và SĐT VN (0[3-9]xxxxxxxx) bắt chính xác, không bắt nhầm câu hỏi hợp lệ.
5. **JSON Schema Draft 2020-12 compliance**: Tất cả các artifact JSON sinh ra phải thỏa mãn schema quy định trong `doc/schemas/`.

---

### Task 0: Môi trường & Thiết lập Pipeline RAG (Setup CP0)

**Files:**
- Modify: `.env` (tạo mới từ `.env.example`, điền `OPENAI_API_KEY`)
- Modify: `src/m2_search.py` (tinh chỉnh fallback Qdrant)
- Modify: `src/m4_eval.py` (bổ sung `metadata.evaluator_models` vào return dict)
- Test: `scripts/setup_answers.py --live`

**Interfaces:**
- Consumes: Môi trường python venv sẵn có từ Day 18 (`.venv`), tài liệu trong `data/`, câu hỏi trong `fixtures/test_set_50q.json`.
- Produces: `artifacts/answers_50q.json` chứa đúng 50 answers với đầy đủ `generation_mode` và `generation_model`.

- [ ] **Step 1: Cấu hình file `.env`**
  - Sao chép khóa `OPENAI_API_KEY` từ Day 18 sang `.env` ở thư mục gốc repo hiện tại.
- [ ] **Step 2: Cập nhật `src/m4_eval.py` trả về `metadata`**
  - Bổ sung cấu trúc `"metadata": {"evaluator_models": ["gpt-4o-mini", "BAAI/bge-m3"]}` vào dict trả về của `evaluate_ragas`.
- [ ] **Step 3: Cập nhật fallback an toàn cho `src/m2_search.py`**
  - Trong `DenseSearch.__init__`, bắt exception tổng quát (`Exception`) khi kết nối localhost:6333 để tự động dùng `QdrantClient(":memory:")` khi không có docker.
- [ ] **Step 4: Chạy `scripts/setup_answers.py --live`**
  - Chạy lệnh: `& "d:\Document\Ai_Thuc_Chien\4-10-2026\K4-Track3A-DAY18-DaoDuyHieu-2A202602651-ProductionRAG\.venv\Scripts\python.exe" scripts/setup_answers.py --live`
  - Đảm bảo sinh ra `artifacts/answers_50q.json` gồm 50 câu (20 factual, 20 multi-hop, 10 adversarial).
- [ ] **Step 5: Kiểm tra xác thực `answers_50q.json`**
  - Chạy hàm kiểm tra `validate_answers` để đảm bảo hợp đồng hợp lệ.

---

### Task 1: Phase A — RAGAS Production Evaluation (Tasks 1-4)

**Files:**
- Modify: `src/phase_a_ragas.py`
- Test: `tests/test_phase_a.py`

**Interfaces:**
- Consumes: `artifacts/answers_50q.json`, `src/m4_eval.py`
- Produces:
  - `group_by_distribution(test_set: list[dict]) -> dict[str, list[dict]]`
  - `run_ragas_50q(answers: list[dict]) -> RagasEvaluation`
  - `bottom_10(results: list[RagasResult]) -> list[dict]`
  - `cluster_analysis(results: list[RagasResult]) -> dict`

- [ ] **Step 1: Implement Task 1 `group_by_distribution`**
  - Phân loại 50 câu thành `{"factual": [...], "multi_hop": [...], "adversarial": [...]}`.
- [ ] **Step 2: Implement Task 2 `run_ragas_50q`**
  - Trích xuất dữ liệu, gọi `evaluate_ragas` từ `src.m4_eval`, ánh xạ vào danh sách `RagasResult`, trả về `RagasEvaluation(results, raw["metadata"]["evaluator_models"])`.
- [ ] **Step 3: Implement Task 3 `bottom_10`**
  - Sắp xếp tăng dần theo `avg_score`, lấy 10 câu đầu, ánh xạ `diagnosis` và `suggested_fix` từ `DIAGNOSTIC_TREE`.
- [ ] **Step 4: Implement Task 4 `cluster_analysis`**
  - Xây dựng ma trận 4x3 (worst_metric x distribution).
  - Tìm `dominant_failure_distribution` dựa trên trung bình `avg_score` thấp nhất (bỏ nhóm rỗng).
  - Tìm `dominant_failure_metric` dựa trên số lượng câu có worst_metric đó nhiều nhất.
  - Xóa toàn bộ comment `# TODO` trong file.
- [ ] **Step 5: Chạy unit tests offline cho Phase A**
  - Chạy: `pytest tests/test_phase_a.py -v`
  - Kỳ vọng: 6/6 tests PASS.

---

### Task 2: Phase B — LLM-as-Judge & Calibration (Tasks 5-8)

**Files:**
- Modify: `src/phase_b_judge.py`
- Test: `tests/test_phase_b.py`

**Interfaces:**
- Consumes: `artifacts/answers_50q.json`, `fixtures/human_labels_10q.json`, `fixtures/test_set_50q.json`
- Produces:
  - `pairwise_judge(question, answer_a, answer_b, reference="") -> dict`
  - `swap_and_average(question, answer_a, answer_b, reference="") -> JudgeResult`
  - `cohen_kappa(judge_labels, human_labels) -> float`
  - `bias_report(judge_results: list[JudgeResult]) -> dict`

- [ ] **Step 1: Implement Task 5 `pairwise_judge`**
  - Gọi OpenAI API (`gpt-4o-mini`) với `response_format={"type": "json_object"}`.
  - Đánh giá theo 3 tiêu chí: accuracy, completeness, conciseness với prompt chi tiết.
- [ ] **Step 2: Implement Task 6 `swap_and_average`**
  - Gọi lượt 1: `(q, A, B)`, lượt 2: `(q, B, A)`.
  - Quy đổi kết quả lượt 2 về không gian A/B ban đầu.
  - Xác định `final_winner` (đồng thuận thì lấy winner, bất đồng thì "tie"), `position_consistent`.
- [ ] **Step 3: Implement Task 7 `cohen_kappa`**
  - Dùng `sklearn.metrics.cohen_kappa_score` hoặc tính toán chuẩn xác theo công thức $κ = (p_o - p_e) / (1 - p_e)$.
- [ ] **Step 4: Implement Task 8 `bias_report`**
  - Đếm `position_bias_count`, `position_bias_rate`.
  - Tính `verbosity_bias` trên các ca có kết quả rõ ràng (`total_decisive`).
  - Xóa toàn bộ comment `# TODO` trong file.
- [ ] **Step 5: Chạy unit tests offline cho Phase B**
  - Chạy: `pytest tests/test_phase_b.py -v`
  - Kỳ vọng: 6/6 tests PASS.

---

### Task 3: Phase C — Guardrails Stack & Latency (Tasks 9a-12)

**Files:**
- Modify: `src/phase_c_guard.py`
- Test: `tests/test_phase_c.py`

**Interfaces:**
- Consumes: `fixtures/adversarial_set_20.json`, `fixtures/clean_set_8.json`, `fixtures/output_set_4.json`, `guardrails/`
- Produces:
  - `pii_scan(text, analyzer=None, anonymizer=None) -> dict`
  - `check_input_rail(text: str, rails=None) -> dict` (async)
  - `check_output_rail(question: str, answer: str, rails=None) -> dict` (async)
  - `run_adversarial_suite(adversarial_set, rails=None, ...) -> list[dict]`
  - `measure_p95_latency(test_inputs, n_runs=20, ...) -> dict`

- [ ] **Step 1: Implement Task 9a `pii_scan`**
  - Sử dụng Presidio Analyzer + Anonymizer phát hiện PII (CCCD, SĐT, Email).
- [ ] **Step 2: Implement Task 9b & 11 `check_input_rail` & `check_output_rail`**
  - `check_input_rail`: Gọi `rails.generate_async` với `options={"rails": ["input"], "log": {"activated_rails": True}}`.
  - `check_output_rail`: Kiểm tra context câu hỏi + câu trả lời, trả về `safe`, `flagged_reason`, `final_answer`.
- [ ] **Step 3: Implement Task 10 `run_adversarial_suite`**
  - Duyệt tuần tự qua 2 lớp: Presidio PII trước -> nếu an toàn thì mới gọi NeMo input rail.
  - So khớp `actual` với `expected` để xác định trường `passed`.
- [ ] **Step 4: Implement Task 12 `measure_p95_latency`**
  - Chạy 2 lần warm-up thực sự (loại khỏi kết quả đo).
  - Thu thập $N \ge 20$ mẫu tuần tự: Presidio -> NeMo input rail.
  - Gọi `summarize_latency` để tính toán percentiles tuyến tính và đánh giá budget.
  - Xóa toàn bộ comment `# TODO` trong file.
- [ ] **Step 5: Chạy unit tests offline cho Phase C**
  - Chạy: `pytest tests/test_phase_c.py -v`
  - Kỳ vọng: 12/12 tests PASS.

---

### Task 4: Chạy Thực Nghiệm Thật (Live Experiments) & Sinh Artifacts JSON

**Files:**
- Run: `scripts/run_experiments.py --phase a --live`
- Run: `scripts/run_experiments.py --phase b --live`
- Run: `scripts/run_experiments.py --phase c --live --latency-samples 20`
- Artifacts:
  - `artifacts/ragas_50q.json`
  - `artifacts/judge_results.json`
  - `artifacts/guard_results.json`

- [ ] **Step 1: Chạy Phase A live**
  - Chạy `python scripts/run_experiments.py --phase a --live`
  - Kiểm tra `artifacts/ragas_50q.json` được tạo thành công, có đủ metadata và 50 kết quả.
- [ ] **Step 2: Chạy Phase B live**
  - Chạy `python scripts/run_experiments.py --phase b --live`
  - Kiểm tra `artifacts/judge_results.json` được tạo thành công với 5 cặp swap-and-average và 10 binary judgments.
- [ ] **Step 3: Chạy Phase C live**
  - Chạy `python scripts/run_experiments.py --phase c --live --latency-samples 20`
  - Kiểm tra `artifacts/guard_results.json` đạt tối thiểu 15/20 attacks (mục tiêu >=18/20), 8/8 clean allowed, 4 output cases và >=20 latency samples.

---

### Task 5: Viết Báo Cáo Kỹ Thuật & Hoàn Thiện TEAM.md (Task 13)

**Files:**
- Modify: `doc/reports/failure_clusters.md`
- Modify: `doc/reports/bias_report.md`
- Modify: `doc/reports/blueprint.md`
- Modify: `doc/TEAM.md`

- [ ] **Step 1: Điền `failure_clusters.md`**
  - Lấy dữ liệu thật từ `artifacts/ragas_50q.json`.
  - Điền bảng điểm theo 3 distribution, 10 câu bottom rows kèm rank, id, avg_score, diagnosis, suggested fix.
  - Trình bày matrix và giải thích nguyên nhân, bẫy adversarial (xóa hết placeholder `{{...}}`).
- [ ] **Step 2: Điền `bias_report.md`**
  - Lấy dữ liệu thật từ `artifacts/judge_results.json`.
  - Điền 5 cặp pairwise, kết quả swap-and-average, position bias rate, verbosity bias.
  - Điền bảng calibration 10 câu nhị phân đối chiếu với human labels, giá trị Cohen's Kappa, nhận xét.
- [ ] **Step 3: Điền `blueprint.md`**
  - Trình bày kiến trúc bảo vệ nhiều tầng và failure actions.
  - Điền bảng số đo latency thực tế (P50, P95, P99) từ `guard_results.json`, các tầng ngoài phạm vi ghi rõ "chưa đo".
  - Đề xuất CI gates và monitoring cho production.
- [ ] **Step 4: Cập nhật `doc/TEAM.md`**
  - Điền thông tin thành viên nhóm, MSSV, phân công nhiệm vụ cụ thể, phần INDIVIDUAL chi tiết.

---

### Task 6: Kiểm Thử Toàn Diện & Chuẩn Bị Nộp Bài

**Files:**
- Test: `scripts/check_lab.py --with-tests`
- Verify git status & commit

- [ ] **Step 1: Chạy toàn bộ test offline**
  - Chạy `pytest tests/ -m "not integration" -q`
  - Đảm bảo 100% tests PASS (không còn lỗi nào trong số 24 student tests).
- [ ] **Step 2: Chạy bộ kiểm tra chuẩn của bài lab**
  - Chạy `python scripts/check_lab.py --with-tests`
  - Đảm bảo in ra `0 failed checks (not a rubric score)`.
- [ ] **Step 3: Kiểm tra git ignore và secrets**
  - Kiểm tra đảm bảo không có file `.env` bị commit, các artifact JSON trong `artifacts/` sẵn sàng commit.
