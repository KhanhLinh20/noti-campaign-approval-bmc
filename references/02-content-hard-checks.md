# 02 — Content Hard Checks
## Noti Campaign Agent — Group Nhóm 2

> **Phiên bản:** v1.19 — 06/2026 (add Rule 2.14 brand integrity — tên "MoMo" phải viết đúng, hard block)
> **Scope:** Rules 2.1 – 2.14 (Title/Body length, PII, format violations, banned phrases, image advisory, gift card reminder duplicate risk, brand integrity)
> **Load:** Always (Phase 0 mandatory)
> **Script coverage:** Đa số rules (2.1, 2.2, 2.3, 2.4, 2.6, 2.8, 2.10, 2.11, 2.12, 2.13, 2.14) đã implement trong `scripts/tier1_check.py` — KHÔNG dùng LLM.

---

## Nhóm 2 — Content Hard Checks

### Rule 2.1 — Title tối đa 30 ký tự
- **Tier:** 🔴 Script
- **Trigger:** Agent nhập title
- **Logic:** `len(title sau khi strip placeholder) > 30` → block. Áp dụng cho cả Business role và Platform role (Platform role UI có thể extend nhưng agent vẫn block để đảm bảo content quality).
- **Error message:** `"Title đang có [N] ký tự — vượt giới hạn 30 ký tự. Vui lòng rút gọn."`
- **Implementation note:** Đếm theo số ký tự Unicode (emoji = 1 ký tự). Placeholder `${lastname}`, `${fullname}` = **0 ký tự** (strip trước khi đếm). Athena LƯU/trả template string còn nguyên `${...}` và chỉ render lúc gửi, nên **không** reverse-substitute — chỉ strip `${...}` rồi `len()`.
- **⛔ CẤM render fallback rồi cộng ký tự:** TUYỆT ĐỐI KHÔNG thay `${lastname}`/`${fullname}` bằng giá trị fallback (VD `"bạn"`) rồi cộng độ dài fallback đó vào số ký tự. Placeholder LUÔN = 0 ký tự, không quan tâm fallback là gì. *Anti-pattern:* body `"... Đừng để lỡ ${lastname} nhé!"` đúng = **83** (strip `${lastname}`); render thành `"... bạn nhé!"` rồi tính 86 (cộng 3 ký tự của "bạn") là **SAI**. Fallback `"bạn"` chỉ dùng cho render lúc GỬI THẬT (xem `survey-cio.md` §7), KHÔNG bao giờ dùng để đếm.
- **⛔ CẤM tự đếm bằng mắt (v1.11.3):** Số ký tự title/body PHẢI lấy VERBATIM từ `tier1_check.py` stdout (`metadata.title_len` / `metadata.body_len`). **TUYỆT ĐỐI KHÔNG** để LLM tự đếm — LLM đếm sai ký tự tiếng Việt có dấu + khoảng trắng, và hay tự "thu gọn" khoảng trắng đôi để lại sau khi strip placeholder. *Anti-pattern thực tế:* title `"Nhìn lại tháng 6 của ${lastname}"` đúng = **21**, body `"Tháng qua ${lastname} đã chi bao nhiêu?"` đúng = **28** (còn khoảng trắng đôi ở chỗ placeholder) — model tự đếm ra 22/26 là SAI. **Nếu chưa/không chạy được `tier1_check.py`** → ghi "⚠️ chưa verify (chưa chạy script)", KHÔNG được đoán một con số.

---

### Rule 2.2 — Body tối đa 120 ký tự
- **Tier:** 🔴 Script
- **Trigger:** Agent nhập body
- **Logic:** `len(body sau khi strip placeholder) > 120` → block. Tương tự rule 2.1, áp dụng cả Platform role.
- **Error message:** `"Body đang có [N] ký tự — vượt giới hạn 120 ký tự. Vui lòng rút gọn."`
- **Implementation note:** Placeholder `${lastname}`, `${fullname}` = **0 ký tự** (strip trước khi đếm). Không reverse-substitute (xem rule 2.1).
- **⛔ CẤM render fallback rồi cộng ký tự:** KHÔNG thay `${lastname}`/`${fullname}` bằng fallback (`"bạn"`) rồi cộng độ dài vào count. Placeholder = 0 ký tự tuyệt đối. Fallback chỉ cho render lúc gửi thật, KHÔNG dùng để đếm (xem rule 2.1).

---

### Rule 2.3 — Body không ngắt xuống dòng
- **Tier:** 🔴 Script
- **Trigger:** Agent nhập body
- **Logic:** Detect ký tự `\n`, `\r\n`, bullet character (`•`, `-`, `*` đầu dòng) trong body → block.
- **Error message:** `"Body không được ngắt câu xuống dòng hoặc dùng bullet. Vui lòng viết liền mạch."`

---

### Rule 2.4 — PII: Không chứa thông tin cá nhân nhận dạng
- **Tier:** 🔴 Script (Regex)
- **Trigger:** Agent nhập title hoặc body
- **Logic:** Regex scan các pattern sau trong title + body:
  - Số điện thoại: `(84|0)\d{9,10}`
  - Email: `\S+@\S+\.\S+`
  - CCCD/CMND: `\b\d{9}\b` hoặc `\b\d{12}\b`
  - Số tài khoản ngân hàng: chuỗi 9–14 chữ số liên tiếp (context-aware: loại trừ số tiền có đơn vị kèm theo)
- **Error message:** `"Phát hiện thông tin cá nhân ([loại]) trong nội dung. Vui lòng xoá trước khi tiếp tục."`
- **Lộ trình:** Khi MoMo triển khai Presidio → thay thế regex bằng Presidio scan.

---

### Rule 2.6 — Param (biến) phải đúng format và nằm trong danh sách cho phép
- **Tier:** 🔴 Script
- **Trigger:** Agent nhập title hoặc body có chứa ký tự `$` hoặc `{`
- **Logic:**
  - Detect tất cả pattern dạng `${...}` trong title và body
  - **Noti Campaign chỉ chấp nhận 2 biến:** `${fullname}`, `${lastname}` — tất cả các biến khác (firstname, phone, amount, email, city…) KHÔNG cho phép
  - Biến không thuộc whitelist → block
  - Biến sai chính tả hoặc sai case (VD: `${Lastname}`, `${ lastname }`) → block, gợi ý đúng
- **Error message (biến không hợp lệ):** `"Biến '[X]' không được phép trong Noti Campaign. Whitelist: \${fullname}, \${lastname}."`
- **Error message (sai chính tả):** `"Biến '[X]' không đúng format. Kiểm tra lại tên biến và đảm bảo không có khoảng trắng bên trong."`
- **Implementation note:** Regex: `\$\{\s*\w+\s*\}` — extract tất cả biến, so sánh case-sensitive với whitelist `["fullname", "lastname"]`. Khoảng trắng bên trong braces → invalid.

---

### Rule 2.7 — Group Quan trọng: format violation → HITL thay vì REJECT
- **Tier:** 🔵 HITL
- **Trigger:** Campaign có `group = Quan trọng` (content_type IN `TRANSACTION`, `REMIND`, `WARNING`, `SERVICE`) + phát hiện vi phạm format ở Rule 2.1, 2.2, 2.3, 2.6
- **Logic:** Nội dung Quan trọng (giao dịch, nhắc nhở, cảnh báo, dịch vụ) không nên bị auto-block — user cần nhận thông tin này dù format chưa hoàn hảo. Thay vì REJECT, route HITL để reviewer (PCS) sửa và approve thủ công.
  - Format violations áp dụng → HITL: Rule 2.1 (title dài), Rule 2.2 (body dài), Rule 2.3 (newline/bullet), Rule 2.6 (param sai)
  - **Ngoại lệ:** PII (Rule 2.4) vẫn là REJECT cho MỌI content_type — data privacy không negotiate được
- **HITL priority order (v2.5+ — check top-down, match là dừng):**
  1. **HITL-trigger:** DIM-3.4b typo / DIM-3.7 misleading offer / DIM-3.9 sensitive action / DIM-4.4 Vietlott financial / DIM-4.5 Vietlott promo → HITL_REQUIRED
  2. **Regulatory floor:** DIM-1.6 (CT semantic) / 4.1 / 4.2 / 4.3 / 4.6 / 4.7 / 4.8 / 4.9 có `sub_score ≤ 25` → HITL_REQUIRED bất kể overall score (danh sách chuẩn = `REG_FLOOR_DIMS` trong `07-llm-judge-core_v1.12.md`)
  3. **Quan trọng HITL exception (rule này):** format violations Rule 2.1/2.2/2.3/2.6 + group Quan trọng → HITL_REQUIRED
  4. **Score thresholds:** REJECT < 50 · WARNING/HITL 50-84 · APPROVED ≥ 85
- **Hành động:** Route đến PCS, kèm danh sách format issues cần sửa trước khi approve
- **Error message:** `"[Format issues] — Nội dung Quan trọng không thể auto-reject. Route HITL (PCS) để reviewer xem xét và sửa trước khi approve."`

---

### Rule 2.8 — Block test/placeholder content
- **Tier:** 🔴 Script
- **Trigger:** Agent submit campaign với title/body
- **Logic:** Detect các heuristics chỉ dấu test/placeholder content — BLOCK submit (không phải HITL, vì đây rõ ràng là lỗi operational):
  1. **Chuỗi lặp đơn giản:** title hoặc body là sequence chữ lặp (`ggg`, `hhh`, `ff`, `fff`, `aaa`), hoặc số đơn thuần (`123`, `12345`), hoặc độ dài ≤ 3 ký tự
  2. **Keyword test:** title hoặc body chứa (case-insensitive) `test`, `qc`, `check`, `demo`, `debug`, `abc`, `xyz`, `dummy`, `sample` — không đi kèm context nghiệp vụ
  3. **Low entropy:** Shannon entropy body < 1.5 bit/char (body toàn ký tự giống nhau)
  4. **Segment name red flag:** segment chứa `_test_`, `_qc_`, `_check_`, `_demo_`, `_debug_`, hoặc `__` (double underscore) — cờ cảnh báo thêm
- **Error message:** `"Nội dung có dấu hiệu test/placeholder (chi tiết: [lý do cụ thể]). Sử dụng môi trường UAT/Dev với token cá nhân để test thay vì submit production queue. Nếu đây là nội dung thật, vui lòng viết rõ ràng hơn."`
- **Implementation note:** 
```python
TEST_KEYWORDS = {"test", "qc", "check", "demo", "debug", "abc", "xyz", "dummy", "sample"}
REPETITION_PATTERN = r"^(.)\1{2,}$"  # 3+ ký tự lặp
SHORT_CONTENT_THRESHOLD = 3
```
- **Ngoại lệ:** Nội dung có từ `test` trong context nghiệp vụ (VD: "Test nhanh tính năng mới") không bị block — chỉ flag nếu toàn bộ nội dung là test keyword.

---

### Rule 2.9 — Duplicate content detection
- **Tier:** 🟡 LLM + 🔴 Script
- **Trigger:** Agent submit campaign, hoặc batch review mode scan nhiều campaign IN_REVIEW
- **Logic 2-tier:**
  1. **Same content + same segment (Script):** Nếu title + body đã submit cho cùng segment trong 7 ngày gần nhất → **BLOCK** (duplicate submit lỗi operational)
     - Error: `"Nội dung này đã được submit cho segment '[X]' trong 7 ngày qua. Nếu là chủ ý resubmit, vui lòng liên hệ Platform."`
  2. **Same content + different segment (LLM flag — KHÔNG block):** Nếu có ≥ 2 campaign trong batch cùng title+body nhưng khác segment → **FLAG informational** cho approver (không block vì đây là pattern Growth chia segment hợp lệ)
     - Flag message: `"💡 Content trùng với [N] campaign khác trong batch (segment khác nhau). Đây có thể là multi-segment split hợp lệ — approver có thể duyệt đồng loạt."`
- **Implementation note:**
  - Script check: hash (title + body) + segment → lookup 7-day history
  - LLM batch check: tính similarity score (cosine / Jaccard) ≥ 90% = "same content"
  - **Không block** case 2 — vì Growth hợp pháp chia nhỏ segment để A/B test content

---

### Rule 2.11 — Banned phrases scan (Legal/Compliance blacklist)
- **Tier:** 🔴 Script + 🟠 Reg-floor + 🟡 LLM (severity-aware)
- **Trigger:** Phase 2 review title+body — scan against external blacklist file
- **Source file:** `assets/banned-phrases.json` (Legal/Compliance maintain, sync monthly). Mỗi phrase có `pattern` + `severity` (blocker/critical/warning) + `reason` + optional `carve_out`.
- **Logic theo severity:**
  - `severity: "blocker"` → 🔴 Tier A hard block → NOT_QUALIFIED (vi phạm Luật Quảng cáo VN / NHNN, không thể override)
  - `severity: "critical"` → 🟠 Tier C Reg-floor → HITL_REQUIRED (force HITL bất kể overall score; approver verify carve-out nếu có)
  - `severity: "warning"` → 🟡 Tier 2 LLM score deduction (-15 đến -25 depending on context)
- **Match logic:** Substring match case-insensitive, Vietnamese diacritics aware. KHÔNG cần whole-word boundary — phrase phải đủ đặc trưng (Legal đảm bảo khi maintain file).
- **Carve-out:** Một số phrase có exception (vd "đảm bảo trúng" OK nếu kèm cơ chế game). Khi match phrase có `carve_out`, escalate lên HITL thay vì auto-block — approver xác nhận context.
- **Lookup pattern (Phase 2):**
  ```bash
  # Pseudo-code: scan content vs phrases array
  jq -r '.phrases[] | "\(.pattern)\t\(.severity)"' assets/banned-phrases.json | \
    while IFS=$'\t' read pattern sev; do
      if echo "<title+body>" | grep -qi "$pattern"; then
        echo "MATCH: $pattern → $sev"
      fi
    done
  ```
- **Error message (blocker):** `"Phát hiện cụm từ '[X]' nằm trong danh sách Legal/Compliance cấm. Lý do: [reason]. Owner sửa nội dung và resubmit."`
- **HITL message (critical):** `"Phát hiện cụm '[X]' (severity: critical). Approver xác nhận có thuộc carve-out không, hoặc reject để owner sửa."`
- **Tag (Phase 5 structured log):** `banned_phrase_blocker` / `banned_phrase_critical` / `banned_phrase_warning` — add vào Common tag dictionary
- **Update procedure:** Legal team add phrase mới qua PR vào `banned-phrases.json`, KHÔNG cần thay code skill. Bump `_version` field khi update. Skill load on-demand.
- **Implementation note:** Skill **KHÔNG** preload file trong Phase 0 (~3KB nhưng rarely change) — Phase 2 load on-demand khi scan từng campaign. Cross-reference với Rule 3.7 (promotional claim) — Rule 2.11 là layer trên cùng (hard block từ Legal), Rule 3.7 là Tier 2 LLM (advisory + game carve-out).

---

### Rule 2.12 — Image out-app advisory (v1.17+)
- **Tier:** ⚪ Advisory (KHÔNG hard block, KHÔNG degrade score)
- **Trigger:** Campaign có `extra.image_url` không rỗng AND `notification_config.allow_out_app = true`
- **Logic:** Emit advisory tag `image_outapp_review` → Phase 3 batch report hiển thị cột "🖼 Ảnh" với markdown link clickable. Approver bắt buộc visual review hình trước khi APPROVE.
- **Lý do (problem statement):** Icon nhỏ (vd 600×400) có thể bị iOS render full screen ở out-app push notification → ảnh stretch / dominate notification, gây UX lỗi. Phân tích URL pattern KHÔNG đủ catch — cần human visual check.
- **KHÔNG block:** Verdict không degrade. Approver tự quyết sau khi xem link.
- **Advisory message:** `"Có hình ảnh out-app — click link review trước khi duyệt: [image_url]"`
- **Tag (Phase 5 structured log):** `image_outapp_review`
- **Phase 4 confirm panel:** Highlight advisory + clickable link. Approver phải xem trước khi chọn APPROVE.
- **Implementation note:** `scripts/rules.py::rule_2_12_image_outapp_advisory()` deterministic. Output JSON thêm field `advisories[]` (separate khỏi `issues[]` để Phase 3 render riêng).

---

### Rule 2.13 — Gift card reminder pattern detection (v1.18+)
- **Tier:** 🔵 HITL trigger (KHÔNG hard block, KHÔNG degrade score) — force human review
- **Apply when:** ANY content_type (KHÔNG limit REMIND only) — pattern này có thể xuất hiện ở mọi CT khi BU dùng sai routing
- **Trigger:** AND 3 signals — all phải match
  - **Signal 1 (remind language):** title + body chứa từ "bạn còn" / "đã sẵn sàng" / "thu thập ngay" / "đừng quên" / "chưa dùng" / "sắp hết" / ... (xem `GIFT_REMIND_PATTERNS` trong `scripts/constants.py`)
  - **Signal 2 (gift/voucher keywords):** title + body chứa từ "thẻ quà" / "voucher" / "quà sinh nhật" / "đặc quyền" / "gói thành viên" / ... (xem `GIFT_KEYWORDS`)
  - **Signal 3 (ref_id voucher page):** `ref_id` ∈ `{voucher_detail, gift_detail, my_vouchers, my_rewards, membership_benefit, voucher_list, ...}` (xem `REFID_VOUCHER_PATTERNS`)
- **Lý do thiết kế:** ML Promotion side đã có cơ chế remind tự động cho voucher/thẻ quà sắp hết hạn. Noti Campaign side gửi thêm = duplication / over-notification → user fatigue + Rule 5.2 BU daily cap risk.
- **Routing rule:** **FOLLOW CT default** (KHÔNG override):
  - `CT=REMIND` (Quan trọng) → HITL → **PCS**
  - `CT=PROMOTION*` / `GAME` / `ADVERTISING` / `EVENT` (Ưu đãi) → HITL → **BMC** bất kể score
  - `CT=FRIENDS` / `BUSINESS_PAGE` / `SOCIAL` (Tương tác) → HITL → BMC
  - `CT=SURVEY` → KHÔNG applicable (SURVEY có rule routing riêng — Rule 6.5)
- **Force HITL bất kể score Tier 2:** Khi pattern match, override score gate (vd score ≥ 85 vẫn HITL).
- **HITL message cho approver:** `"Pattern phát hiện: Nội dung có chứa remind voucher, cần human review"` (natural VN, không show số rule per Principle #8)
- **BMC/PCS review checklist:**
  1. Verify với ML Promotion team — có duplicate remind không
  2. Nếu duplicate → reject hoặc yêu cầu Growth coordinate timing
  3. Nếu không duplicate → approve + note trong comment
- **Tag (Phase 5 structured log):** `gift_card_reminder_duplicate_risk`
- **False positive mitigation:** AND 3 signals đồng thời = high precision. Test scenarios:
  - ✅ Match: "Bạn còn Quà sinh nhật... Voucher đã sẵn sàng. Thu thập ngay!" + ref_id=voucher_detail
  - ✅ Pass: "Hoàn 50% khi thanh toán QR" + ref_id=my_qrcode (PROMOTION new offer, không có signal 1 + 3)
  - ✅ Pass: "Bảo trì hệ thống 22h-23h" + ref_id=maintenance (REMIND service, không có signal 2 + 3)
  - ✅ Pass: "Voucher mới có sẵn" + ref_id=voucher_detail (không có signal 1 — remind language)
- **Implementation note:** `scripts/rules.py::rule_2_13_gift_card_reminder_advisory()` deterministic Tier 1 keyword scan. Constants ở `scripts/constants.py` (3 sets: GIFT_REMIND_PATTERNS, GIFT_KEYWORDS, REFID_VOUCHER_PATTERNS) — extend khi pattern mới emerge.

---

### Rule 2.14 — Brand integrity: tên "MoMo" phải viết đúng (v1.19+)
- **Tier:** 🔴 Script (deterministic) — và LLM tự enforce khi chạy không có script (vd Athena Copilot)
- **Trigger:** Scan title + body
- **Logic:** Brand **"MoMo"** CHỈ có 1 cách viết đúng: `MoMo` (camelCase — M hoa, o thường, M hoa, o thường; **không dấu, không khoảng trắng**). Mọi biến thể khác khi chỉ brand → **hard block NOT_QUALIFIED**:
  - ❌ `Mô Mô`, `Mo Mo` (tách chữ / có dấu mũ / có khoảng trắng)
  - ❌ `Momo` (chỉ hoa chữ đầu) · `MOMO` (all caps) · `momo` (all thường)
  - ❌ `mômô`, `MÔMÔ`, `Mô mô`, `mô mô` (mọi tổ hợp dấu)
  - ✅ Chỉ chấp nhận: `MoMo`
- **Match logic (deterministic):** regex case-insensitive `\bm[ôo]\s?m[ôo]\b` quét mọi token hình dạng "momo"; token nào KHÁC chính xác `MoMo` → block. Word-boundary tránh false positive (vd "homomorphic" không bị flag).
- **Error message:** `"Tên thương hiệu viết sai ('[X]'). Phải viết đúng 'MoMo' theo brand guideline. Owner sửa và resubmit."`
- **Severity:** 🔴 Hard block (NOT_QUALIFIED) — áp dụng **MỌI content_type & group**, KỂ CẢ Quan trọng (KHÔNG dùng ngoại lệ Rule 2.7). Brand integrity không khoan nhượng.
- **Lý do thiết kế:** Sai tên thương hiệu trên push gửi hàng triệu user = tổn hại brand integrity nghiêm trọng. Đây là check deterministic (1 cách viết đúng duy nhất) → đặt ở Tier 1 script, KHÔNG để Tier 2 LLM. Lý do: LLM coi "Mô Mô" là 2 âm tiếng Việt hợp lệ + whitelist brand (Rule 3.4b) khiến LLM bỏ qua — nên trước đây pattern này lọt.
- **Data source:** `assets/brand-dictionary.json` field `enforce[]` — content team thêm brand cần enforce (canonical + match_pattern) qua JSON, KHÔNG sửa code. Field `known_partner_brands[]` là whitelist brand đối tác KHÔNG flag chính tả (input cho Rule 3.4b).
- **Tag (Phase 5 structured log):** `brand_name_misspelled`
- **Implementation note:** `scripts/brand.py::check_rule_2_14()`. Fail-open: JSON missing/regex lỗi → stderr warning 1 lần + skip Rule 2.14 (giống Rule 2.11 / 1.8).
- **⚙️ LLM-mode (Copilot / no-script):** Khi skill chạy KHÔNG có Python (vd upload Athena Copilot), **LLM TỰ áp dụng rule này**: quét title+body, nếu thấy bất kỳ biến thể "MoMo" sai như list trên → verdict **NOT_QUALIFIED**. KHÔNG dựa vào whitelist brand của Rule 3.4b để bỏ qua (whitelist chỉ cho tên viết ĐÚNG).
- **Test scenarios:**
  - ❌ Block: "Đoán xem **Mô Mô** tặng bạn gì..." → NOT_QUALIFIED
  - ❌ Block: "**Momo** Day trở lại" / "**MOMO** giảm giá" / "**Mo Mo** tặng quà"
  - ✅ Pass: "**MoMo** Day trở lại, MoMo tặng deal giảm 1 triệu" (viết đúng)
  - ✅ Pass: "Mua sắm **Shopee** hoàn tiền qua **MoMo**" (đối tác đúng + brand đúng)

---

