# Hiếu — CP0 và Phase A Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:executing-plans` and execute tasks in order. Keep each completed task and its verification result visible in the working notes. Do not start Dũng’s Phase B/C work from this plan.

**Goal:** Hoàn tất phần Hiếu từ kiểm tra/tích hợp pipeline RAG, tạo answers thật cho 50 câu, triển khai Phase A, viết failure analysis và bàn giao commit có thể tiếp tục được cho Dũng.

**Architecture:** CP0 ghép các module m1–m5 theo interface repo, sửa Qdrant fallback và đảm bảo m4 công bố đúng evaluator models. Phase A dùng answers đã validate, gọi m4 đúng một lần, tạo 50 kết quả RAGAS, bottom 10 và cluster analysis; runner có sẵn chịu trách nhiệm metadata, schema validation và lưu JSON.

**Tech Stack:** Python 3.11, RAGAS 0.1.22, Qdrant Client, Sentence-Transformers, OpenAI, pytest, JSON Schema Draft 2020-12.

**Spec:** [Phân công nhóm](2026-10-12-team-task-assignment.md), `doc/ASSIGNMENT.md`, `doc/CHECKPOINTS.md`, `doc/PIPELINE_INTERFACE.md`, `doc/REPORT_SCHEMAS.md`, `doc/RUBRIC.md`.

## Global Constraints

- Dùng Python 3.11 và môi trường đã được chuẩn bị trong repo; xác nhận interpreter thực tế trước khi chạy lệnh.
- Setup tự lắp m1/m2/m3/m5; không gọi `src/pipeline.py`.
- Answers phải giữ nguyên 50 IDs/question/distribution/ground_truth gốc; không dùng ground truth làm answer; contexts phải đến từ retrieval thật.
- Mỗi answer có `generation_mode` là `llm` hoặc `extractive_fallback`; `generation_model` là model ID với mode `llm`, và `null` với fallback.
- m4 trả `metadata.evaluator_models` gồm model IDs thực tế được dùng. Không để rỗng khi evaluation thành công; không dùng JUDGE_MODEL để đoán. Nếu evaluator chưa chạy, list rỗng; nếu lỗi xảy ra giữa lượt, không tuyên bố evaluation thành công và không lưu Phase A artifact.
- Nếu RAGAS bị skip/fail, không biến score 0 mặc định thành evidence thành công. Phase A live phải dừng thay vì lưu artifact giả.
- Phase A có đúng 50 rows, 4 metric hữu hạn trong [0,1], counts 20/20/10, bottom 10 và matrix worst_metric × distribution.
- `dominant_failure_distribution` chọn theo mean `avg_score` thấp nhất, bỏ nhóm rỗng; không chọn theo kích thước nhóm.
- Không đọc hoặc commit `.env`, API keys, virtualenv, cache model, `.vs/`, wheel/binary hoặc dữ liệu cá nhân thật.
- Lệnh `--live` có thể phát sinh API cost. Chỉ chạy ở bước live đã được người dùng cho phép; mỗi batch chạy một lần.
- Dùng một repo nhóm chung. Stage theo đường dẫn cụ thể; không push/nộp trừ khi được xác nhận là trưởng nhóm.

## Review Focus

1. **Qdrant từ chối kết nối với exception ngoài loại Qdrant cụ thể:** test client fallback in-memory khi constructor hoặc `get_collections()` báo lỗi kết nối.
2. **RAGAS model IDs đến từ default ngầm hoặc cấu hình khác ID được báo:** test m4 trả đúng IDs của các evaluator objects thực sự được dùng; successful evaluation không thể có metadata rỗng.
3. **Setup làm mất ID, metadata, thứ tự hoặc gọi nhầm `pipeline.py`:** chạy hai support tests hiện có `test_setup_preserves_metadata_and_does_not_call_pipeline_py` và `test_setup_generation_accepts_reused_client`.
4. **RAGAS thiếu/hỏng metric row hoặc trả NaN/out-of-range:** adapter không được ghép thiếu hàng bằng `zip` âm thầm; Phase A phải fail trước khi lưu artifact. Thêm test cho số row/metric không hợp lệ.
5. **Tie/nhóm trống làm thay đổi bottom 10 hoặc chọn nhóm sai:** test tie sorting ổn định; cluster analysis chỉ tính mean trên nhóm có dữ liệu và chọn quality thấp nhất.

---

## File map

- `src/m1_chunking.py`: load tài liệu và tạo parent/child chunks.
- `src/m2_search.py`: BM25/dense/hybrid retrieval; CP0 sửa fallback Qdrant.
- `src/m3_rerank.py`: reranking retrieved documents.
- `src/m4_eval.py`: RAGAS evaluator; CP0 bổ sung evaluator provenance và trạng thái rõ ràng.
- `src/m5_enrichment.py`: enrich chunks theo interface; fallback `[]` dùng chunks gốc.
- `scripts/setup_answers.py`: pipeline assembly và sinh answers; không sửa runner này trừ khi contract test chứng minh có lỗi.
- `src/phase_a_ragas.py`: Tasks 1–4; runner/exporter đã được cung cấp.
- `src/experiment_runners.py`, `src/report_contracts.py`: orchestration/schema checks đã cung cấp; chỉ sửa khi tìm được contract bug và ghi riêng lý do.
- `tests/test_hieu_pipeline.py`: tests mới cho Qdrant fallback và metadata m4.
- `tests/test_phase_a.py`: student tests Phase A hiện có; chỉ bổ sung regression tests cần thiết.
- `artifacts/answers_50q.json`, `artifacts/ragas_50q.json`: evidence tạo từ live runs.
- `doc/reports/failure_clusters.md`: báo cáo Phase A lấy số từ artifact thật.
- `doc/TEAM.md`: điền phần Hiếu sau khi công việc và commit evidence đã tồn tại.

## Task 1: Sửa Qdrant fallback của m2

**Files:**

- Modify: `src/m2_search.py`
- Create: `tests/test_hieu_pipeline.py`

**Interfaces:**

- Consumes: `DenseSearch.__init__()` và `QdrantClient` của dependency đang cài.
- Produces: `DenseSearch()` khởi tạo client Qdrant bình thường khi server hoạt động; nếu kết nối localhost thất bại với bất kỳ exception kết nối nào, dùng `QdrantClient(":memory:")` và khởi tạo `_encoder = None`.

- [ ] **Step 1: Viết test thất bại cho fallback**

Thêm `test_dense_search_falls_back_to_memory_on_connection_error` trong `tests/test_hieu_pipeline.py`. Fake `QdrantClient` để client network ném `RuntimeError` khi tạo hoặc `get_collections()`, sau đó assert constructor được gọi lại với `":memory:"` và object giữ memory client.

- [ ] **Step 2: Chạy riêng test mới để xác nhận đang thất bại**

Run: `python -m pytest tests/test_hieu_pipeline.py::test_dense_search_falls_back_to_memory_on_connection_error -q`
Expected: FAIL vì `DenseSearch` hiện chỉ bắt `ResponseHandlingException`.

- [ ] **Step 3: Sửa fallback trong `DenseSearch.__init__()`**

Giữ import dependency rõ ràng; đặt cả khởi tạo client network lẫn health check trong `try`; bắt exception kết nối tổng quát và tạo client in-memory. Không bắt lỗi import dependency như thể server offline.

- [ ] **Step 4: Chạy test fallback và Phase A support tests liên quan**

Run: `python -m pytest tests/test_hieu_pipeline.py::test_dense_search_falls_back_to_memory_on_connection_error -q`
Expected: PASS; memory client chỉ được dùng sau lỗi kết nối.

- [ ] **Step 5: Commit phần m2**

```powershell
git add src/m2_search.py tests/test_hieu_pipeline.py
git commit -m "fix(search): fall back to in-memory Qdrant"
```

## Task 2: Làm m4 công bố evaluator models thật

**Files:**

- Modify: `src/m4_eval.py`
- Modify: `tests/test_hieu_pipeline.py`

**Interfaces:**

- Consumes: `evaluate_ragas(questions, answers, contexts, ground_truths) -> dict` và RAGAS 0.1.22 objects.
- Produces: result dict giữ `per_question`/aggregate/status và `metadata: {"evaluator_models": [...]}`. IDs phải lấy từ cấu hình evaluator thực sự truyền vào lần `evaluate()`, gồm LLM/embedding được dùng; không lấy từ `JUDGE_MODEL`.

- [ ] **Step 1: Viết regression tests cho model provenance và status**

Thêm:

- `test_evaluate_ragas_reports_models_used_by_evaluator`: fake evaluator/embedding IDs riêng với model generation/judge; assert metadata chứa đúng IDs cấu hình và `evaluation_status == "evaluated"`.
- `test_evaluate_ragas_does_not_claim_success_when_skipped_or_failed`: khi API key thiếu hoặc RAGAS ném lỗi, assert status không phải `evaluated` và Phase A không thể hiểu kết quả đó là số đo thật. Metadata chỉ rỗng nếu evaluator chưa chạy; không giả báo model đã dùng.

Mock RAGAS boundary để tests offline không gọi API hoặc tải model.

- [ ] **Step 2: Chạy tests mới để xác nhận thiếu metadata/status**

Run: `python -m pytest tests/test_hieu_pipeline.py::test_evaluate_ragas_reports_models_used_by_evaluator tests/test_hieu_pipeline.py::test_evaluate_ragas_does_not_claim_success_when_skipped_or_failed -q`
Expected: FAIL do m4 hiện không trả `metadata.evaluator_models`.

- [ ] **Step 3: Cấu hình evaluator rõ ràng và trả metadata**

Kiểm tra API thực tế của RAGAS 0.1.22 đang cài. Cấu hình evaluator LLM/embedding bằng các model IDs đã định trong config (hiện lần lượt `GENERATION_MODEL` và `EMBEDDING_MODEL` nếu chính các object đó được truyền vào evaluation); trả lại IDs từ chính object/configuration được dùng trong lượt đó. Nếu API runtime resolve sang model khác, ghi resolved ID đó. Không gán tên mẫu chỉ để metadata đủ trường.

Các nhánh `skipped_empty_input`, `skipped_no_api_key` và `failed` phải giữ status tương ứng; metadata rỗng nếu không evaluator nào chạy, còn lỗi giữa lượt chạy phải giữ đúng IDs đã cấu hình/thực sự gọi. Không trả các số 0 như một evaluation thành công và không nuốt lỗi thành artifact thành công.

- [ ] **Step 4: Chạy tests m4 mới và setup support tests**

Run: `python -m pytest tests/test_hieu_pipeline.py -q`
Expected: tests metadata/fallback PASS mà không gọi mạng.

- [ ] **Step 5: Commit m4**

```powershell
git add src/m4_eval.py tests/test_hieu_pipeline.py
git commit -m "fix(eval): report actual RAGAS evaluator models"
```

## Task 3: Xác nhận m1–m5 khớp setup contract và tạo answers

**Files:**

- Review: `src/m1_chunking.py`–`src/m5_enrichment.py`, `doc/PIPELINE_INTERFACE.md`
- Run: `scripts/setup_answers.py`
- Produce: `artifacts/answers_50q.json`

**Interfaces:**

- Consumes: m1 `load_documents/chunk_hierarchical`; m5 `enrich_chunks`; m2 `HybridSearch.index/search`; m3 `CrossEncoderReranker.rerank`; fixtures và corpus.
- Produces: 50 JSON answer records đúng `doc/schemas/answers.schema.json` và `validate_answers`.

- [ ] **Step 1: So từng module với interface table**

Xác nhận import path, signatures, kiểu trả về, metadata retention, số lượng/thứ tự chunks, `.text/.score/.metadata`, fallback `[]` của m5 và top-3 rerank fallback. Sửa module từ bài trước chỉ khi thực sự lệch contract; không refactor ngoài phạm vi.

- [ ] **Step 2: Chạy tests scaffold xác nhận setup giữ metadata và không gọi pipeline.py**

Run: `python -m pytest tests/test_support.py::test_setup_preserves_metadata_and_does_not_call_pipeline_py tests/test_support.py::test_setup_generation_accepts_reused_client -q`
Expected: 2 tests PASS; chúng xác nhận orchestration setup, không chứng minh models/Qdrant đã chạy live.

- [ ] **Step 3: Xác nhận interpreter/runtime và cấu hình cục bộ**

Run từ repo root: `python --version`, `python -c "import sys; print(sys.executable)"`, `python -m pip check`. Xác nhận Python 3.11 và dependencies cần cho setup/RAGAS đã sẵn sàng. Kiểm tra `.env` chỉ bằng cách xác nhận có/không; không in hoặc đọc nội dung secret vào output.

- [ ] **Step 4: Chạy setup answers live đúng một lần**

Chỉ chạy sau khi được cho phép thực nghiệm live và đã xác nhận key/model/Qdrant/mô hình cục bộ sẵn sàng.
Run: `python scripts/setup_answers.py --live`
Expected: `artifacts/answers_50q.json` được tạo từ setup pipeline; mỗi record có answer, contexts, reference và generation provenance. Nếu có fallback, giữ nguyên và ghi nhận, không chạy lại chỉ để ép mode thành `llm`.

- [ ] **Step 5: Validate answers độc lập trước Phase A**

Run:

```powershell
python -c "from config import ANSWERS_PATH, TEST_SET_PATH; from src.experiment_support import read_json; from src.report_contracts import validate_answers; validate_answers(read_json(ANSWERS_PATH), read_json(TEST_SET_PATH)); print('answers valid')"
```

Expected: in `answers valid`; nếu fail, sửa nguyên nhân rồi mới chuyển Phase A.

- [ ] **Step 6: Commit pipeline và answers đã xác nhận**

Stage theo file cụ thể; không stage `.env`, `.vs/`, wheel hay virtualenv.

```powershell
git add src/m1_chunking.py src/m2_search.py src/m3_rerank.py src/m4_eval.py src/m5_enrichment.py artifacts/answers_50q.json
git commit -m "feat(rag): prepare validated answers for evaluation"
```

## Task 4: Implement Phase A Tasks 1–2

**Files:**

- Modify: `src/phase_a_ragas.py`
- Test: `tests/test_phase_a.py`
- Consumes: validated `answers_50q.json`, `src/m4_eval.py`
- Produces: `group_by_distribution(test_set) -> dict[str, list[dict]]` và `run_ragas_50q(answers) -> RagasEvaluation`.

- [ ] **Step 1: Bổ sung tests cho lỗi dữ liệu adapter**

Thêm `test_ragas_adapter_rejects_unusable_evaluation_payload` để `run_ragas_50q` raise `ValueError` khi m4 báo status skip/fail, metadata evaluator thiếu/rỗng, số per-question khác 50, hoặc metric không finite/trong [0,1]. Cập nhật mock trong `test_ragas_adapter_preserves_rows` để status là `evaluated`. Không để `zip()` lặng lẽ bỏ records.

- [ ] **Step 2: Chạy test mới để xác nhận đang thất bại**

Run: `python -m pytest tests/test_phase_a.py -m student -q`
Expected: FAIL trên các TODO và các case adapter mới.

- [ ] **Step 3: Implement `group_by_distribution(test_set)`**

Khởi tạo đúng ba keys theo thứ tự `factual`, `multi_hop`, `adversarial`; giữ thứ tự câu đầu vào trong từng group. Không làm mất hoặc tự sửa item.

- [ ] **Step 4: Implement `run_ragas_50q(answers)`**

Truyền bốn list cùng thứ tự vào `src.m4_eval.evaluate_ragas`; yêu cầu status `evaluated`, 50 result rows và metadata evaluator không rỗng. Map trực tiếp `id/distribution/question/answer/contexts/ground_truth` và bốn metrics vào `RagasResult`; chuyển numeric scalar bằng `float` và reject NaN/Inf/out-of-range. Trả `RagasEvaluation(results, evaluator_models)`.

- [ ] **Step 5: Chạy tests Phase A adapter và grouping**

Run: `python -m pytest tests/test_phase_a.py::test_group_exact_counts tests/test_phase_a.py::test_ragas_adapter_preserves_rows tests/test_phase_a.py::test_ragas_adapter_rejects_unusable_evaluation_payload -q`
Expected: các tests grouping/adapter PASS; IDs, rows, values và evaluator IDs được giữ; status/metadata/missing rows không hợp lệ bị từ chối. Chưa chạy bottom/cluster ở task này.

- [ ] **Step 6: Commit Tasks 1–2**

```powershell
git add src/phase_a_ragas.py tests/test_phase_a.py
git commit -m "feat(phase-a): group inputs and adapt RAGAS results"
```

## Task 5: Implement Phase A Tasks 3–4

**Files:** `src/phase_a_ragas.py`, `tests/test_phase_a.py`
**Consumes:** `RagasResult`, `DIAGNOSTIC_TREE`
**Produces:** `bottom_10(results) -> list[dict]`; `cluster_analysis(results) -> dict`.

- [ ] **Step 1: Bổ sung tests edge cases**

Thêm `test_bottom_ties_keep_input_order` và `test_cluster_empty_input_is_rejected`; xác nhận matrix column totals và nhóm mean thấp nhất bằng các test hiện có `test_cluster_matrix` và `test_weakest_distribution_is_quality_not_size`.

- [ ] **Step 2: Chạy Phase A tests để xác nhận TODO còn fail**

Run: `python -m pytest tests/test_phase_a.py -m student -q`
Expected: FAIL trên bottom/cluster TODO và edge cases.

- [ ] **Step 3: Implement `bottom_10(results)`**

Sort tăng dần `avg_score` ổn định; lấy tối đa 10 rows; gán rank từ 1; trả đủ `question_id`, `distribution`, `question`, `avg_score`, `worst_metric`, `diagnosis`, `suggested_fix`. Dùng đúng entry `DIAGNOSTIC_TREE[r.worst_metric]`; không để exporter tính đè. Với 50 inputs, trả đúng 10.

- [ ] **Step 4: Implement `cluster_analysis(results)`**

Tạo matrix đủ 4 metrics × 3 distributions; đếm mọi result theo `worst_metric`; tính `distribution_avg_scores` chỉ cho groups không rỗng; chọn distribution có mean thấp nhất; chọn metric có tổng count cao nhất; trả `insight` không rỗng và có cơ sở. Với empty input, raise `ValueError` rõ nghĩa thay vì chọn nhóm giả.

- [ ] **Step 5: Chạy toàn bộ Phase A student tests**

Run: `python -m pytest tests/test_phase_a.py -m student -q`
Expected: tất cả Phase A student tests PASS.

- [ ] **Step 6: Commit Tasks 3–4**

```powershell
git add src/phase_a_ragas.py tests/test_phase_a.py
git commit -m "feat(phase-a): add bottom questions and failure clusters"
```

## Task 6: Chạy Phase A live, viết failure report và bàn giao

**Files:**

- Run: `scripts/run_experiments.py --phase a --live`
- Produce: `artifacts/ragas_50q.json`, `doc/reports/failure_clusters.md`, phần Hiếu trong `doc/TEAM.md`

- [ ] **Step 1: Kiểm tra preconditions và diff trước live run**

Xác nhận answers đã validate, evaluator model IDs thực tế đã xác định, không còn `# TODO` trong `src/phase_a_ragas.py`, API permission đã rõ và artifact chưa chứa kết quả run trước cần giữ lại. Không in `.env` hoặc key.

- [ ] **Step 2: Chạy Phase A live một lần**

Run: `python scripts/run_experiments.py --phase a --live`
Expected: runner gọi `validate_answers`, yêu cầu evaluator metadata, validate Phase A Draft 2020-12 + hợp đồng số liệu rồi mới lưu `artifacts/ragas_50q.json`. Nếu RAGAS skipped/failed, dừng; không chấp nhận zero scores làm kết quả thật.

- [ ] **Step 3: Đối chiếu artifact và provenance**

Kiểm tra 50 `per_question`, đủ bốn metric hữu hạn trong [0,1], mỗi distribution 20/20/10, đúng 10 bottom rows từ Task 3, matrix khớp worst metrics, weakest group đúng mean thấp nhất, metadata version 2/run_kind live/source hashes và evaluator models khớp m4. Đọc vài câu bottom cùng answer/context/reference trước khi kết luận nguyên nhân.

- [ ] **Step 4: Điền `failure_clusters.md` bằng evidence thật**

Thay mọi placeholder trong `doc/reports/failure_clusters.md`: metadata/run time/model IDs/fallback, bảng metric theo distribution, 10 bottom rows, matrix, nhóm yếu nhất, metric trội, phân tích version/negation và cách cải thiện. Nêu rõ giới hạn nếu answers có extractive fallback. Không tự điền số; không dùng `?`, `{{...}}` hoặc placeholder `[...]`.

- [ ] **Step 5: Hoàn thiện phần Hiếu trong TEAM**

Điền tên/MSSV do nhóm xác nhận, files/functions thực làm, commits, lệnh/tests đã chạy, điều đã học, giới hạn và nguồn/AI hỗ trợ. Không ghi môi trường/model/runtime là đã xác minh nếu chưa có output.

- [ ] **Step 6: Rà final handoff và tạo commit Hiếu**

Run `git status --short`; stage riêng mã m1–m5, m2/m4 changes, Phase A, tests, `artifacts/answers_50q.json`, `artifacts/ragas_50q.json`, `doc/reports/failure_clusters.md`, `doc/TEAM.md` sau khi điền thật. Kiểm tra staged diff để loại `.env`, `.vs/`, wheel, virtualenv, cache và dữ liệu cá nhân. Commit message: `feat(hieu): complete CP0 and Phase A handoff`. Không push nếu chưa được xác nhận là trưởng nhóm.

## Handoff cho Dũng

Hiếu chỉ đánh dấu bàn giao khi repo có:

- Pipeline m1–m5 đúng `doc/PIPELINE_INTERFACE.md`.
- `artifacts/answers_50q.json` được `validate_answers` chấp nhận.
- `src/phase_a_ragas.py` hoàn thiện, Phase A student tests pass.
- `artifacts/ragas_50q.json` được runner tạo và validate từ live run.
- `doc/reports/failure_clusters.md` khớp artifact; phần Hiếu trong TEAM có bằng chứng.
- Commit SHA của phần Hiếu, danh sách file và ghi chú generation/evaluator model/fallback.

Dũng bắt đầu Phase B/C sau khi xác nhận nhận đủ các đầu ra trên. Nếu H1/Phase A bị trả lại do thiếu contract, sửa phần đó trước khi Dũng triển khai phần sau.
