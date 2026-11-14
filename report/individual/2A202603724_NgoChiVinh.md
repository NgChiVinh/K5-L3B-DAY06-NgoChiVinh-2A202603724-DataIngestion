# Báo cáo cá nhân — Day 6: Data Ingestion Engineering

- **Họ và tên:** Ngô Chí Vĩnh
- **MSSV:** `2A202603724`
- **Lớp:** `L3B`
- **Học phần:** Day 06 · Data Ingestion Engineering

---

## Dữ liệu và pipeline

### 1. Chủ đề, nguồn/quyền, số trang và quy tắc tính trang
- **Chủ đề & Tài liệu nguồn:** Báo cáo kinh tế vĩ mô và chuyên đề thị trường vốn tiếng Việt của Ngân hàng Thế giới (World Bank) tại Việt Nam: *"Báo cáo Điểm lại Tháng 8/2024: Vươn tới tầm cao mới trên thị trường vốn"* (*Taking Stock August 2024: Reaching New Heights in Capital Markets*).
  - **Mã tài liệu (`document_id`):** `wb-diem-lai-2024-08`
  - **Đường dẫn cục bộ:** `starter/data/wb_diem_lai_2024_08.pdf` (dung lượng `3,825,650` bytes)
  - **URL gốc & Giấy phép:** Tài liệu công bố mở từ World Bank Open Knowledge Repository theo giấy phép **Creative Commons Attribution 3.0 IGO (`CC BY 3.0 IGO`)**, cho phép tải về, trích xuất, lập chỉ mục và tái phân phối cho mục đích học thuật/nghiên cứu khi ghi nhận nguồn. Toàn bộ thông tin khai báo được lưu tại `data/manifest.json`.
- **Số trang và quy tắc tính trang nội dung hợp lệ:**
  - Tổng số trang vật lý của file PDF là **64 trang** (đánh số `1..64` theo thứ tự trang PDF 1-based).
  - Áp dụng quy tắc lọc trang nghiêm ngặt theo `GUIDE.md` và `BENCHMARK.md`, pipeline trong `starter/src/ingestion.py` loại bỏ **17 trang không phải nội dung phân tích chính** (ghi vết chi tiết từng trang trong `results/ingestion_log.json`), bao gồm:
    - **12 trang tiền văn bản (trang `1–12`):** Trang bìa ngoài/trong (`1, 3`), trang trắng (`2`), trang bản quyền/miễn trừ trách nhiệm (`4`), mục lục và danh mục hình/bảng/hộp (`5–8`), danh mục chữ viết tắt (`9–10`), lời cảm ơn (`11`), và trang ngăn cách phần Tổng quan (`12`, 83 ký tự).
    - **2 trang ngăn cách chương (`19, 38`):** Trang tiêu đề Chương 1 (`19`, 114 ký tự) và trang tiêu đề Chương 2 (`38`, 126 ký tự).
    - **3 trang cuối (`62–64`):** Trang trắng (`62, 63`, 0 ký tự) và bìa sau (`64`).
  - Danh sách loại trừ được gán **xác định theo số trang** trong `classify_wb_page()` (dựa trên Mục lục), không dựa trên ngưỡng độ dài; trang nào trích xuất ra rỗng cũng bị ghi log với lý do `empty_text`.
  - **Tổng số trang nội dung hợp lệ được nạp vào pipeline:** **47 trang** (vượt mức tối thiểu `>= 30` trang nội dung của `GUIDE.md`), với tổng cộng **`141,104` ký tự** sau chuẩn hóa, chia thành 3 phần chính theo đúng Mục lục báo cáo:
    1. `tong_quan` (trang `13–18`, **6 trang**, `19,990` ký tự): *Tổng quan diễn biến kinh tế vĩ mô, triển vọng 2024–2026 và tóm tắt chuyên đề thị trường vốn*.
    2. `chuong_1_kinh_te_vi_mo` (trang `20–37`, **18 trang**, `50,860` ký tự): *Chương 1 — Diễn biến kinh tế gần đây và triển vọng*.
    3. `chuong_2_thi_truong_von` (trang `39–61`, **23 trang**, `70,254` ký tự): *Chương 2 — Vươn tới tầm cao mới trên thị trường vốn*.

### 2. Chuẩn hóa, lỗi và giới hạn
- **Quy trình đọc và chuẩn hóa (`starter/src/ingestion.py`):**
  1. Đọc từng trang PDF bằng `pypdf` (`6.12.2` trong môi trường chạy, theo `pip show`), loại bỏ các trang thuộc danh sách loại trừ hoặc trích xuất ra rỗng (`len == 0`), ghi log từng trang bị loại vào `results/ingestion_log.json`.
  2. Chuẩn hóa Unicode tiếng Việt về dạng dựng sẵn **NFC (`unicodedata.normalize("NFC", text)`)** để đồng nhất dấu thanh và ký tự tiếng Việt giữa văn bản PDF và câu hỏi truy vấn.
  3. Thay ` ` (non-breaking space) bằng dấu cách, chuẩn hóa ngắt dòng (`
`/`` $ightarrow$ `
`), gộp dấu cách/tab liên tiếp trong mỗi dòng và rút gọn từ 3 dòng trống trở lên còn `

`, **giữ nguyên ranh giới dòng** để chiến lược B/C nhận diện heading và đoạn.
- **Xử lý lỗi và giới hạn kỹ thuật được ghi nhận:**
  - **Lỗi giới hạn tốc độ API (Rate Limit `429 RESOURCE_EXHAUSTED`):** Gói miễn phí (Free Tier) của Gemini API giới hạn `100` yêu cầu nhúng/phút (`embed_content_free_tier_requests`). Khi chạy nhúng toàn bộ `332` chunks của Chiến lược A và `195` chunks của Chiến lược B/C, pipeline gặp `7` lần mã lỗi `429`. Adapter trong `starter/src/embeddings.py` đã tự động bắt ngoại lệ, đọc thời gian chờ (`retry in Xs`) trong thông báo lỗi của Google API (mặc định 62s nếu không có), tạm dừng chờ (`38s–60s`) rồi thử lại thành công 100%, đồng thời lưu bộ nhớ đệm (`results/embedding_cache.json`) và ghi nhận đầy đủ `7` sự kiện `429` vào `results/metrics_summary.json`.
  - **Giới hạn của trình trích xuất văn bản PDF (`pypdf`):** Báo cáo của World Bank có nhiều biểu đồ đa trục (Hình 1.1–1.30, Hình 2.1–2.18) và bảng số liệu nhiều cột (như Bảng 0.1 ở trang 16). Khi trích xuất thuần văn bản bằng `pypdf`, các nhãn trục tung/trục hoành (`"0% 5% 10%... Q1-22 Q2-22..."`) và chú thích song ngữ bị trải phẳng thành các chuỗi số rời rạc nằm xen kẽ hoặc cuối trang, gây giảm điểm mạch lạc (Chunk Coherence) ở những trang dày đặc đồ thị như trang `16, 20, 21, 22`.

### 3. Embedding model, Vector Store, metric, lệnh chạy và chi phí
- **Embedding Model:**
  - **Provider & SDK:** Google Gemini API qua thư viện chính thức `google-genai` (`3.0.0` trong môi trường chạy, theo `pip show`; `requirements.txt` ghi `>=1.0.0`).
  - **Xử lý document/query:** chunk được nhúng với `task_type="RETRIEVAL_DOCUMENT"`, câu hỏi với `task_type="RETRIEVAL_QUERY"`; giống nhau cho cả 3 chiến lược.
  - **Model & Version:** `gemini-embedding-001`
  - **Số chiều vector (`dimensions`):** `3072` chiều (vector thực thụ từ mô hình ngôn ngữ đa ngữ của Google, cấu hình qua `starter/.env`).
- **Vector Store:**
  - **Hệ quản trị & Phiên bản:** **Qdrant Local Persistent Vector Store** (`qdrant-client==1.20.0`), lưu trữ bền vững trên đĩa tại `starter/qdrant_storage` (ngoài ra `starter/src/store.py` cũng cài đặt sẵn `PgVectorStore` tương thích `psycopg` cho môi trường PostgreSQL + pgvector).
  - **Tổ chức Collection & Metric:** Mỗi chiến lược được lưu vào một collection độc lập (`day6_strategy_A`, `day6_strategy_B`, `day6_strategy_C`) với độ đo tương đồng **Cosine (`Distance.COSINE`)**. Qdrant chạy ở chế độ local (`QdrantClient(path=...)`) không dùng chỉ mục HNSW nên tìm kiếm là duyệt toàn bộ (exact); số bản ghi được đếm bằng `count(exact=True)`.
  - **Cơ chế chống trùng lặp khi nạp lại (Idempotent Upsert):** Mỗi chunk có định danh xác định `chunk_id = "{document_id}__{strategy}__p{page:02d}__c{chunk_index:03d}"` và được ánh xạ một-một sang `point_id = uuid.uuid5(NAMESPACE_DNS, f"day6:{strategy}:{chunk_id}")`. Khi nạp lại tài liệu cho cùng `(document_id, strategy)`, hàm `QdrantVectorStore.upsert()` tự động xóa các point cũ không còn nằm trong danh sách `chunk_id` mới và ghi đè (`upsert`) theo `point_id` cố định. Thực nghiệm nạp lại lần 2 trong `src/run.py` xác nhận số lượng bản ghi giữ nguyên tuyệt đối: Chiến lược A (`332` $\rightarrow$ `332`), Chiến lược B (`195` $\rightarrow$ `195`), Chiến lược C (`195` $\rightarrow$ `195`), `idempotent_verified = true`.
- **Lệnh chạy tái lập kết quả:**
  ```powershell
  cd D:\lab06-vinuni\K5-L3B-DAY06-2A202603724-DataIngestion\starter
  python -m src.run
  ```
- **Chi phí thực tế:** **`$0.00` (Miễn phí trên Gemini API Free Tier)**. Tổng số lượng văn bản đã nhúng là `332` chunks (A) + `195` chunks (B, dùng chung vector với C) + `20` câu hỏi = `547` văn bản duy nhất (tương đương `~63,678` word tokens tính trên cả 3 chiến lược).

### 4. Metadata bắt buộc, trường lọc bổ sung, nguồn giá trị và lý do chọn
Mỗi chunk lưu vào Qdrant đều đính kèm payload metadata đầy đủ:
- **Các trường bắt buộc truy vết nguồn:**
  - `document_id`: `"wb-diem-lai-2024-08"` (khai báo từ `data/manifest.json`).
  - `source`: `"starter/data/wb_diem_lai_2024_08.pdf"` (đường dẫn tới file gốc).
  - `page`: Số nguyên `13..61` biểu thị đúng số trang vật lý (1-based) trong file PDF.
  - `chunk_id`, `strategy`, `chunking_method`, `chunk_index`, `char_start`, `char_end`, `char_length`.
- **Trường lọc bổ sung (`section`) và các trường ngữ cảnh (`sub_section`, `year`, `language`):**
  - **Nguồn giá trị:** Trường `section` và `sub_section` được gán xác định dựa trên ánh xạ khoảng trang từ Mục lục chính thức của báo cáo (trang 8 PDF):
    - Trang `13–18` $\rightarrow$ `section = "tong_quan"`
    - Trang `20–37` $\rightarrow$ `section = "chuong_1_kinh_te_vi_mo"`
    - Trang `39–61` $\rightarrow$ `section = "chuong_2_thi_truong_von"`
  - **Lý do chọn `section` làm trường lọc cho Chiến lược C:** Báo cáo Điểm lại của World Bank có cấu trúc gồm phần *Tổng quan* (trang `13–18`) tóm tắt toàn bộ các con số chính của *Chương 1* (trang `20–37`) và *Chương 2* (trang `39–61`), nhưng đôi khi cập nhật ở các mốc thời gian khác nhau (ví dụ: tỷ giá cuối tháng 6/2024 ở trang 14 phần Tổng quan so với tỷ giá cuối tháng 3/2024 ở trang 28 Chương 1). Nếu chỉ tìm kiếm thuần vector (Chiến lược B), các đoạn văn ở Phần Tổng quan và các Chương chi tiết rất dễ cạnh tranh điểm tương đồng và đè lên nhau. Việc lọc theo `section` giúp khoanh vùng chính xác chương mục mà người dùng muốn tra cứu.

---

## Cấu hình và benchmark

### 1. Ba chiến lược A / B / C và thiết kế so sánh có kiểm soát
Tham số của ba cấu hình được khai báo trực tiếp trong `starter/src/run.py` (bước 2) và thực thi bởi các hàm `fixed_size()` / `by_paragraph()` trong `starter/src/chunking.py`:

| Chiến lược | Phương pháp cắt (`chunking`) | Tham số kích thước & gối đầu | Xử lý cấu trúc văn bản | Metadata đính kèm | Bộ lọc khi truy vấn (`filter`) | Mục đích so sánh có kiểm soát |
| :---: | :--- | :--- | :--- | :--- | :--- | :--- |
| **A** *(Baseline)* | `fixed_size` | `size = 500` ký tự, `overlap = 50` ký tự | Ghép dòng phẳng trên từng trang, giữ nguyên cả dòng tiêu đề chạy đầu trang | `document_id`, `source`, `page`, `section`, `sub_section`, `year`, `language` | **Không (`None`)** | Đánh giá đường cơ sở cắt cứng theo độ dài ký tự cố định. |
| **B** *(Structure-aware)* | `by_paragraph` | `max_size = 1000` ký tự, `overlap = 0` | Loại bỏ running header đầu trang; gom các dòng thành khối, mở khối mới tại dòng heading (`I.`, `1.2`, `Bảng n`, `Hình n`, `Hộp n`) hoặc khi khối đã `>= 350` ký tự và dòng kết thúc bằng dấu chấm; khối `> 1000` ký tự được tách theo câu; sau đó gộp các khối liên tiếp sao cho mỗi chunk `<= 1000` ký tự | Giống hệt Chiến lược A | **Không (`None`)** | **So sánh A vs B:** Đo tác động của *chunking theo cấu trúc* so với *cắt cố định 500 ký tự* (cùng không dùng bộ lọc). **Lưu ý:** B còn khác A ở việc bỏ running header, nên A–B thay **2 yếu tố** (cách cắt + lọc header); không thể quy toàn bộ chênh lệch cho riêng cách cắt. |
| **C** *(Structure + Metadata Filter)* | `by_paragraph` | `max_size = 1000` ký tự, `overlap = 0` | Giống hệt Chiến lược B (tạo ra cùng `195` chunks với độ dài y hệt B) | Giống hệt Chiến lược B | **Có (`filter = {"section": ...}`)** tại tầng Qdrant khi câu hỏi có `filter` | **So sánh B vs C:** Cô lập hoàn toàn tác động của *bộ lọc metadata (`section`)* khi phương pháp chunking và tập vector giữ nguyên 100%. |

### 2. Bộ câu hỏi Benchmark (20 câu: 15 `dev` / 5 `test`) và kiểm chứng Evidence
- Toàn bộ **20 câu hỏi** được lưu tại `benchmark/questions.json`, chia cố định trước khi chạy thử nghiệm thành:
  - **Tập `dev` (`15` câu: `q01`–`q15`):** Gồm `4` câu trực tiếp (`q01, q02, q08, q09`), `3` câu diễn đạt lại (`q03, q07, q10`), `4` câu điều kiện/ngoại lệ (`q04, q05, q06, q11`), và `4` câu có điều kiện lọc metadata `section` (`q12, q13, q14, q15`).
  - **Tập `test` (`5` câu: `q16`–`q20`):** Được khóa làm tập holdout độc lập, gồm `1` câu trực tiếp (`q16`), `1` câu điều kiện/ngoại lệ (`q17`), `1` câu diễn đạt lại (`q18`), và `2` câu có điều kiện lọc metadata `section` (`q19, q20`).
- **Quy trình kiểm chứng `evidence_quote`:** Trước khi chạy đánh giá, toàn bộ 20 câu hỏi được kiểm tra tự động bằng script đối chiếu với văn bản đã chuẩn hóa NFC của từng trang PDF: `100% (20/20)` chuỗi `evidence_quote` là chuỗi con khớp chính xác trên trang chuẩn `gold_page`. Ngoài ra, đối với các số liệu được World Bank nhắc lại ở cả phần Tổng quan và Chương chi tiết (`q01, q05, q06, q11, q19, q20`), trường `alternative_gold_pages` được ghi nhận minh bạch để chấm chính xác khi câu hỏi không ép buộc bộ lọc chương.
- **Quy tắc chấm hit tự động (`starter/src/evaluation.py`):** một chunk là *evidence hit* khi thuộc đúng `document_id` + trang gold (hoặc trang thay thế) **và** (i) chứa nguyên văn `evidence_quote` sau khi gộp khoảng trắng/viết thường, hoặc (ii) chứa cả 65 ký tự đầu lẫn 65 ký tự cuối của quote, hoặc (iii) chứa `>= 75%` số mệnh đề (tách theo `.`/`;`, dài `>= 25` ký tự) của quote. Trong lần chạy này **mọi hit đều đạt độ phủ 100%** (`evidence_coverage = 1.0` cho tất cả hit trong `results/traces_all.json`), nên nhánh (iii) không làm thay đổi kết quả.
- **Ghi chú về dev/test:** `python -m src.run` tính trace của dev và test trong cùng một lần chạy. Tiêu chí chọn chiến lược đã được ghi trong `benchmark/questions.json` (`selection_criteria_locked_before_test`) trước khi chạy, và kết quả test không được dùng để thay đổi tham số chunking, filter hay bộ câu hỏi.

### 3. Tiêu chí chọn chiến lược đã chốt trước khi xem tập `test`
Trước khi mở kết quả tập `test`, quy tắc chọn chiến lược tối ưu trên tập `dev` (`15` câu) đã được chốt như sau:
1. Ưu tiên chiến lược có **Dev Evidence Hit@3** cao nhất và giảm thiểu số câu bị cắt rời bằng chứng qua nhiều chunk (`split_evidence_across_chunks`).
2. Nếu hai chiến lược hòa nhau về Dev Evidence Hit@3, chọn chiến lược có **Dev Hit@1** cao hơn, **điểm mạch lạc (Chunk Coherence)** cao hơn, và **tỷ lệ tuân thủ điều kiện lọc (`Filter Compliance`)** trên các câu có filter cao hơn với chi phí thời gian/lưu trữ hợp lý.
- Trên tập `dev`, **Chiến lược C** đạt `Evidence Hit@3 = 15/15 (100.0%)` (vượt xa A `11/15 = 73.33%`), đạt `Hit@1 = 12/15 (80.0%)` (cao hơn B `11/15 = 73.33%` và A `10/15 = 66.67%`), và đạt `Filter Compliance = 4/4 (100.0%)` (so với `1/4 = 25.0%` của A và B). Do đó, **Chiến lược C được chốt là chiến lược được chọn trước khi đánh giá trên tập `test`**.

---

## Kết quả

### Bảng 1: Độ chính xác truy hồi (Retrieval Accuracy) và Chi phí tài nguyên

| Strategy | Split | Hit@1 (n/N) | Evidence Hit@3 (n/N) | Chunk count | Thời gian | Chi phí |
| :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **A** (`fixed_size` 500/50, no filter) | `dev` | `10/15` (`66.67%`) | `11/15` (`73.33%`) | `332` (mean `467.6` chars, `~33,850` tokens) | `228.98s` *(gồm chờ rate-limit)* | `$0.00` *(Gemini Free Tier)* |
| **A** (`fixed_size` 500/50, no filter) | `test` | `2/5` (`40.00%`) | `2/5` (`40.00%`) | `332` | *(như trên)* | `$0.00` |
| **B** (`by_paragraph` <=1000, no filter) | `dev` | `11/15` (`73.33%`) | `15/15` (`100.00%`) | `195` (mean `706.0` chars, `~29,828` tokens) | `174.14s` *(gồm chờ rate-limit)* | `$0.00` *(Gemini Free Tier)* |
| **B** (`by_paragraph` <=1000, no filter) | `test` | `4/5` (`80.00%`) | `4/5` (`80.00%`) | `195` | *(như trên)* | `$0.00` |
| **C** (`by_paragraph` <=1000 + `section` filter) | `dev` | **`12/15` (`80.00%`)** | **`15/15` (`100.00%`)** | `195` (mean `706.0` chars, `~29,828` tokens) | `175.31s` *(= 174.14s nhúng của B + 1.17s upsert; C dùng lại vector của B)* | `$0.00` *(Gemini Free Tier)* |
| **C** (`by_paragraph` <=1000 + `section` filter) | `test` | **`4/5` (`80.00%`)** | **`4/5` (`80.00%`)** | `195` | *(như trên)* | `$0.00` |

*(Ghi chú thêm về Retrieval: Ở cả 3 chiến lược, tỷ lệ tìm trúng trang chuẩn `Page Hit@3` đều đạt `15/15` trên `dev` và `5/5` trên `test`. Lý do khiến `Evidence Hit@3` của Chiến lược A tụt xuống `11/15` trên `dev` và `2/5` trên `test` là vì quy tắc chấm nghiêm ngặt của `BENCHMARK.md`: không tính là hit khi bằng chứng bị cắt rời qua hai chunk khác nhau khiến một chunk đơn lẻ không đủ trả lời — Chiến lược A bị cắt rời bằng chứng ở `4` câu `dev` (`q02, q05, q07, q09`) và `3` câu `test` (`q17, q19, q20`), trong khi Chiến lược B và C chỉ bị tách ở duy nhất `1` câu `test` (`q19`)).*

### Bảng 2: Đánh giá thủ công về Độ mạch lạc (Coherence), Metadata và Chất lượng căn cứ (Grounding)

| Strategy | Coherence trung bình /2 (n) | Metadata đủ và đúng (n/N) | Filter tuân thủ (n/N hoặc N/A) | Grounding 0/1/2 (số câu) và trung bình /2 |
| :---: | :---: | :---: | :---: | :---: |
| **A** | **`0.60 / 2.00`** (`n = 10` vị trí; `4` mẫu điểm `0`, `6` mẫu điểm `1`, `0` mẫu điểm `2`) | **`15/15` (`100.0%`)** trên mẫu `5 câu test × top-3` | Test: `2/2` *(ngẫu nhiên, không bật filter)* \| Dev: `1/4` (`25.0%`) \| Tổng: `3/6` (`50.0%`) | Điểm `0`: `0` câu \| Điểm `1`: `3` câu (`q17, q19, q20`) \| Điểm `2`: `2` câu (`q16, q18`) $\rightarrow$ **TB: `1.40 / 2.00`** |
| **B** | **`1.60 / 2.00`** (`n = 10` vị trí; `0` mẫu điểm `0`, `4` mẫu điểm `1`, `6` mẫu điểm `2`) | **`15/15` (`100.0%`)** trên mẫu `5 câu test × top-3` | Test: `2/2` *(ngẫu nhiên, không bật filter)* \| Dev: `1/4` (`25.0%`) \| Tổng: `3/6` (`50.0%`) | Điểm `0`: `0` câu \| Điểm `1`: `1` câu (`q19`) \| Điểm `2`: `4` câu (`q16, q17, q18, q20`) $\rightarrow$ **TB: `1.80 / 2.00`** |
| **C** | **`1.60 / 2.00`** (`n = 10` vị trí; `0` mẫu điểm `0`, `4` mẫu điểm `1`, `6` mẫu điểm `2`) | **`15/15` (`100.0%`)** trên mẫu `5 câu test × top-3` | **Test: `2/2` (`100.0%`) \| Dev: `4/4` (`100.0%`) \| Tổng: `6/6` (`100.0%`)** | Điểm `0`: `0` câu \| Điểm `1`: `1` câu (`q19`) \| Điểm `2`: `4` câu (`q16, q17, q18, q20`) $\rightarrow$ **TB: `1.80 / 2.00`** |

### Đường dẫn trace, nhãn thủ công và cách chọn mẫu
- **Toàn bộ trace truy hồi (`20 câu × 3 chiến lược × top-3`):** `results/traces_all.json`
- **Tổng hợp số liệu định lượng & thống kê phân phối chunk:** `results/metrics_summary.json` và `results/strategy_stats.json`
- **Nhật ký nạp dữ liệu & danh sách 17 trang bị loại trừ:** `results/ingestion_log.json`
- **Bảng kiểm toán thủ công chi tiết (Coherence, Metadata, Grounding):** `results/manual_audit.json` và bản trình bày bảng Markdown tại `results/manual_audit_tables.md`
- **Dữ liệu đối chiếu 10 vị trí Coherence cố định:** `results/coherence_samples_raw.json`. Cách chọn mẫu: Chọn cố định **10 trang đầu tiên có nội dung liên tiếp** của báo cáo (`pos_13, pos_14, pos_15, pos_16, pos_17, pos_18, pos_20, pos_21, pos_22, pos_23`, bao phủ toàn bộ 6 trang phần *Tổng quan* và 4 trang đầu của *Chương 1* có nhiều bảng và biểu đồ), sau đó lấy tất cả các chunk rơi vào từng vị trí của cả 3 chiến lược A, B, C để chấm đối chiếu trên cùng một mặt bằng.

---

## Phân tích và kết luận

### 1. So sánh có kiểm soát A–B và B–C; phân tích các ví dụ lỗi điển hình

#### a) So sánh A vs B (Tác động của Chunking theo đoạn văn so với Cắt cố định 500 ký tự)
Khi giữ nguyên mô hình nhúng `gemini-embedding-001` (`3072` chiều), giữ nguyên Vector Store Qdrant và cùng không dùng bộ lọc metadata, việc chuyển từ cắt cố định 500 ký tự (`overlap=50`) ở **Chiến lược A** sang cắt theo ranh giới đoạn văn và câu (`max_size=1000`) kèm lọc bỏ running header ở **Chiến lược B** tạo ra cải thiện rõ trên cả 5 khía cạnh. **Giới hạn của phép so sánh:** A–B thay đổi đồng thời 2 yếu tố (cách cắt chunk và việc bỏ running header `"BÁO CÁO ĐIỂM LẠI THÁNG 8/2024..."`), nên các chênh lệch dưới đây là tác động gộp của cả hai; để tách riêng cần chạy thêm một biến thể A' (cắt cố định 500/50 nhưng có bỏ header). B–C là phép so sánh chỉ thay đúng một yếu tố.
- **Giảm `41.3%` số lượng chunk và loại bỏ dư thừa lưu trữ:** Số chunk giảm từ `332` (`155,231` ký tự do cộng dồn phần gối đầu 50 ký tự và tiêu đề đầu trang) xuống `195` (`137,676` ký tự), giúp thời gian nạp và số lượng lời gọi API giảm tương ứng.
- **Tăng mạnh độ mạch lạc (`0.60/2` $\rightarrow$ `1.60/2`) và chất lượng căn cứ (`1.40/2` $\rightarrow$ `1.80/2`):** Chiến lược A thường xuyên cắt đứt giữa từ tiếng Việt (`"tăng trưởng 7,4%... Các dịc"` / `"h dịch vụ"`, `"ngân hàng t"` / `"o Q1-2024"`) và băm nhỏ Bảng 0.1 (`pos_16`) cũng như các trục số biểu đồ (`pos_20..pos_22`). Chiến lược B bảo toàn nguyên vẹn từng đoạn lập luận kinh tế (độ dài trung vị `759` ký tự).
- **Tăng vọt `Evidence Hit@3` từ `73.33%` lên `100.00%` trên `dev` và từ `40.00%` lên `80.00%` trên `test`:** Chiến lược B khắc phục triệt để 4 ca đứt gãy bằng chứng trên `dev` (`q02, q05, q07, q09`) và 2/3 ca đứt gãy bằng chứng trên `test` (`q17, q20`).

#### b) So sánh B vs C (Tác động của Bộ lọc Metadata `section`)
Khi giữ nguyên 100% tập `195` chunks của Chiến lược B và chỉ bật thêm điều kiện lọc `section` tại Qdrant cho các câu hỏi có filter (`q12–q15` trên `dev`, `q19–q20` trên `test`):
- **Tỷ lệ tuân thủ điều kiện lọc (`Filter Compliance`) trên tập `dev` tăng từ `1/4 (25.0%)` lên `4/4 (100.0%)`** (và đạt tuyệt đối `6/6 = 100.0%` trên toàn bộ benchmark).
- **Nâng `Dev Hit@1` từ `11/15 (73.33%)` lên `12/15 (80.00%)`:** Ở các câu `q12` và `q13` (hỏi số liệu chi tiết của Chương 1), Chiến lược B để các đoạn tóm tắt ở trang 15 (`tong_quan`) và trang 47 (`chuong_2_thi_truong_von`) chen vào Rank 2 và Rank 3; Chiến lược C lọc sạch các chunk ngoại lai này. Đặc biệt, ở câu `q15`, bộ lọc metadata trực tiếp cứu một ca sai số liệu ở ngay vị trí **Rank 1**.

#### c) Phân tích 3 ví dụ lỗi cụ thể (kèm ID câu hỏi, Chunk ID, số trang và nguyên nhân gốc rễ)

1. **Ví dụ lỗi 1 — Cắt ngang bằng chứng đa điều kiện do kích thước cố định (`q02` trên `dev` và `q17`, `q20` trên `test` ở Chiến lược A):**
   - **Câu hỏi `q20` (`test`, trang chuẩn `60`):** Hỏi về 3 con số huy động vốn bổ sung đến năm 2030 từ (i) BHXH (`20 tỷ USD`), (ii) bảo hiểm nhân thọ (`15 tỷ USD`), và (iii) quỹ đầu tư & quỹ hưu trí tư nhân (`14 tỷ USD`).
   - **Hiện tượng trong `results/traces_all.json`:** Ở Chiến lược A, Rank 1 là chunk `wb-diem-lai-2024-08__A__p60__c004` (`score = 0.8018`) chứa được hai con số `20 tỷ đô la Mỹ` và `15 tỷ đô la Mỹ`, nhưng bị cắt cứng ở ký tự thứ 500 đúng vào cụm từ: *"...Các quỹ đầu tư và quỹ hưu trí tư nhân tăng tr"*. Con số thứ ba (`"14 tỷ đô la Mỹ"`) bị đẩy sang chunk kế tiếp `wb-diem-lai-2024-08__A__p60__c005` (`score = 0.7801`, Rank 2). Tương tự, ở câu `q17` (trang `46`), chunk `wb-diem-lai-2024-08__A__p46__c003` (Rank 1) bị cắt đứt giữa câu kết luận *"...gây ra sự biến dạng cho chức năng định giá của thị trường trái phiếu"*, còn chữ *"Chính phủ."* rơi sang `p46__c004` (Rank 3). Ở câu `q02` (trang `23`), câu chứa chỉ số `IPI = 166` nằm ở `wb-diem-lai-2024-08__A__p23__c001` (Rank 3) nhưng câu kế tiếp chứa `PMI = 55` bị cắt sang `p23__c002` (nằm ngoài Top-3, bị hai chunk nhãn biểu đồ trang 24 là `p24__c002` và `p24__c001` đè lên).
   - **Cách khắc phục ở Chiến lược B & C:** Thuật toán `by_paragraph` giữ trọn cả đoạn văn 3 nguồn vốn trong duy nhất 1 chunk `wb-diem-lai-2024-08__B__p60__c003` (`942` ký tự, Rank 1, `score = 0.8312`) và giữ trọn đoạn IPI + PMI trong `wb-diem-lai-2024-08__B__p23__c001` (`954` ký tự, Rank 1, `score = 0.7780`).

2. **Ví dụ lỗi 2 — Nhiễu chéo giữa phần Tổng quan và Chương chi tiết dẫn tới sai lệch số liệu theo mốc thời gian (`q15` trên `dev` ở Chiến lược B):**
   - **Câu hỏi `q15` (`dev`, có filter `section = "tong_quan"`, trang chuẩn `14`):** *"Trong phần Tổng quan của báo cáo, tỷ giá VND/US$ trên thị trường đã tăng từ mức 24.258 VND vào tháng 12/2023 lên mức bao nhiêu vào cuối tháng 6/2024 và nhu cầu mua vàng trong nước tăng bao nhiêu phần trăm?"*
   - **Hiện tượng trong `results/traces_all.json`:** Ở **Chiến lược B** (không lọc metadata), vị trí **Rank 1** trả về chunk `wb-diem-lai-2024-08__B__p28__c002` thuộc **`chuong_1_kinh_te_vi_mo`** (trang `28`, `score = 0.8033`), đẩy chunk đúng ở trang `14` là `wb-diem-lai-2024-08__B__p14__c003` (`tong_quan`, `score = 0.8031`) xuống **Rank 2**. Nghiêm trọng hơn, đoạn văn ở trang `28` viết: *"tỷ giá tăng từ 24.258 VND trong tháng 12/2023 lên **24.760 VND vào cuối tháng 3/2024**..."*, trong khi đoạn văn ở trang `14` phần Tổng quan viết: *"tỷ giá VND/US$ tăng từ mức 24.258 VND trong tháng 12/2023 lên **25.334 VND vào cuối tháng 6/2024**..."*. Do hai đoạn văn có cấu trúc câu gần như song song (đều nhắc tới chênh lệch lãi suất `166 điểm cơ bản`, tỷ giá `24.258 VND` tháng 12/2023 và nhu cầu mua vàng `+28,6%`), vector embedding của `p28__c002` có điểm cosine nhỉnh hơn `0.0002` so với `p14__c003`. Nếu hệ thống chỉ lấy Top-1 hoặc ưu tiên Rank 1 mà không có bộ lọc chương mục, LLM sẽ trả lời nhầm số liệu tháng 3/2024 thay vì tháng 6/2024.
   - **Cách khắc phục ở Chiến lược C:** Khi áp dụng bộ lọc `filter = {"section": "tong_quan"}` tại Qdrant, toàn bộ các chunk của Chương 1 (bao gồm `p28__c002`) bị loại ngay từ tầng chỉ mục, giúp `wb-diem-lai-2024-08__C__p14__c003` vươn lên **Rank 1** chính xác tuyệt đối.

3. **Ví dụ lỗi 3 — Đoạn văn dài vượt ngưỡng `max_size = 1000` ký tự làm tách câu kết luận (`q19` trên `test` ở cả Chiến lược A, B và C):**
   - **Câu hỏi `q19` (`test`, có filter `section = "chuong_2_thi_truong_von"`, trang chuẩn `49`):** Hỏi hai ý: (1) quy mô huy động vốn bình quân hàng năm trên HOSE & HNX trong 5 năm qua (`37 ngàn tỷ đồng / 1,5 tỷ USD`), và (2) số đợt IPO cùng giá trị huy động trong năm 2023 (`3 đợt IPO, 173 tỷ đồng / 7 triệu USD`).
   - **Hiện tượng trong `results/traces_all.json`:**
     - Ở **Chiến lược A**, Rank 1 (`wb-diem-lai-2024-08__A__p49__c003`) chỉ chứa câu về 3 đợt IPO năm 2023 (`173 tỷ đồng`), còn con số `37 ngàn tỷ đồng` nằm ở `p49__c002` bị rơi khỏi Top-3! Thay vào đó, Rank 3 (`p49__c007`) lại chứa chú thích về sàn UPCOM (`32 ngàn tỷ đồng`), tạo nguy cơ trả lời sai sàn giao dịch.
     - Ở **Chiến lược B và C**, do khối văn bản mở đầu mục Thị trường cổ phiếu trên trang `49` dài `1,095` ký tự (vượt ngưỡng `max_size = 1000`), hàm `_split_oversized_block()` tách theo câu và câu cuối cùng (*"Trong năm 2023, chỉ có ba đợt IPO được thực hiện, huy động được 173 tỷ đồng (7 triệu đô la Mỹ)."*, dài `95` ký tự) rơi thành một chunk riêng `wb-diem-lai-2024-08__C__p49__c002`, trong khi phần trước (chứa con số `37 ngàn tỷ đồng`) nằm ở `wb-diem-lai-2024-08__C__p49__c001` (`999` ký tự). Mặc dù cả hai chunk đều được truy hồi ngay tại **Rank 1** (`p49__c001`, `score = 0.7870`) và **Rank 2** (`p49__c002`, `score = 0.7801`) — tức Top-3 chứa đủ 100% thông tin — nhưng xét theo quy tắc chấm nghiêm ngặt *"một chunk đơn lẻ phải chứa đủ bằng chứng"*, câu `q19` vẫn bị tính là `split_evidence_across_chunks = true` (không tính Hit@3 đơn lẻ và chấm Grounding = `1/2`). Phân tích này cho thấy ngưỡng `max_size = 1000` không có gối đầu câu (`sentence overlap = 1`) có thể cắt rời câu kết luận ngắn ở cuối một đoạn văn dài hơi vượt ngưỡng.

### 2. Chiến lược được chọn, đánh đổi và điều kiện áp dụng
- **Chiến lược được chọn:** **Chiến lược C (`by_paragraph`, `max_size = 1000`, kèm bộ lọc metadata `section`)**.
- **Đánh đổi (Trade-offs):**
  - **Ưu điểm vượt trội:** So với Chiến lược A, Chiến lược C giảm `41.3%` số lượng vector cần lưu trữ (`195` so với `332` chunks), nâng điểm mạch lạc Chunk Coherence từ `0.60/2` lên `1.60/2`, nâng Grounding Quality trên tập `test` từ `1.40/2` lên `1.80/2`, nâng `Evidence Hit@3` từ `73.33%` lên `100.00%` (dev) và từ `40.00%` lên `80.00%` (test). So với Chiến lược B, Chiến lược C giữ nguyên chi phí lưu trữ nhưng nâng `Filter Compliance` từ `25.0%` lên `100.0%` trên tập `dev` và nâng `Dev Hit@1` từ `73.33%` lên `80.00%`.
  - **Chi phí / Rủi ro đánh đổi:**
    1. Các chunk của Chiến lược C dài hơn (trung bình `706` ký tự so với `467.6` ký tự của A), nên khi đưa Top-3 vào prompt của LLM sẽ tiêu tốn nhiều context token hơn khoảng `~1.5` lần cho mỗi truy vấn.
    2. Việc áp dụng bộ lọc cứng (`hard filter` trên trường `section`) đòi hỏi tầng định tuyến truy vấn (Query Router / Intent Classifier) hoặc giao diện người dùng phải xác định đúng `section` cần lọc; nếu gán sai nhãn `filter` ở đầu vào, bộ lọc cứng sẽ loại bỏ mất chương chứa đáp án.
- **Điều kiện áp dụng tốt nhất:** Phù hợp cho các báo cáo phân tích vĩ mô, tài liệu chính sách, báo cáo tài chính hoặc sổ tay kỹ thuật có cấu trúc chương mục rõ ràng và có phần Tóm tắt điều hành (*Executive Summary*) lặp lại thuật ngữ của các chương chi tiết.

### 3. Hạn chế của dữ liệu, nhãn, tập test nhỏ và cách đo thời gian/chi phí
1. **Hạn chế của dữ liệu & công cụ trích xuất PDF:** Corpus chứa nhiều biểu đồ đa trục và bảng số liệu nhiều cột (Bảng 0.1 trang 16, Hình 1.1–1.8 trang 20–22, Hình 2.12 trang 49). Trình đọc `pypdf` chỉ trích xuất lớp văn bản phẳng mà không nhận diện được cấu trúc ô bảng hay tách lớp đồ họa vector, dẫn tới sự xuất hiện của các chunk chứa nhãn trục số biểu đồ rời rạc (khiến Coherence của B và C dừng ở mức `1.60/2` thay vì `2.00/2`).
2. **Hạn chế của nhãn tự gán (Self-grading bias):** Bộ câu hỏi benchmark và điểm kiểm toán thủ công (Coherence, Grounding) do cùng một người thực hiện thiết kế và chấm. Để giảm thiểu thiên kiến chủ quan, bài làm đã áp dụng quy tắc kiểm chứng chuỗi con tự động (`evidence_quote` phải khớp chính xác trong văn bản chuẩn hóa) và chấm trừ điểm nghiêm ngặt đối với mọi trường hợp bằng chứng bị tách qua 2 chunk (như câu `q19` ở cả B và C).
3. **Hạn chế của quy mô tập `test` nhỏ (`5` câu):** Trên tập `test` chỉ có `5` câu hỏi (`2` câu có filter), mỗi câu tương ứng với `20%` độ chính xác. Ngoài ra, cả 2 câu có filter trên tập `test` (`q19, q20`) đều chứa các thuật ngữ đặc thù của Chương 2 (`IPO, HOSE, HNX, BHXH, MSCI`) nên ngay cả khi không bật bộ lọc (Chiến lược B), tìm kiếm ngữ nghĩa vẫn đưa các chunk Chương 2 lên Top-3, làm cho kết quả trên tập `test` của B và C bằng nhau (`4/5 = 80.0%`), trong khi lợi thế thực sự của C được bộc lộ rõ hơn trên tập `dev` (`q12, q13, q15`).
4. **Hạn chế khi đo thời gian và chi phí trên Free Tier:** Thời gian chạy lần đầu (`228.98s` cho A, `174.14s` cho B) bị chi phối chủ yếu bởi `7` lần ngủ chờ (38s–60s/lần) khi chạm ngưỡng `100 items/phút` của Gemini Free Tier, chứ không phản ánh độ trễ tính toán thuần túy của chunking hay Qdrant. Thời gian của C (`175.31s`) gồm cả thời gian nhúng của B vì C dùng lại vector của B. Thời gian khi chạy lại với cache chưa được ghi vào artifact nên không báo cáo ở đây. Chi phí `$0.00` là do dùng Free Tier, không phải ước tính theo giá trả phí.
5. **Tái lập:** `results/embedding_cache.json` (~23 MB) và các file `*.sqlite` của Qdrant không được commit (đã đưa vào `.gitignore`), nên người chấm cần `GEMINI_API_KEY` của riêng mình để chạy lại `python -m src.run`. Mục `manual_audit_summary` trong `results/metrics_summary.json` được bổ sung thủ công từ `results/manual_audit.json` sau khi chạy; chạy lại pipeline sẽ ghi đè file này và mất mục đó (số liệu gốc vẫn còn trong `results/manual_audit.json`).
6. **Phạm vi kết luận:** Kết quả chỉ áp dụng cho một tài liệu (47 trang) và 20 câu hỏi; chênh lệch 1 câu bằng 6,7 điểm % trên dev và 20 điểm % trên test, nên không suy rộng thành "chiến lược tốt nhất" cho corpus khác.

### 4. Hướng cải tiến nếu làm lại hoặc mở rộng
1. **Bổ sung gối đầu theo câu (`Sentence-level Overlap = 1 câu`) cho chiến lược `by_paragraph`:** Khi một đoạn văn dài vượt ngưỡng `max_size = 1000` ký tự (như khối mở đầu trang 49 ở câu `q19` dài `1,095` ký tự), việc giữ lại 1–2 câu cuối của mảnh trước hoặc nâng nhẹ ngưỡng gộp câu cuối (`tolerance = +120` ký tự nếu câu cuối cùng kết thúc đoạn) sẽ giữ trọn câu *"Trong năm 2023, chỉ có ba đợt IPO..."* nằm cùng `p49__c001`, khắc phục triệt để lỗi tách bằng chứng ở `q19`.
2. **Trích xuất nhận diện bố cục (Layout-aware PDF Parsing) và lọc nhiễu trục biểu đồ:** Thay `pypdf` bằng công cụ phân tích bố cục tài liệu (`Docling`, `Marker`, hoặc `PyMuPDF4LLM`) kết hợp bước hậu xử lý phát hiện các khối văn bản có tỷ lệ chữ số/nhãn trục đồ thị cao để chuyển bảng thành định dạng Markdown Table chuẩn và loại bỏ các chuỗi số trục tọa độ rời rạc ở các trang `20–24, 47, 49`.
3. **Kết hợp Hybrid Search (BM25 + Dense Vector) và Bộ lọc mềm (Soft Metadata Boosting):** Kết hợp điểm tìm kiếm từ khóa chính xác (cho các con số, mã định danh, tên tổ chức như `VSDC`, `SCB`, `VAMC`, `IPI`, `PMI`) với vector `gemini-embedding-001`, đồng thời hỗ trợ cơ chế cộng điểm ưu tiên (`metadata boosting`) bên cạnh bộ lọc cứng để tăng độ bền vững khi người dùng không chỉ định rõ chương mục.


---

## Sử dụng công cụ AI và cách kiểm tra (theo `RULES.md`)

- **Công cụ đã dùng:** Trợ lý AI lập trình được dùng để giải thích yêu cầu đề, gợi ý và viết code pipeline (`starter/src/`: đọc PDF, chunking, adapter Gemini có xử lý `429`, Qdrant store, đánh giá), gợi ý câu hỏi benchmark từ nội dung báo cáo, và hỗ trợ soạn phần trình bày báo cáo/README. Học viên tự chọn corpus, chốt cấu hình A/B/C, tách dev/test và tiêu chí chọn chiến lược trước khi chạy, tự chạy pipeline với API key của mình và đọc lại code để giải thích được từng bước.
- **Rà soát cuối:** Claude Code (Anthropic) được dùng để đối chiếu báo cáo với code, manifest và `results/`; các mô tả không khớp (danh sách trang loại trừ, tên hàm/collection, phân loại câu hỏi, phiên bản thư viện, độ dài chunk, số liệu thời gian không có trong artifact) đã được sửa theo dữ liệu thật. Không có số liệu kết quả nào được thay đổi.
- **Cách kiểm tra kết quả:**
  - Kiểm tra tự động 20/20 `evidence_quote` là chuỗi con của văn bản đã chuẩn hóa trên đúng `gold_page`.
  - Đối chiếu Hit@1 / Evidence Hit@3 trong báo cáo, `README.md` và `artifacts/experiment_log.csv` với `results/traces_all.json` và `results/metrics_summary.json`.
  - Nhãn Coherence / Metadata / Grounding trong `results/manual_audit.json`: AI hỗ trợ trích chunk và soạn lý do cho từng vị trí/câu; học viên đọc lại chunk gốc trong `results/coherence_samples_raw.json` và `results/traces_all.json` rồi duyệt điểm từng nhãn theo thang 0–2 của `GUIDE.md`. Không dùng LLM judge tự động để ra điểm. Người chấm là tác giả bài, nên có nguy cơ thiên lệch như đã nêu ở mục Hạn chế.
