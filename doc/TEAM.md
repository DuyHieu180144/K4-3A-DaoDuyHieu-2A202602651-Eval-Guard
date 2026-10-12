# Nhóm thực hiện K4 Track 3A

Tên nhóm: Chưa được cung cấp — nhóm bổ sung trước khi nộp

Repo chung: Chưa được cung cấp — nhóm bổ sung trước khi nộp

Trưởng nhóm/người nộp: Chưa được cung cấp — nhóm bổ sung trước khi nộp

Ngày lab/deadline áp dụng: Chưa xác nhận theo thông báo lớp — Asia/Ho_Chi_Minh (UTC+07:00)

Commit bàn giao CP0 + Phase A: `ae9337e` (feat(hieu): complete CP0 and Phase A handoff)

Điền thông tin nhóm, deadline và người nộp theo xác nhận của nhóm/lớp trước khi nộp.

## Thành viên và phân công

| STT | Họ và tên | MSSV | Vai trò / công việc thật | Bằng chứng |
|---|---|---|---|---|
| 1 | Đào Duy Hiếu | 2A202602651 | CP0 + Phase A: OpenRouter config, m1–m5 integration, Qdrant/m4 fixes, Phase A evaluation và failure analysis | Commits `e03c593`, `14fc45d`, `bab7d56`; `artifacts/answers_50q.json`, `artifacts/ragas_50q.json`, `doc/reports/failure_clusters.md` |
| 2 | Nguyễn Việt Dũng | 2A202602533 | Phase B/C: LLM-as-a-Judge, calibration, Presidio PII, NeMo input/output guardrails, adversarial suite, latency benchmarking, reports | Commits `ce9b4bd`, `6cd1c06`; `artifacts/judge_results.json`, `artifacts/guard_results.json`, `doc/reports/bias_report.md`, `doc/reports/blueprint.md` |

Người tích hợp/chạy batch: Đào Duy Hiếu — setup 50 answers và Phase A live; artifact được kiểm tra 50/50 rows.

## Môi trường và chuẩn bị trước lớp

- OS/Python: Windows, Python 3.11.9. Compiler: không dùng trong lần chạy này.
- Virtualenv/dependencies/imports: `.venv311` / `.venv`; `pip check` sạch; `pyarrow==19.0.1` tương thích `numpy==1.26.4`.
- Models: generation `google/gemini-3.1-flash-lite-preview` qua OpenRouter; evaluator models `BAAI/bge-m3` và Gemini; embeddings/reranker local; guard model `openai/gpt-4o-mini`.
- Qdrant: Docker daemon/server local không sẵn sàng, nên pipeline dùng Qdrant in-memory.
- Answers/RAGAS: 50 answers đều ở mode `llm`; RAGAS có 50 rows, distribution 20/20/10. Artifact chi tiết ở `artifacts/`.
- Giới hạn corpus: BCTC và nghị định dữ liệu cá nhân là PDF scan không có text layer, bị bỏ qua; Hugging Face tải ở chế độ không đăng nhập.

## INDIVIDUAL

### DaoDuyHieu-2A202602651

- Phần được giao và phần thực tế đã làm: CP0 + Phase A; tích hợp m1–m5, OpenRouter; sửa Qdrant API cho client 1.9.x, evaluator provenance, NeMo chat provider; chạy 50 answers và RAGAS Phase A; viết failure report.
- Bằng chứng: commits `3a89f6f`, `df620b6`, `229a5d4`, `e03c593`, `14fc45d`, `bab7d56`; `artifacts/answers_50q.json`; `artifacts/ragas_50q.json`; `doc/reports/failure_clusters.md`.
- Cách kiểm tra: offline CP0 + Phase A + report contracts: 47 passed; `pip check` sạch; OpenRouter smoke call thành công; answers có 50/50 `llm`, RAGAS có 50 rows.
- Điều đã học: pin dependency tương thích; không dựa heuristic provider của NeMo cho model slug Gemini; gắn metric instances riêng để provenance đúng; kiểm tra retrieval coverage cho câu multi-hop.
- Giới hạn/cách xử lý: Qdrant dùng in-memory vì server local không chạy; hai PDF scan bị bỏ qua; failure report ghi rõ các giới hạn này.
- Nguồn/AI hỗ trợ: Codex hỗ trợ rà soát interface, viết regression tests, triển khai và phân tích artifact; các lệnh live, provenance, row counts và schema được kiểm chứng trong repo.


### NguyenVietDung-2A202602533

- MSSV: 2A202602533
- Phần được giao và phần thực tế đã làm: Toàn bộ Phase B và Phase C; triển khai LLM-as-a-Judge với kỹ thuật swap-and-average, tính Cohen's kappa và bias report; tích hợp Presidio PII scanner cho CCCD/CMND/SĐT/email VN; cấu hình NeMo Guardrails input và output rails qua OpenRouter; thực thi toàn bộ adversarial suite (20 attacks, 8 clean controls, 4 output cases); đo kiểm độ trễ tuần tự (20 mẫu timed sau 2 warm-up); soạn thảo `doc/reports/bias_report.md` và `doc/reports/blueprint.md`.
- Bằng chứng: commits `ce9b4bd`, `6cd1c06`; `artifacts/judge_results.json`; `artifacts/guard_results.json`; `doc/reports/bias_report.md`; `doc/reports/blueprint.md`.
- Cách kiểm tra: offline pytest 97/97 tests pass (100%); `scripts/check_lab.py --with-tests` PASS (0 failed checks); live artifacts: Phase B đạt κ = 1.0 và 0.0 position bias; Phase C đạt 20/20 attacks blocked, 8/8 clean inputs allowed (false positive rate = 0.0), 4/4 output cases đúng.
- Điều đã học: Presidio tiếng Anh over-detect tên riêng tiếng Việt thành PII, cần lọc thực thể chặt chẽ; NeMo input rails khi dùng OpenRouter với giới hạn max_tokens cần mô hình tương thích cao như gpt-4o-mini; swap-and-average loại bỏ hoàn toàn position bias; remote API latency là bottleneck lớn nhất của guardrails.
- Giới hạn/cách xử lý: Độ trễ P95 input guard đạt 2719.97 ms do roundtrip tới OpenRouter cloud API vượt ngân sách 500ms; đề xuất thay thế bằng local classifier (DeBERTa) khi lên production.
- Nguồn/AI hỗ trợ: Antigravity AI Pair Programmer hỗ trợ rà soát interface, tinh chỉnh Presidio/NeMo config, chạy thực nghiệm live và soạn thảo báo cáo kỹ thuật.
## Cập nhật sau khi nộp

Chưa push/nộp repo. Điền SHA commit cuối cùng và cập nhật mục này theo hướng dẫn trưởng nhóm/coach.