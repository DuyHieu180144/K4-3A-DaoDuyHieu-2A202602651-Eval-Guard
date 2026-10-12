# Nhóm thực hiện K4 Track 3A

Tên nhóm: Chưa được cung cấp — nhóm bổ sung trước khi nộp

Repo chung: Chưa được cung cấp — nhóm bổ sung trước khi nộp

Trưởng nhóm/người nộp: Chưa được cung cấp — nhóm bổ sung trước khi nộp

Ngày lab/deadline áp dụng: Chưa xác nhận theo thông báo lớp — Asia/Ho_Chi_Minh (UTC+07:00)

Commit dùng để chấm: Sẽ điền SHA sau commit hoàn thiện handoff

Điền thông tin nhóm, deadline và người nộp theo xác nhận của nhóm/lớp trước khi nộp.

## Thành viên và phân công

| STT | Họ và tên | MSSV | Vai trò / công việc thật | Bằng chứng |
|---|---|---|---|---|
| 1 | Đào Duy Hiếu | 2A202602651 | CP0 + Phase A: OpenRouter config, m1–m5 integration, Qdrant/m4 fixes, Phase A evaluation và failure analysis | Commits `e03c593`, `14fc45d`, `bab7d56`; `artifacts/answers_50q.json`, `artifacts/ragas_50q.json`, `doc/reports/failure_clusters.md` |
| 2 | Dũng (tên đầy đủ cần bổ sung) | Chưa xác nhận | Phase B/C theo phân công nhóm; tiếp tục từ handoff OpenRouter/NeMo | Chưa bắt đầu trong phạm vi commit Hiếu; xem `doc/HIEU_HANDOFF.md` |

Người tích hợp/chạy batch: Đào Duy Hiếu — setup 50 answers và Phase A live; artifact được kiểm tra 50/50 rows.

## Môi trường và chuẩn bị trước lớp

- OS/Python: Windows, Python 3.11.9. Compiler: không dùng trong lần chạy này.
- Virtualenv/dependencies/imports: `.venv311`; `pip check` sạch; `pyarrow==19.0.1` tương thích `numpy==1.26.4`.
- Models: generation `google/gemini-3.1-flash-lite-preview` qua OpenRouter; evaluator models `BAAI/bge-m3` và Gemini; embeddings/reranker local.
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


### Dung-Chưa xác nhận

- MSSV: chưa được cung cấp; xác nhận trước khi nộp.
- Phần được giao: Phase B/C theo phân công nhóm; phần thực tế chưa bắt đầu trong các commit Hiếu.
- Bằng chứng/handoff: `doc/HIEU_HANDOFF.md` và commit Hiếu; Dũng bổ sung commit/artifact sau khi thực hiện.
- Cách kiểm tra, điều đã học, giới hạn và nguồn hỗ trợ: cập nhật sau khi hoàn thành phần được giao.
## Cập nhật sau khi nộp

Chưa push/nộp repo. Điền SHA commit cuối cùng và cập nhật mục này theo hướng dẫn trưởng nhóm/coach.