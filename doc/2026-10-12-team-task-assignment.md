# Phân công và hướng dẫn thực hiện K4 Track 3A

**Nhóm:** Hiếu và Dũng  
**Repo dùng chung:** `K4-3A-DaoDuyHieu-2A202602651-Eval-Guard`  
**Plan triển khai:** [2026-10-12-production-eval-guard-lab.md](2026-10-12-production-eval-guard-lab.md)  
**Hợp đồng bài lab:** `README.md`, `doc/ASSIGNMENT.md`, `doc/CHECKPOINTS.md`, `doc/RUBRIC.md`, `doc/RULES.md`, `doc/REPORT_SCHEMAS.md`, `doc/SUBMISSION.md`

> Phân công dưới đây đã được Hiếu duyệt. Tên đầy đủ, MSSV, tên nhóm và trưởng nhóm/người nộp chưa có trong repo; điền thông tin thật vào `doc/TEAM.md`, không tự suy đoán.

## 1. Mục tiêu và tiêu chí hoàn thành

Hoàn tất bài lab trên **một repo nhóm chung**, gồm pipeline RAG m1–m5, code Phase A/B/C, bốn JSON artifacts từ thực nghiệm thật, ba báo cáo kỹ thuật, `doc/TEAM.md` đầy đủ và bằng chứng Git của cả hai thành viên.

Bài sẵn sàng nộp khi:

- Có 50 answers theo đúng bộ câu hỏi gốc: 20 factual, 20 multi-hop, 10 adversarial; question/reference còn nguyên, contexts là kết quả retrieval thật, generation metadata đúng.
- Phase A có đủ 50 kết quả với bốn metric hữu hạn trong [0,1], 10 bottom rows do hàm của nhóm tạo, matrix và phân tích đúng hợp đồng.
- Phase B có 5 cặp A/B theo nguồn quy định, 10 binary judgments trên `model_answer` gốc, Cohen’s κ và bias report.
- Phase C có 20 attacks, 8 clean controls, 4 output cases, ít nhất 20 mẫu latency sau hai warm-up. Ngưỡng bắt buộc: ít nhất 15/20 attacks đạt và 8/8 clean inputs allowed. Bonus: 18/20 attacks trở lên, vẫn đạt clean controls.
- `python scripts/check_lab.py` thành công; TEAM/báo cáo không còn placeholder; artifacts phản ánh lượt chạy thật; không có `.env`, API key, virtualenv, cache hoặc dữ liệu cá nhân thật trong commit.

## 2. Phân công tổng quan

| Người | Sở hữu | Kết quả chính |
|---|---|---|
| **Hiếu** | Chặng đầu: pipeline/CP0 và trọn Phase A | m1–m5, `answers_50q.json`, Phase A, `ragas_50q.json`, `failure_clusters.md`; bàn giao dữ liệu và trạng thái đã kiểm tra |
| **Dũng** | Sau khi nhận bàn giao: trọn Phase B và Phase C | Phase B, toàn bộ guardrails/latency, `judge_results.json`, `guard_results.json`, `bias_report.md` |
| **Cùng làm** | Rà blueprint, TEAM và bản nộp cuối | `blueprint.md`, TEAM trung thực, checker pass, repo chung sẵn sàng nộp |

Thứ tự làm việc là tuần tự, không chia owner so le giữa các phase: Hiếu hoàn tất chặng đầu và bàn giao; Dũng bắt đầu phần của mình sau khi CP0/Phase A đã được xác nhận. Dũng sở hữu toàn bộ Phase B/C, kể cả Presidio và adversarial suite. Hai người chỉ cùng rà blueprint, TEAM và bản nộp cuối. TEAM chỉ được ghi việc thực sự hoàn tất và có bằng chứng.

## 3. Hiếu — việc cần làm

### H1. CP0: pipeline RAG và answers

**File:** `src/m1_chunking.py`, `src/m2_search.py`, `src/m3_rerank.py`, `src/m4_eval.py`, `src/m5_enrichment.py`, `artifacts/answers_50q.json`.

1. Đưa đủ năm module m1–m5 từ bài trước vào repo, giữ interface theo `doc/PIPELINE_INTERFACE.md`.
2. Sửa `m2_search.py`: nếu kết nối Qdrant thất bại, fallback sang client in-memory mà không làm setup crash.
3. Sửa `m4_eval.evaluate_ragas(...)` để trả `metadata.evaluator_models` với model IDs thật đã dùng. Không để list rỗng, không lấy model judge thay thế, không hardcode ví dụ nếu cấu hình thực tế khác.
4. Dùng Python interpreter của môi trường đã cài; xác nhận bằng `python --version` và `python -c "import sys; print(sys.executable)"`. Repo hiện có `.venv311`; nếu cần, gọi trực tiếp `.venv311/Scripts/python.exe` từ repo root. Không dùng đường dẫn tuyệt đối Day 18 trong plan cũ.
5. Sau khi pipeline/key/runtime sẵn sàng, chạy từ gốc repo `python scripts/setup_answers.py --live` để tạo `artifacts/answers_50q.json`. Không đưa key vào command, log, report hoặc commit.
6. Kiểm tra đủ ID gốc, distribution 20/20/10, question/reference nguyên trạng, contexts do pipeline lấy thật; `generation_mode` là `llm` hoặc `extractive_fallback`, và `generation_model` phù hợp chế độ.

**Bàn giao:** answers đúng schema/hợp đồng; ghi rõ provenance model và fallback để các phase sau dùng đúng.

### H2. Phase A: RAGAS

**File:** `src/phase_a_ragas.py`, `tests/test_phase_a.py`, `artifacts/ragas_50q.json`, `doc/reports/failure_clusters.md`.

Implement bốn hàm:

- `group_by_distribution(test_set)`: đúng ba keys `factual`, `multi_hop`, `adversarial`, số lượng 20/20/10.
- `run_ragas_50q(answers)`: gọi adapter m4, ánh xạ đủ 50 `RagasResult`, lấy `raw["metadata"]["evaluator_models"]` vào `RagasEvaluation`.
- `bottom_10(results)`: sắp xếp tăng dần `avg_score`; đủ rank/id/question/distribution/worst_metric/diagnosis/suggested_fix. Diagnosis và fix lấy từ diagnostic tree, exporter phải giữ nguyên.
- `cluster_analysis(results)`: matrix worst_metric × distribution đếm mọi câu; nhóm yếu nhất theo mean `avg_score` thấp nhất, bỏ nhóm rỗng; metric trội theo số lần xuất hiện.

> Chạy tests offline Phase A sau khi implement. Khi code sẵn sàng và live run được cho phép, chạy `python scripts/run_experiments.py --phase a --live` một lần. Viết `failure_clusters.md` từ JSON: số liệu từng distribution, đúng 10 bottom rows, matrix, đối chiếu câu hỏi/answer/context/reference và giới hạn. Không khẳng định nguyên nhân nếu dữ liệu chỉ cho thấy tương quan.

### H3. Báo cáo và bàn giao

- Viết `doc/reports/failure_clusters.md` từ `artifacts/ragas_50q.json`.
- Xác nhận answers và Phase A artifact đã được tạo/kiểm tra; ghi lại lệnh, model metadata, fallback và giới hạn để Dũng tiếp tục mà không phải chạy lại setup/Phase A.
- Điền mục Hiếu trong `doc/TEAM.md`: công việc thực tế, commit, cách kiểm tra, điều đã học, giới hạn, khai báo nguồn/AI nếu có.
- Tạo commit bàn giao gọn, liệt kê các file đã đổi và kết quả kiểm tra. Sau điểm bàn giao, Dũng tiếp tục Phase B/C; Hiếu hỗ trợ giải thích pipeline nếu cần nhưng không nhận thêm phần triển khai phase sau.

## 4. Dũng — việc cần làm

### D1. Phase B: pairwise judge và calibration

**File:** `src/phase_b_judge.py`, `tests/test_phase_b.py`, `artifacts/judge_results.json`, `doc/reports/bias_report.md`.

Implement bốn hàm:

- `pairwise_judge(question, answer_a, answer_b, reference="")`: gọi judge theo JSON contract; đánh giá accuracy/completeness/conciseness; trả winner A/B/tie, reasoning và scores hợp lệ.
- `swap_and_average(...)`: gọi cả A/B và B/A với cùng question/reference; quy đổi lượt hai về A/B ban đầu; tính consensus/tie và position consistency.
- `cohen_kappa(judge_labels, human_labels)`: tính κ đúng thứ tự 10 nhãn, xử lý edge cases tương thích sklearn.
- `bias_report(judge_results)`: position inconsistency count/rate và verbosity win rate trên case decisive, đủ chi tiết đối chiếu từng cặp.

Nguồn bắt buộc:

- Pairwise IDs: `1, 5, 12, 21, 41`. A từ `answers_50q.json:answer`; B từ `human_labels_10q.json:model_answer`; reference từ `test_set_50q.json:ground_truth`.
- Binary calibration dùng đúng 10 `model_answer` trong `human_labels_10q.json`, theo thứ tự fixture. Không thay bằng answer pipeline.
- Không gửi `human_label`, `human_note` hoặc phân bố nhãn người vào prompt. Chỉ so nhãn human sau khi judge hoàn tất.
- Winner A/B không đồng nghĩa nhãn tốt/xấu 0/1.

**Bàn giao:** tests offline Phase B đạt; khi live run được phép, chạy `python scripts/run_experiments.py --phase b --live` một lần; JSON có 5 cặp/10 lượt và 10 binary judgments; viết `bias_report.md` từ số liệu thật, nêu giới hạn và không coi judge là chân lý.

### D2. Phase C: toàn bộ guardrails và latency

**File:** toàn bộ `src/phase_c_guard.py`, `guardrails/config.yml`, `guardrails/rails.co`, `tests/test_phase_c.py`, fixtures và `artifacts/guard_results.json`.

- Implement `pii_scan(text, analyzer=None, anonymizer=None)` bằng Presidio; xử lý CCCD 12 số, CMND 9 số, điện thoại VN và email; trả entities/vị trí/redacted text theo contract.
- `check_input_rail(text, rails=None)` async: chỉ chạy input rail; đọc response và activated rails theo NeMo 0.10.0/API đang dùng; trả allowed/blocked_reason/response theo contract. Không suy ra block chỉ từ từ ngữ refusal như “xin lỗi” hay “không thể”.
- `check_output_rail(question, answer, rails=None)` async: kiểm tra answer đã có; giữ nguyên output an toàn; thay/redact output nhạy cảm; trả `safe`, `flagged_reason`, `final_answer`.
- Implement `run_adversarial_suite(...)`: giữ nguyên inputs; chạy PII trước rồi input rail theo contract; `expected` chỉ dùng tính `passed`, không quyết định `actual`. Đủ 20 attacks và 8 clean controls; không sửa fixtures để làm đẹp số liệu. Chỉ dùng dữ liệu giả.
- `measure_p95_latency(test_inputs, n_runs=20, ...)` với `n_runs` ít nhất 20: tạo engines trước đo; chạy hai warm-up thật trong cùng event loop và loại chúng khỏi samples; đo tuần tự Presidio rồi NeMo input; thu durations dương; mỗi tổng sample bằng tổng hai lớp; percentile linear từ samples. Không short-circuit lượt đo.
- Ghi `scope=input_layers_sequential`; không gọi đây là end-to-end/full guard/RAG/output latency. Ghi số thật nếu vượt budget 500ms.
- Xác nhận 8 clean inputs allowed và 4 output cases đúng; xử lý false positive bằng sửa rail/code, không đổi tiêu chí.

**Bàn giao:** tests offline Phase C đạt; khi live run được phép, chạy `python scripts/run_experiments.py --phase c --live --latency-samples 20` một lần; artifact đủ attacks/clean/output/latency; báo cáo nêu đúng scope.

### D3. Báo cáo và hồ sơ đóng góp

- Viết `doc/reports/bias_report.md` từ `artifacts/judge_results.json`, giải thích nguồn candidate, hai lượt, calibration, κ, bias và giới hạn mẫu.
- Cùng Hiếu viết `doc/reports/blueprint.md`; Dũng xác nhận latency, guard models, attack/clean/output và giới hạn phép đo.
- Điền mục Dũng trong `doc/TEAM.md` bằng tên/MSSV thật, commits, cách kiểm tra, điều đã học, giới hạn và khai báo nguồn/AI nếu có.

## 5. Thứ tự và điểm phụ thuộc

1. **Chặng Hiếu:** hoàn thành H1, tạo/kiểm tra answers, hoàn thành H2, chạy Phase A khi live run được phép, viết failure clusters và commit bàn giao. Không chuyển việc Phase B/C sang Hiếu.
2. **Bàn giao:** Dũng xác nhận đã nhận code, answers, Phase A artifact và ghi chú model/fallback. Nếu thiếu dữ liệu hoặc checker Phase A phát hiện lỗi, trả lại đúng phần để Hiếu sửa trước khi bắt đầu Phase B/C.
3. **Chặng Dũng:** sau bàn giao, hoàn thành D1 rồi D2; chạy tests offline; chạy live B/C khi được phép; tạo hai artifacts và viết bias report.
4. **Tổng hợp:** Dũng soạn blueprint từ artifacts; Hiếu rà phần pipeline/Phase A, Dũng rà Phase B/C. Cùng cập nhật TEAM và chạy `python scripts/check_lab.py` sau khi đủ mọi đầu ra.
5. Rà Git/secrets. Trưởng nhóm được ghi trong TEAM xác nhận commit cuối trên GitHub và nộp repo chung.

Khi lỗi xảy ra, lưu thông tin lỗi không chứa secret, xác định nguyên nhân rồi mới tiếp tục. Không tự tạo JSON thay kết quả live, không chạy lại chỉ để đổi timestamp, không xóa bằng chứng lỗi cần nêu trong giới hạn.

## 6. Hướng dẫn bắt buộc cho AI

AI đọc file này và các hợp đồng đầu file trước khi sửa. Phải tuân thủ:

1. **Kiểm tra trạng thái thật trước khi hành động:** đọc Git status, files, interpreter và artifacts. Plan cũ có đường dẫn Day 18 trên máy khác; không dùng đường dẫn tuyệt đối đó. Chạy từ repo root với Python môi trường hiện hành.
2. **Ưu tiên hợp đồng bài lab:** nếu plan này khác `doc/ASSIGNMENT.md`, schema, tests, checker hoặc README, đối chiếu tài liệu chính thức và ghi nhận/sửa xung đột trước khi code. Không thay schema để làm test dễ pass.
3. **Tôn trọng owner và thứ tự bàn giao:** Hiếu sở hữu H1–H3; Dũng chỉ bắt đầu D1–D3 sau khi nhận bàn giao CP0/Phase A. Dũng sở hữu toàn bộ Phase C. Không làm song song hai chặng, không ghi đè thay đổi chưa commit; nếu phải sửa phần người kia, nêu lý do và trả lại để owner rà.
4. **Không làm giả bằng chứng:** không bịa answers, model IDs, labels, latency, timestamps, test results hoặc report metrics. Chỉ báo kết quả đã quan sát từ artifacts và lệnh thực sự chạy.
5. **Bảo vệ dữ liệu:** không đọc/in ra/commit `.env`, keys, tokens; không commit virtualenv, cache, `.vs/`, wheel/binary hoặc dữ liệu cá nhân thật. Chỉ dùng fixture. Nếu secret bị stage, bỏ khỏi staging và báo owner.
6. **Giữ provenance/prompt an toàn:** không trộn model roles generation/evaluator/judge/guard; không gửi human labels/notes vào judge; không để expected điều khiển actual.
7. **Live run cần được cho phép rõ:** các lệnh live có thể phát sinh chi phí. Chỉ chạy khi yêu cầu hiện tại cho phép thực nghiệm live; không chạy lại phase đã có artifact hợp lệ. Nếu chưa được cho phép, hoàn thiện việc offline và nêu lệnh cần chạy tiếp.
8. **Kiểm chứng trước khi tuyên bố xong:** chạy tests offline liên quan sau khi sửa code; chạy checker khi đủ artifacts/reports. Nêu đúng lệnh/kết quả; không nói pass nếu chưa chạy. Không lặp integration/API chỉ để kiểm tra lại artifacts đã có.
9. **Không tự push/nộp:** AI có thể chuẩn bị thay đổi cục bộ; chỉ trưởng nhóm được xác nhận mới push/nộp. Không force push, không tạo repo riêng cho từng người.
10. **TEAM phải trung thực:** AI có thể soạn nháp, nhưng mỗi người xác nhận tên/MSSV, phần thực làm, bằng chứng, điều học được và khai báo nguồn/AI. Không tự điền nhận dạng.

## 7. Git: commit gì, ai push

### Nên commit vào repo chung

- Commit bàn giao của Hiếu: `src/m1_chunking.py`–`src/m5_enrichment.py`, adapter cần thiết, Phase A, `answers_50q.json`, `ragas_50q.json`, `failure_clusters.md`.
- Commit của Dũng sau bàn giao: Phase B/C, guardrail config, tests cần thiết, `judge_results.json`, `guard_results.json`, `bias_report.md`, `blueprint.md`.
- `doc/TEAM.md` sau khi cả hai xác nhận; file phân công này nếu nhóm muốn lưu hướng dẫn trong repo.
- Tất cả bốn artifacts live và ba báo cáo sau khi rà schema, provenance, nội dung và secrets.
- Mỗi thành viên có commit thể hiện phần đã làm. Ví dụ: `feat(phase-a): implement RAGAS aggregation`, `feat(phase-b): add swap-and-average judge`.

### Tuyệt đối không commit

- `.env`, API key/token, log chứa credentials.
- `.venv`, `.venv311`, `venv`, `.pytest_cache`, `__pycache__`, model caches.
- `.vs/`, `nemoguardrails-*.whl`, installer/binary cài môi trường.
- Mock data trình bày như live results, artifacts tự bịa hoặc PII thật.

Trước commit, đọc `git status --short`, staged diff và rà file nhạy cảm. Stage theo đường dẫn cụ thể; tránh `git add .` khi workspace còn `.vs/`, wheel hoặc môi trường. Artifacts JSON là bằng chứng phải commit; `.gitignore` hiện nêu rõ điều này.

Hai người dùng **một repo chung** và commit/push phần mình theo phối hợp của nhóm; không sửa cùng file đồng thời, không force push. Trưởng nhóm được ghi trong `doc/TEAM.md` kiểm tra commit cuối trên GitHub rồi nộp một link. Chưa có xác nhận ai là trưởng nhóm nên không mặc định Hiếu là người nộp chỉ vì tên repo.

## 8. Checklist bàn giao

### Hiếu

- [ ] Đủ năm module RAG đúng interface; Qdrant fallback và evaluator metadata đúng thực tế.
- [ ] Answers 50 câu được tạo/validate, không kèm secret.
- [ ] Phase A code, tests, live artifact và `failure_clusters.md` hoàn tất.
- [ ] Bàn giao cho Dũng answers, Phase A artifact, model/fallback metadata và commit evidence.
- [ ] Mục INDIVIDUAL của Hiếu có việc thật và commit evidence.

### Dũng

- [ ] Nhận bàn giao CP0/Phase A trước khi bắt đầu phần triển khai của Dũng.
- [ ] Phase B code, tests, live artifact và `bias_report.md` đúng nguồn.
- [ ] Toàn bộ Phase C: PII, input/output rails, adversarial/clean suite và latency.
- [ ] Latency có hai warm-up thật, ít nhất 20 mẫu, đúng scope và percentile.
- [ ] Phase C có đủ 20 attacks, 8 clean controls, 4 output cases và latency hợp lệ.
- [ ] Mục INDIVIDUAL của Dũng có việc thật và commit evidence.

### Cùng rà trước khi nộp

- [ ] Có đủ bốn JSON live và `python scripts/check_lab.py` thành công.
- [ ] Ba reports không còn placeholder, số liệu khớp JSON, nêu giới hạn thật.
- [ ] TEAM có hai thành viên, MSSV, phân công, bằng chứng, môi trường và hai mục INDIVIDUAL.
- [ ] Không commit `.env`, secret, `.vs/`, virtualenv, cache hoặc wheel.
- [ ] Trưởng nhóm xác nhận commit cuối trên GitHub, lưu SHA vào TEAM và nộp một link.
