# Bàn giao Hiếu → Dũng: CP0 và Phase A

Ngày cập nhật: 2026-10-12
Trạng thái: CP0 + Phase A live đã chạy; artifact và failure report đã được tạo, kiểm tra.

## Phạm vi Hiếu đã hoàn tất

- Hoàn thiện kết nối pipeline m1–m5, cấu hình OpenRouter và runner có xác nhận `--live`.
- Qdrant client 1.9.x dùng `search(query_vector=...)`; fallback Qdrant in-memory hoạt động khi server local chưa chạy.
- m4 gắn evaluator vào metric instances riêng và lưu đúng model provenance.
- Phase A kiểm tra đầu vào, trả đúng 50 kết quả, bottom 10 ổn định và failure matrix theo điểm.
- NeMo setup inject `ChatOpenAI` với model/API base/key từ config để dùng OpenRouter chat trên NeMo 0.10.0.
- Regression tests ở `tests/test_hieu_pipeline.py`; Phase A contract tests ở `tests/test_phase_a.py`.

## Bằng chứng và artifact

- Python 3.11.9; `pip check` sạch; bộ test CP0 + Phase A + report contracts: 47 passed.
- `artifacts/answers_50q.json`: 50/50 câu dùng generation mode `llm`; IDs, question, distribution, ground truth khớp fixture; contexts không rỗng.
- `artifacts/ragas_50q.json`: 50/50 rows, `run_kind: live`, distribution 20/20/10, evaluator model provenance và failure matrix.
- `doc/reports/failure_clusters.md`: scores, bottom 10, đối chiếu answer/context/ground truth và giới hạn thực nghiệm.
- OpenRouter smoke call thành công với `google/gemini-3.1-flash-lite-preview`.
- PyArrow đã pin ở 19.0.1 để tương thích NumPy 1.26.4; `pip check` sạch.

## Kết quả Phase A

`multi_hop` có mean thấp nhất (0.6513); `answer_relevancy` là worst metric thường gặp nhất (21/50). Báo cáo đề xuất sửa retrieval/chunking theo bảng và đảm bảo đủ context cho từng vế multi-hop.

## Giới hạn cần bàn giao

Qdrant local không kết nối được nên lần chạy này dùng in-memory. Hai PDF scan không có text layer (`BCTC.pdf` và nghị định dữ liệu cá nhân) bị bỏ qua. Hugging Face tải model không đăng nhập; embeddings/reranker chạy local. RAGAS là evaluator tự động, chưa thay review thủ công cho các ca tính toán/version.

## Điểm nối cho Dũng

Dũng có thể tiếp tục Phase B/C trên cùng nhánh. Dùng `config.create_llm_client()` cho judge và `src.phase_c_guard.setup_nemo_rails()` cho NeMo; hàm setup đã inject chat model OpenRouter tường minh. Trước Phase C live run, smoke test một input sạch và một input bị chặn để xác nhận rails thật sự gọi chat API.

Chưa push hoặc nộp repo. Các trường tên nhóm, repo URL, người nộp và MSSV cần xác nhận/điền trong `doc/TEAM.md` trước khi nộp.