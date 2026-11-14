# Day 06 · Data Ingestion Engineering

**Lab cá nhân** · **Học viên:** Ngô Chí Vĩnh (`2A202603724`) · **Lớp:** `L3B`

Biến tài liệu thành kho tri thức có thể truy xuất cho AI agent, rồi đo xem cách chuẩn bị dữ liệu nào hiệu quả nhất.

| 📄 Dữ liệu | 🧩 Chiến lược | 🎯 Benchmark |
|---|---|---|
| **47 trang nội dung hợp lệ** (từ 64 trang PDF gốc) | **3 cấu hình (`A`, `B`, `C`)** trên Qdrant + `gemini-embedding-001` (`3072d`) | **20 câu hỏi** (`15 dev` / `5 test`, gồm `6` câu lọc metadata) |

---

## Hướng dẫn Cài đặt, Chạy lại Thực nghiệm và Cấu trúc Bài nộp

### 1. Yêu cầu môi trường và Cài đặt thư viện
Dự án sử dụng **Python 3.11+**, mô hình nhúng thật **Google Gemini (`gemini-embedding-001`, 3072 chiều)** qua `google-genai` và cơ sở dữ liệu vector lưu trữ bền vững trên đĩa **Qdrant Local Persistent Store (`qdrant-client`)** (ngoài ra `starter/src/store.py` cũng hỗ trợ `PostgreSQL + pgvector`).

```powershell
cd starter
pip install -r requirements.txt
```

### 2. Cấu hình biến môi trường (`starter/.env`)
Tạo file `starter/.env` từ `starter/.env.example` và điền `GEMINI_API_KEY` (file `.env` đã được đưa vào `.gitignore`, tuyệt đối không commit khóa bí mật):

```env
GEMINI_API_KEY=<YOUR_GEMINI_API_KEY>
EMBEDDING_MODEL=gemini-embedding-001
```

Code chỉ đọc các biến trên (cùng `OPENAI_API_KEY` / `OPENROUTER_API_KEY` nếu dùng provider khác). Provider được chọn tự động theo key có trong `.env` (ưu tiên Gemini); số chiều (`3072`) được đo từ vector thật trả về; vector store luôn là Qdrant local tại `starter/qdrant_storage` (khai báo trong `starter/src/run.py`).

> **Lưu ý tái lập:** cache embedding (`results/embedding_cache.json`, ~23 MB) và dữ liệu Qdrant (`starter/qdrant_storage/`) không được commit, nên cần `GEMINI_API_KEY` riêng để chạy lại. Lần chạy đầu trên Free Tier mất ~7 phút do giới hạn 100 items/phút.

### 3. Lệnh chạy toàn bộ Pipeline và Đánh giá Benchmark (`A / B / C`)
Từ thư mục `starter/`, chạy lệnh duy nhất sau:

```powershell
cd starter
python -m src.run
```

Lệnh này thực hiện tự động từ đầu đến cuối:
1. Đọc tài liệu PDF tại `starter/data/wb_diem_lai_2024_08.pdf`, lọc bỏ 17 trang không phải nội dung (bìa, trang trắng, bản quyền, mục lục, viết tắt, lời cảm ơn, trang ngăn cách chương), chuẩn hóa Unicode NFC trên **47 trang nội dung hợp lệ** (`141,104` ký tự) và xuất nhật ký `results/ingestion_log.json`.
2. Chia chunk theo 3 chiến lược **A (`fixed_size` 500/50)**, **B (`by_paragraph` $\le 1000$, không filter)** và **C (`by_paragraph` $\le 1000$, có filter `section`)**.
3. Tạo vector bằng `gemini-embedding-001` (`3072` chiều, tự động xử lý `429 Rate Limit` của Free Tier và lưu bộ nhớ đệm cục bộ), nạp vào Qdrant tại `starter/qdrant_storage` và **kiểm chứng nạp lại lần 2 không trùng lặp (`idempotent upsert`)**.
4. Chạy truy vấn Top-3 cho toàn bộ 20 câu hỏi (`15 dev` + `5 test`) và xuất kết quả ra thư mục `results/`.

### 4. Đường dẫn Dữ liệu, Mã nguồn và Báo cáo

| Thành phần | Đường dẫn file | Mô tả nội dung |
| :--- | :--- | :--- |
| **Thông tin học viên** | [STUDENT.md](STUDENT.md) | Họ tên: **Ngô Chí Vĩnh**, MSSV: `2A202603724`, Lớp: `L3B` |
| **Tài liệu nguồn (PDF)** | [starter/data/wb_diem_lai_2024_08.pdf](starter/data/wb_diem_lai_2024_08.pdf) | *Báo cáo Điểm lại Tháng 8/2024: Vươn tới tầm cao mới trên thị trường vốn* — World Bank (`CC BY 3.0 IGO`) |
| **Manifest dữ liệu** | [data/manifest.json](data/manifest.json) | Nguồn tải, giấy phép `CC BY 3.0 IGO`, quy tắc lọc 47/64 trang hợp lệ và ánh xạ 3 chương mục |
| **Bộ câu hỏi Benchmark** | [benchmark/questions.json](benchmark/questions.json) | 20 câu hỏi (`q01`–`q15` dev, `q16`–`q20` test), kèm `gold_page`, `evidence_quote` đã kiểm chứng khớp 100% và `filter` |
| **Mã nguồn Pipeline** | [starter/src/](starter/src/) | `ingestion.py`, `chunking.py`, `embeddings.py`, `store.py`, `evaluation.py`, `models.py`, `run.py` (tham số A/B/C khai báo trong `run.py`) |
| **Nhật ký thí nghiệm** | [artifacts/experiment_log.csv](artifacts/experiment_log.csv) | Cấu hình, giả thuyết và kết quả thực nghiệm của 3 chiến lược A, B, C |
| **Kết quả & Trace** | [results/metrics_summary.json](results/metrics_summary.json), [results/traces_all.json](results/traces_all.json) | Bảng tổng hợp chỉ số `Hit@1`, `Evidence Hit@3`, thống kê chunk (`results/strategy_stats.json`) và toàn bộ trace Top-3. Mục `manual_audit_summary` trong `metrics_summary.json` được thêm thủ công từ `manual_audit.json` sau khi chạy (chạy lại `run.py` sẽ ghi đè mục này) |
| **Kiểm toán thủ công** | [results/manual_audit.json](results/manual_audit.json), [results/manual_audit_tables.md](results/manual_audit_tables.md) | Chấm điểm chi tiết Chunk Coherence (`10` vị trí), Metadata Usefulness (`15` hits) và Grounding Quality (`5` câu test) |
| **Báo cáo cá nhân** | [report/individual/2A202603724_NgoChiVinh.md](report/individual/2A202603724_NgoChiVinh.md) | Báo cáo phân tích đầy đủ 5 khía cạnh đánh giá, so sánh A–B / B–C và phân tích lỗi (file mẫu gốc của đề vẫn giữ tại [report/individual/MSSV_HoTen.md](report/individual/MSSV_HoTen.md)) |

### 5. Tóm tắt Kết quả Thực nghiệm Chính

| Chiến lược | Số Chunk | Dev Hit@1 | Dev Evidence Hit@3 | Test Hit@1 | Test Evidence Hit@3 | Coherence TB (`/2`) | Metadata Hợp lệ (Test) | Filter Compliance (Dev / Test) | Grounding TB (`/2`) |
| :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **A** (`fixed_size` 500/50) | `332` | `10/15` (`66.7%`) | `11/15` (`73.3%`) | `2/5` (`40.0%`) | `2/5` (`40.0%`) | `0.60 / 2` | `15/15` (`100%`) | `1/4` (`25%`) / `2/2` (`100%`) | `1.40 / 2` |
| **B** (`by_paragraph` $\le 1000$) | `195` | `11/15` (`73.3%`) | `15/15` (`100.0%`) | `4/5` (`80.0%`) | `4/5` (`80.0%`) | `1.60 / 2` | `15/15` (`100%`) | `1/4` (`25%`) / `2/2` (`100%`) | `1.80 / 2` |
| **C** (`by_paragraph` + `section` filter) | `195` | **`12/15` (`80.0%`)** | **`15/15` (`100.0%`)** | **`4/5` (`80.0%`)** | **`4/5` (`80.0%`)** | **`1.60 / 2`** | **`15/15` (`100%`)** | **`4/4` (`100%`) / `2/2` (`100%`)** | **`1.80 / 2`** |

---

## 1. Xây pipeline

![Đọc tài liệu, chuẩn hóa, chia chunk, tạo vector, lưu và kiểm tra](assets/ingestion-pipeline.svg)

Chọn tài liệu được phép sử dụng; giữ **ID tài liệu, nguồn, trang/vị trí** và metadata phù hợp. Dùng embedding model thật qua API hoặc chạy local; lưu và truy xuất bằng pgvector, Qdrant, Chroma hoặc một store tương đương.

## 2. So sánh và đánh giá

![Ba chiến lược được đánh giá trên cùng corpus và benchmark dev/test](assets/benchmark-workflow.svg)

Dùng cùng dữ liệu, model và câu hỏi cho cả ba cấu hình. Tách **15 câu dev / 5 câu test** trước khi chạy; chọn cấu hình trên dev, rồi đánh giá test sau khi cố định. Mỗi câu hỏi cần có đoạn bằng chứng và trang nguồn; thiết kế bộ câu hỏi và đánh giá theo [BENCHMARK.md](BENCHMARK.md).

Đánh giá theo năm khía cạnh: **độ chính xác truy xuất**, **tính mạch lạc của chunk**, **tính hữu dụng của metadata**, **chất lượng grounding** và **tác động của chiến lược dữ liệu**. Giải thích lựa chọn bằng kết quả, ví dụ lỗi và các đánh đổi.

## Tài liệu hướng dẫn

| Bạn cần tìm | Tài liệu |
|---|---|
| Setup baseline PostgreSQL + pgvector & Qdrant | [starter/README.md](starter/README.md) |
| Các bước làm và cách tính chỉ số | [GUIDE.md](GUIDE.md) |
| Tiến độ trong 4 giờ | [CHECKPOINTS.md](CHECKPOINTS.md) |
| Năm tiêu chí benchmark và bộ câu hỏi | [BENCHMARK.md](BENCHMARK.md) |
| Tiêu chí chấm điểm | [RUBRIC.md](RUBRIC.md) |
| Quy tắc sử dụng dữ liệu, AI và API | [RULES.md](RULES.md) |
| Cách nộp bài | [SUBMISSION.md](SUBMISSION.md) |
