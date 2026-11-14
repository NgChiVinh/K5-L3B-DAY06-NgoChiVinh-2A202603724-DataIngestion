# Bảng Kiểm toán Thủ công (Manual Audit Tables) — Day 06 · Data Ingestion Engineering

- **Sinh viên:** Ngô Chí Vĩnh (`2A202603724`) — Lớp `L3B`
- **Tài liệu nguồn:** `wb-diem-lai-2024-08` (*Báo cáo Điểm lại Tháng 8/2024: Vươn tới tầm cao mới trên thị trường vốn*, Ngân hàng Thế giới tại Việt Nam)
- **File dữ liệu JSON đi kèm:** `results/manual_audit.json`, `results/coherence_samples_raw.json`, `results/traces_all.json`

---

## 1. Chunk Coherence Audit (10 vị trí cố định `pos_13`–`pos_23`, thang điểm `0–2`)

**Quy ước chấm điểm (`BENCHMARK.md`):**
- `2`: Chunk giữ nguyên ý trọn vẹn, không cắt ngang câu/bảng/code, đủ ngữ cảnh đọc độc lập.
- `1`: Chunk đọc hiểu được nhưng bị cắt nhẹ ở đầu/cuối hoặc thiếu một phần ngữ cảnh phụ.
- `0`: Chunk cắt vụn câu/bảng/code, trộn hai mục không liên quan, hoặc không thể hiểu nếu không mở file gốc.

| Sample ID | Trang | Section | Chủ đề / Vị trí đối chiếu | Điểm A | Điểm B | Điểm C | Nhận xét đối chiếu cụ thể theo Chunk ID |
| :--- | :---: | :--- | :--- | :---: | :---: | :---: | :--- |
| `pos_13` | 13 | `tong_quan` | Tăng trưởng GDP 6,4% H1/2024, động lực xuất nhập khẩu và dịch vụ | **1** | **2** | **2** | **A:** `p13__c001`..`c007` dính running header đầu trang và cắt ngang từ ở mốc 500 ký tự (`"tăng lần l"` / `"nh hơn"`, `"đạt m"` / `"h dịch vụ"`, `"phục"` / `"ho bãi"`). **B & C:** `p13__c001`..`c004` đã lọc sạch header, giữ nguyên 4 đoạn văn trọn câu (759–864 ký tự). |
| `pos_14` | 14 | `tong_quan` | Cán cân thanh toán quốc tế, tỷ giá VND/USD, nhu cầu vàng & can thiệp của NHNN | **1** | **2** | **2** | **A:** `p14__c002`..`c007` cắt ngang từ tại nhiều vị trí (`"xuất khẩu hàng h"` / `"ới 8,7%"`, `"bao"` / `"g phi chính thức"`). **B & C:** `p14__c002`..`c005` bảo toàn trọn vẹn từng đoạn phân tích vĩ mô (khoản mục "Lỗi và sai sót" nằm gọn trong `c004`, biện pháp NHNN nằm gọn trong `c005`). |
| `pos_15` | 15 | `tong_quan` | Tín dụng (+13,5%), nợ xấu ngân hàng (SCB, VAMC), trái phiếu DN, ngân sách & lạm phát | **1** | **2** | **2** | **A:** Cắt ngang từ ở mọi điểm nối (`"được c"` / `"ộng sản"`, `"27 ngân hàng t"` / `"o Q1-2024"`) và trộn cuối mục trái phiếu DN với đầu mục ngân sách ở `p15__c006`. **B & C:** Tách chuẩn xác thành 4 đoạn theo đúng 4 chủ đề (`p15__c001`..`c004`). |
| `pos_16` | 16 | `tong_quan` | Giải ngân đầu tư công, triển vọng 2024–2026 & **Bảng 0.1** (Một số chỉ số kinh tế) | **0** | **1** | **1** | **A:** `p16__c006`, `c007` và `c008` (51 ký tự) cắt vụn Bảng 0.1 làm tách rời dãy số dự báo khỏi tên chỉ tiêu và tiêu đề năm; không thể hiểu nếu không mở PDF gốc. **B & C:** Giữ trọn 3 đoạn văn xuôi (`c001`..`c003`) và gom toàn bộ Bảng 0.1 vào `p16__c004` (640 ký tự), nhưng do `pypdf` đọc tuyến tính nên dãy số xếp trước danh sách tên chỉ tiêu. |
| `pos_17` | 17 | `tong_quan` | Rủi ro/cơ hội tăng trưởng kinh tế & tổng quan 3 chức năng thị trường vốn | **1** | **2** | **2** | **A:** Chia đôi câu số liệu tiết kiệm của nhà đầu tư tổ chức giữa `p17__c007` (`"...chỉ đ"`) và `p17__c008` (`"uy động qua các nhà đầu tư tổ chức còn thấp, chỉ đạt 19% GDP"`). **B & C:** Giữ nguyên vẹn 4 đoạn lập luận lớn (`p17__c001`..`c004`). |
| `pos_18` | 18 | `tong_quan` | Cơ sở nhà đầu tư tổ chức và vai trò đa dạng hóa danh mục của Quỹ BHXH | **1** | **2** | **2** | **A:** `p18__c001`..`c009` liên tục cắt ngang chữ (`"một ng"` / `"n dụng"`, `"doanh n"` / `"ếu"`), xé lẻ luận điểm về danh mục 10% GDP của BHXH qua 3 chunk `c003`..`c005`. **B & C:** Chia đúng 5 đoạn văn hoàn chỉnh (`p18__c001`..`c005`, 636–882 ký tự). |
| `pos_20` | 20 | `chuong_1_kinh_te_vi_mo` | Mở đầu Chương 1 (Diễn biến kinh tế gần đây) kèm biểu đồ **Hình 1.1 & Hình 1.2** | **0** | **1** | **1** | **A:** `p20__c004` trộn nửa câu văn dịch vụ với tiêu đề Hình 1.1; `c005`..`c006` là chuỗi trục số biểu đồ song ngữ bị cắt ngang tiêu đề (`"Đóng góp củ"` / `"o trở thành"`). **B & C:** Tách bạch 2 đoạn văn xuôi (`c001`, `c002`) khỏi 2 khối biểu đồ (`c003`, `c004`), nhưng bản thân chunk biểu đồ vẫn chứa nhãn trục số rời rạc từ PDF. |
| `pos_21` | 21 | `chuong_1_kinh_te_vi_mo` | Đầu tư tư nhân (+3,9%), FDI (+13%), đầu tư công (+4%) & **Hình 1.3 – Hình 1.4** | **0** | **1** | **1** | **A:** Trộn chú thích đầu trang với câu vắt trang ở `c001`, cắt ngang số liệu ở `c002`..`c004` và băm nhãn trục biểu đồ thành 3 chunk nhiễu (`c005`..`c007`). **B & C:** Đoạn phân tích đầu tư nằm trọn vẹn trong `p21__c002` (975 ký tự); `c003`..`c004` còn dính nhãn trục số của Hình 1.3–1.4. |
| `pos_22` | 22 | `chuong_1_kinh_te_vi_mo` | Chi tiêu người tiêu dùng, doanh số bán lẻ (+8,8%) & **Hình 1.5 – Hình 1.8** | **0** | **1** | **1** | **A:** Trộn lời văn với hàng loạt dãy số trục biểu đồ Hình 1.5–1.8 bị cắt vụn từ `p22__c003` đến `c007` (`"ycles Vehicles Motorcycles 161 84 85..."`). **B & C:** Gom toàn bộ lời văn phân tích tiêu dùng vào duy nhất 1 chunk hoàn chỉnh `p22__c001` (878 ký tự), tách riêng phần nhãn biểu đồ sang `c002`..`c004`. |
| `pos_23` | 23 | `chuong_1_kinh_te_vi_mo` | Chỉ số sản xuất công nghiệp (`IPI = 166`), chỉ số `PMI = 55` & Hình 1.9 | **1** | **2** | **2** | **A:** Cắt đứt đôi câu bằng chứng về IPI và PMI ngay giữa `p23__c001` (`"...IPI lên đến 166 (+14,3%...). Chỉ số n"`) và `p23__c002` (`"...Chỉ số nhà quản trị mua hàng (PMI) cũng tăng mạnh, chạm mức 55"`), trực tiếp gây lỗi truy hồi ở câu `q02`. **B & C:** Giữ trọn toàn bộ đoạn phân tích IPI, PMI và các ngành điện tử, xăng dầu, kim loại trong 1 chunk `p23__c001` (954 ký tự). |
| **Tổng / Trung bình** | — | — | **10 vị trí đối chiếu (`pos_13`–`pos_23`)** | **`6/20` (`0.60/2`)** | **`16/20` (`1.60/2`)** | **`16/20` (`1.60/2`)** | **B & C cải thiện `+1.00` điểm/2 so với A nhờ cắt theo đoạn văn và lọc bỏ running header.** |

---

## 2. Metadata Usefulness Audit (`5 câu test × top-3 = 15 hits/chiến lược` & tuân thủ bộ lọc)

### 2.1. Kiểm tra tính đầy đủ và chính xác của Metadata trên `15` kết quả `test` (`q16`–`q20`)

| Question ID | Filter yêu cầu | Chiến lược A (`Top-3` Chunk IDs & Section) | Chiến lược B (`Top-3` Chunk IDs & Section) | Chiến lược C (`Top-3` Chunk IDs & Section) | Đủ 4 trường (`document_id`, `source`, `page`, `section`) & đúng PDF gốc? | Tuân thủ Filter (`A / B / C`) |
| :--- | :--- | :--- | :--- | :--- | :---: | :---: |
| `q16` | `null` | `p37__c003` (`chuong_1`), `p39__c008` (`chuong_2`), `p33__c002` (`chuong_1`) | `p37__c002` (`chuong_1`), `p39__c005` (`chuong_2`), `p16__c001` (`tong_quan`) | `p37__c002` (`chuong_1`), `p39__c005` (`chuong_2`), `p16__c001` (`tong_quan`) | **3/3** hợp lệ ở cả A, B, C | N/A |
| `q17` | `null` | `p46__c003` (`chuong_2`), `p47__c006` (`chuong_2`), `p46__c004` (`chuong_2`) | `p46__c002` (`chuong_2`), `p47__c003` (`chuong_2`), `p46__c001` (`chuong_2`) | `p46__c002` (`chuong_2`), `p47__c003` (`chuong_2`), `p46__c001` (`chuong_2`) | **3/3** hợp lệ ở cả A, B, C | N/A |
| `q18` | `null` | `p57__c002` (`chuong_2`), `p57__c003` (`chuong_2`), `p57__c001` (`chuong_2`) | `p57__c001` (`chuong_2`), `p57__c002` (`chuong_2`), `p42__c002` (`chuong_2`) | `p57__c001` (`chuong_2`), `p57__c002` (`chuong_2`), `p42__c002` (`chuong_2`) | **3/3** hợp lệ ở cả A, B, C | N/A |
| `q19` | `section = "chuong_2_thi_truong_von"` | `p49__c003` (`chuong_2`), `p55__c005` (`chuong_2`), `p49__c007` (`chuong_2`) | `p49__c001` (`chuong_2`), `p49__c002` (`chuong_2`), `p49__c005` (`chuong_2`) | `p49__c001` (`chuong_2`), `p49__c002` (`chuong_2`), `p49__c005` (`chuong_2`) | **3/3** hợp lệ ở cả A, B, C | **Có / Có / Có** (`3/3` hits thuộc Chương 2) |
| `q20` | `section = "chuong_2_thi_truong_von"` | `p60__c004` (`chuong_2`), `p60__c005` (`chuong_2`), `p60__c006` (`chuong_2`) | `p60__c003` (`chuong_2`), `p60__c005` (`chuong_2`), `p60__c004` (`chuong_2`) | `p60__c003` (`chuong_2`), `p60__c005` (`chuong_2`), `p60__c004` (`chuong_2`) | **3/3** hợp lệ ở cả A, B, C | **Có / Có / Có** (`3/3` hits thuộc Chương 2) |
| **Tổng kết Test** | **2 câu có filter** | **`15/15 (100%)` metadata hợp lệ** | **`15/15 (100%)` metadata hợp lệ** | **`15/15 (100%)` metadata hợp lệ** | **`15/15 (100%)`** | **Test: `2/2` (`100%`)** |

### 2.2. Đối chiếu tỷ lệ tuân thủ điều kiện lọc (`Filter Compliance`) trên toàn bộ 6 câu có Filter (`4 dev` + `2 test`)

| Question ID | Split | Điều kiện lọc (`filter`) | Tuân thủ Top-3 ở Chiến lược A | Tuân thủ Top-3 ở Chiến lược B | Tuân thủ Top-3 ở Chiến lược C | Phân tích tác động thực tế |
| :--- | :---: | :--- | :---: | :---: | :---: | :--- |
| `q12` | `dev` | `section = "chuong_1_kinh_te_vi_mo"` | **Không** (Rank 2 là `p15__c005` thuộc `tong_quan`) | **Không** (Rank 2 là `p15__c003` thuộc `tong_quan`, Rank 3 là `p47__c001` thuộc `chuong_2`) | **Có (`3/3`)** (`p31__c002`, `p32__c002`, `p32__c004`) | Lọc bỏ bản tóm tắt ở trang 15 và chương 2 ở trang 47, giữ lại thuần túy phân tích chuyên sâu Chương 1. |
| `q13` | `dev` | `section = "chuong_1_kinh_te_vi_mo"` | **Không** (Rank 3 là `p15__c007` thuộc `tong_quan`) | **Không** (Rank 2 là `p15__c004` thuộc `tong_quan`) | **Có (`3/3`)** (`p32__c003`, `p35__c004`, `p32__c004`) | Lọc bỏ đoạn tóm tắt lạm phát ở trang 15 (`tong_quan`), chỉ lấy số liệu chi tiết của Chương 1. |
| `q14` | `dev` | `section = "chuong_2_thi_truong_von"` | **Có (`3/3`)** | **Có (`3/3`)** | **Có (`3/3`)** | Chủ đề thông lệ công bố thông tin và chuẩn IFRS chỉ xuất hiện ở Chương 2. |
| `q15` | `dev` | `section = "tong_quan"` | **Không** (Rank 2 & 3 là `p28__c003`, `p28__c004` thuộc `chuong_1`) | **Không — Sai Top-1!** (Rank 1 là `p28__c002` thuộc `chuong_1`, score `0.8033` > Rank 2 `p14__c003` score `0.8031`) | **Có (`3/3`) — Đúng Top-1!** (Rank 1 là `p14__c003` thuộc `tong_quan`, score `0.8031`) | **Ví dụ điển hình chứng minh giá trị của Chiến lược C:** Trang 28 (`chuong_1`) nêu tỷ giá cuối tháng 3/2024 (`24.760 VND`), trong khi trang 14 (`tong_quan`) nêu tỷ giá cuối tháng 6/2024 (`25.334 VND`). Không có filter, Chiến lược B trả về sai số liệu ở Rank 1; Chiến lược C lọc `section="tong_quan"` nên loại bỏ `p28__c002` và đưa `p14__c003` lên Rank 1. |
| `q19` | `test` | `section = "chuong_2_thi_truong_von"` | **Có (`3/3`)** | **Có (`3/3`)** | **Có (`3/3`)** | Từ khóa `HOSE`, `HNX`, `IPO` đặc thù cho Chương 2; Chiến lược C đảm bảo cứng bằng bộ lọc Qdrant. |
| `q20` | `test` | `section = "chuong_2_thi_truong_von"` | **Có (`3/3`)** | **Có (`3/3`)** | **Có (`3/3`)** | Từ khóa `BHXH`, `bảo hiểm nhân thọ`, `2030` tập trung tại trang 60 thuộc Chương 2. |
| **Tổng cộng** | **6 câu** | **Dev (`4`) + Test (`2`)** | **Dev: `1/4 (25%)` \| Test: `2/2 (100%)` \| Tổng: `3/6 (50%)`** | **Dev: `1/4 (25%)` \| Test: `2/2 (100%)` \| Tổng: `3/6 (50%)`** | **Dev: `4/4 (100%)` \| Test: `2/2 (100%)` \| Tổng: `6/6 (100%)`** | **Chiến lược C đạt 100% tuân thủ điều kiện lọc trên cả Dev và Test.** |

---

## 3. Grounding Quality Audit (`5 câu test q16–q20`, thang điểm `0–2`)

**Quy ước chấm điểm (`BENCHMARK.md`):**
- `2`: Top-3 chứa đủ bằng chứng để trả lời đúng và truy ngược được nguồn (`document_id`, `page` hoặc `section`).
- `1`: Top-3 có thông tin liên quan nhưng thiếu một phần điều kiện hoặc phải ghép nhiều mảnh chưa thật chắc chắn.
- `0`: Top-3 không đủ thông tin để trả lời có căn cứ.

| Question ID | Loại câu hỏi | Trang chuẩn | Điểm A | Điểm B | Điểm C | Giải thích chi tiết dựa trên Top-3 kết quả truy hồi |
| :--- | :--- | :---: | :---: | :---: | :---: | :--- |
| `q16` | Trực tiếp | `37` | **2** | **2** | **2** | Cả 3 chiến lược đều đưa chunk chứa nguyên vẹn câu bằng chứng *"Chỉ cần tăng đầu tư công thêm một điểm phần trăm so GDP có thể khiến cho GDP tăng thêm 0,1 phần trăm"* lên **Rank 1** (`p37__c003` ở A; `p37__c002` ở B và C) kèm đầy đủ metadata trang 37. |
| `q17` | Điều kiện / ngoại lệ | `46` | **1** | **2** | **2** | **A (`1/2`):** Rank 1 (`p46__c003`) chứa tỷ lệ 20% đợt đấu thầu bị từ chối nhưng bị cắt đứt giữa câu kết luận ở ký tự 500 (*"...biến dạng cho chức năng định giá của thị trường trái phiếu"*), phần đuôi rơi sang Rank 3 (`p46__c004`). **B & C (`2/2`):** Rank 1 (`p46__c002`) bảo toàn 100% đoạn văn trong một chunk duy nhất. |
| `q18` | Diễn đạt lại | `57` | **2** | **2** | **2** | Cả 3 chiến lược đều xếp đoạn mô tả vai trò lưu ký tập trung của **VSDC** và sự khác biệt thanh toán giữa trái phiếu chính phủ (qua **NHNN**) với chứng khoán doanh nghiệp (qua **NHTM Nhà nước**) ở **Rank 1** (`p57__c002` ở A; `p57__c001` ở B và C). |
| `q19` | Metadata filter (`chuong_2_thi_truong_von`) | `49` | **1** | **1** | **1** | **A (`1/2`):** Rank 1 (`p49__c003`) chỉ có thông tin 3 đợt IPO năm 2023 (173 tỷ đồng), làm mất hoàn toàn vế đầu về huy động vốn bình quân 5 năm trên HOSE & HNX (`37 ngàn tỷ đồng / 1,5 tỷ USD`, nằm ở `p49__c002` ngoài Top-3), trong khi Rank 3 (`p49__c007`) lại nêu số liệu của sàn UPCOM (`32 ngàn tỷ đồng`) dễ gây râu ông nọ cắm cằm bà kia. **B & C (`1/2`):** Top-3 lấy được **đầy đủ cả 2 vế** nhưng nằm tách ở 2 chunk liên tiếp: Rank 1 (`p49__c001`) chứa mức bình quân `37 ngàn tỷ đồng`, còn câu cuối về 3 đợt IPO năm 2023 (`173 tỷ đồng`) bị tách sang Rank 2 (`p49__c002`) do đoạn gốc vượt ngưỡng `max_size=1000`. Chấm `1/2` trung thực theo quy tắc phải ghép 2 mảnh. |
| `q20` | Metadata filter (`chuong_2_thi_truong_von`) | `60` | **1** | **2** | **2** | **A (`1/2`):** Rank 1 (`p60__c004`) chứa số liệu của BHXH (`20 tỷ USD`) và bảo hiểm nhân thọ (`15 tỷ USD`) nhưng bị cắt cứng ở chữ *"Các quỹ đầu tư và quỹ hưu trí tư nhân tăng tr"*; con số `14 tỷ USD` rơi sang Rank 2 (`p60__c005`). **B & C (`2/2`):** Rank 1 (`p60__c003`) giữ nguyên vẹn cả 3 con số (`20 tỷ`, `15 tỷ`, `14 tỷ USD`) trong 1 chunk duy nhất, kèm chú thích giả định ở Rank 2 và Rank 3. |
| **Tổng / Trung bình** | **5 câu `test` (`q16`–`q20`)** | — | **`7/10` (`1.40/2`)** | **`9/10` (`1.80/2`)** | **`9/10` (`1.80/2`)** | **B và C nâng Grounding Quality từ `1.40/2` lên `1.80/2` nhờ loại bỏ hiện tượng cắt ngang câu ở `q17` và `q20`.** |

