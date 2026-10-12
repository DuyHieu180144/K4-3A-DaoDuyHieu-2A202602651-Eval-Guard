# Bàn giao Hiếu → Dũng: CP0 và Phase A

Ngày cập nhật: 2026-10-12  
Trạng thái: code CP0/Phase A đã tích hợp và kiểm tra offline; live run đang chờ runtime nhận API key.

## Phạm vi Hiếu đã hoàn tất trong mã nguồn

- Hoàn thiện kết nối pipeline m1–m5, cấu hình OpenRouter và runner có xác nhận `--live`.
- Qdrant client 1.9.x dùng `search(query_vector=...)`; fallback Qdrant in-memory dùng được khi server local chưa chạy.
- m4 gắn evaluator vào metric instances riêng và lưu đúng trạng thái/model provenance.
- Phase A kiểm tra dữ liệu đầu vào, trả đúng 50 kết quả hợp lệ, bottom 10 ổn định, phân tích cụm lỗi theo điểm trung bình.
- NeMo setup khởi tạo `ChatOpenAI` trực tiếp bằng model, API base và key từ config để dùng OpenRouter chat; không dựa vào heuristic chọn provider theo model slug của NeMo 0.10.0.
- Regression tests mới ở `tests/test_hieu_pipeline.py`; contract tests Phase A ở `tests/test_phase_a.py`.

## Bằng chứng kiểm tra hiện có

- Python 3.11.9; `pip check` sạch.
- Offline suite CP0 + Phase A + report contracts: 46 passed.
- `py_compile` cho các module đã sửa và `git diff --check`: thành công.
- Docker daemon hiện không sẵn sàng; Qdrant in-memory fallback đã có regression coverage.
- Chưa sinh `artifacts/answers_50q.json` hoặc `artifacts/ragas_50q.json`; không dùng dữ liệu giả thay cho live run.

## Việc Hiếu cần hoàn tất khi runtime nạp được key

1. Đặt `OPENROUTER_API_KEY` trong `.env` ở repo root (hoặc dùng tên tương thích `OPENAI_API_KEY`). Không gửi key qua chat, không thêm `.env` vào Git.
2. Từ repo root, dùng đúng interpreter đã chuẩn bị:

   ```powershell
   .\.venv311\Scripts\python.exe scripts\setup_answers.py --live
   .\.venv311\Scripts\python.exe scripts\run_experiments.py --phase a --live
   ```

3. Chỉ tiếp tục nếu answers có đủ 50 IDs theo test set, `generation_mode`/contexts đúng nguồn, và RAGAS có `evaluation_status: evaluated`, 50 rows cùng evaluator model metadata.
4. Dựa trên `artifacts/ragas_50q.json` để hoàn thiện `doc/reports/failure_clusters.md`; cập nhật kết quả thực tế và giới hạn vào `doc/TEAM.md`.

Runtime kiểm tra gần nhất tìm thấy `.env` nhưng config không nhận được giá trị cho cả `OPENROUTER_API_KEY` lẫn legacy `OPENAI_API_KEY`. Không có giá trị bí mật nào được đọc ra màn hình. Khi người dùng xác nhận runtime đã nhận key, chạy lại hai lệnh trên.

## Điểm nối cho Dũng

Dũng có thể bắt đầu Phase B/C trên cùng nhánh sau các commit CP0/Phase A. Dùng `config.create_llm_client()` cho judge và `src.phase_c_guard.setup_nemo_rails()` cho NeMo; hàm setup đã inject chat model OpenRouter tường minh. Trước Phase C live run, chạy smoke test một input sạch và một input bị chặn để xác nhận rails thực sự gọi chat API. Không dùng Phase A score `0` hoặc test mock làm kết quả đánh giá.

Các kết quả API/live thuộc phần Hiếu vẫn là điều kiện cần trước khi coi bàn giao Phase A đã hoàn tất. Không push hoặc nộp repo khi chưa được trưởng nhóm cho phép.
