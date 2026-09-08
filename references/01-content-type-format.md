# 01 — Content Type & Format Rules
## Noti Campaign Agent — Group Nhóm 1

> **Phiên bản:** v1.17 — 06/2026 (tighten Rule 1.6 axis 1 — explicit gift card reminder pattern HITL trigger, complement Rule 2.13 Tier 1 catch)
> **Scope:** Rules 1.1 – 1.8 (Content type validation, format constraint, RefID glossary)
> **Load:** Always (Phase 0 mandatory)

---

## Nhóm 1 — Content Type & Format

### Rule 1.1 — Content type hợp lệ cho Noti Campaign

- **Tier:** 🔴 Script
- **Trigger:** Agent propose bất kỳ campaign nào

**Logic theo mode:**

**Create mode (agent tạo mới):** Chỉ cho phép **5 content_type chính + 1 EVENT đặc biệt** — các CT khác (TRANSACTION, REMIND, PROMOTION, PROMOTION_OUTDATED, GAME, FRIENDS, BUSINESS_PAGE, SOCIAL) thuộc flow hệ thống/đối tác/SDK, KHÔNG phải Noti Campaign do Growth/Agent tạo:

| Group | Content Type VN | API code | Approver | Ghi chú agent-create |
|---|---|---|---|---|
| Quan trọng | Cảnh báo | `WARNING` | **PCS** | Cho phép |
| Quan trọng | Dịch vụ | `SERVICE` | **PCS** | Cho phép |
| Ưu đãi | Khuyến mãi dịch vụ | `PROMOTION_SERVICE` | BMC | Cho phép |
| Ưu đãi | Quảng cáo | `ADVERTISING` | BMC | Cho phép |
| Ưu đãi | Sự kiện đặc biệt | `EVENT` | BMC | **Chỉ thematic campaign** — xem Rule 1.7 |
| Tương tác | Khảo sát | `SURVEY` | **CIO** | Cho phép (routing riêng — xem Rule 1.5 + 6.5) |

**Review mode (agent duyệt):** Vẫn accept full 14 CT codes (vì campaign legacy có thể thuộc bất kỳ CT nào):

| Group (Tab UI) | Content Type VN | API code | Approver |
|---|---|---|---|
| Quan trọng | Giao dịch | `TRANSACTION` | **PCS** |
| Quan trọng | Nhắc nhở | `REMIND` | **PCS** |
| Quan trọng | Cảnh báo | `WARNING` | **PCS** |
| Quan trọng | Dịch vụ | `SERVICE` | **PCS** |
| Ưu đãi | Khuyến mãi (legacy) | `PROMOTION` | BMC |
| Ưu đãi | Khuyến mãi dịch vụ | `PROMOTION_SERVICE` | BMC |
| Ưu đãi | Khuyến mãi hết hạn | `PROMOTION_OUTDATED` | BMC |
| Ưu đãi | Game | `GAME` | BMC |
| Ưu đãi | Quảng cáo | `ADVERTISING` | BMC |
| Ưu đãi | Sự kiện | `EVENT` | BMC |
| Tương tác | Bạn bè | `FRIENDS` | BMC |
| Tương tác | Business Page | `BUSINESS_PAGE` | BMC |
| Tương tác | Social | `SOCIAL` | BMC |
| Tương tác | Khảo sát | `SURVEY` | **CIO** |

**Quy tắc vàng:**
- **Mọi content_type thuộc Group Quan trọng → PCS duyệt**, không ngoại lệ.
- Mọi content_type có prefix `PROMOTION*` (kể cả suffix mới phát sinh) → Ưu đãi → BMC.
- `SURVEY` là ngoại lệ duy nhất nhóm Tương tác → CIO duyệt bắt buộc, không auto-schedule.

**Error messages:**
- Create mode — CT ngoài 6 cho phép: `"Content type '[X]' không thuộc nhóm Noti Campaign (WARNING / SERVICE / PROMOTION_SERVICE / ADVERTISING / EVENT / SURVEY). CT '[X]' thuộc flow hệ thống/đối tác, không submit qua Noti Campaign. Vui lòng chọn lại CT phù hợp hoặc liên hệ PCS để được tư vấn."`
- Review mode — CT ngoài 14: `"Content type '[X]' không nằm trong danh sách 14 code được phép. Vui lòng chọn lại hoặc liên hệ PCS."`

**Implementation note:**
```
NOTI_CAMPAIGN_ALLOWED_CTS = {WARNING, SERVICE, PROMOTION_SERVICE, ADVERTISING, EVENT, SURVEY}
VALID_CTS_FULL = {TRANSACTION, REMIND, WARNING, SERVICE, PROMOTION, PROMOTION_SERVICE,
                  PROMOTION_OUTDATED, GAME, ADVERTISING, EVENT, FRIENDS,
                  BUSINESS_PAGE, SOCIAL, SURVEY}
# Create mode: content_type ∈ NOTI_CAMPAIGN_ALLOWED_CTS
# Review mode: content_type ∈ VALID_CTS_FULL
```

---

### Rule 1.2 — Chỉ dùng format out-app push
- **Tier:** 🔴 Script
- **Trigger:** Agent setup channel/format cho campaign
- **Logic:** Campaign thông thường (ngữ cảnh quảng cáo do user setup) chỉ được dùng out-app push. Các format sau đều bị block:
  - Push In-app = TRUE
  - Header (là một dạng in-app format, bị cấm từ 3/2025)
  - Popup, XBanner, Snackbar
- **Lưu ý role:** Business Account role: UI đã disable sẵn. Platform role: UI vẫn cho phép tick → agent phải chủ động chặn.
- **Error message:** `"Noti Campaign chỉ được gửi out-app (Push Notification) đến end-user. Format '[X]' không được phép. Nếu dùng các format in-app, vui lòng email đến platform-customer-success@mservice.com.vn và nêu rõ nghiệp vụ cần hỗ trợ."`
- **Implementation note:** Check `push_inapp`, `format` fields trước khi submit MCP call.

---

### Rule 1.3 — Cảnh báo (WARNING): không duplicate channel
- **Tier:** 🔴 Script
- **Trigger:** Agent tạo campaign content_type `WARNING` (Quan trọng/Cảnh báo, ví dụ sự cố hệ thống)
- **Logic:** Nếu đã có out-app campaign cho cùng sự cố → không tạo thêm Header in-app cho cùng nội dung đó.
- **Error message:** `"Campaign WARNING (Cảnh báo) cho sự cố này đã có out-app push. Không tạo thêm Header in-app cho cùng nội dung."`

---

### Rule 1.4 — PROMOTION*/GAME: Khuyến mãi direct push phải qua Noti Campaign
- **Tier:** 🔴 Script
- **Trigger:** Nội dung campaign có content_type prefix `PROMOTION*` hoặc `GAME` và chứa từ khoá khuyến mãi trực tiếp
- **Logic:** Detect keywords: "nhận voucher", "mở app nhận quà", "direct push", "big campaign" → route sang BMC, không tự submit.
- **Error message:** `"Campaign khuyến mãi có nội dung direct push voucher/big campaign phải được BMC duyệt trước khi submit."`

---

### Rule 1.5 — Khảo sát (SURVEY) phải do CIO quản lý
- **Tier:** 🔵 HITL
- **Trigger:** Agent propose campaign content_type `SURVEY`
- **Logic:** Agent chỉ được propose nội dung noti mời làm survey. Không được tự tạo bảng hỏi. Toàn bộ campaign SURVEY phải do CIO đăng ký và quản lý.
- **Hành động:** Agent flag → thông báo Growth → Các noti dạng này sẽ được CIO duyệt manual.
- **Error message:** `"Khảo sát (SURVEY) phải do CIO đăng ký. Agent chỉ hỗ trợ soạn nội dung noti mời khảo sát, không tạo campaign độc lập."`

---

### Rule 1.6 — Content type semantic consistency (CT vs nội dung + RefID alignment)
- **Tier:** 🟡 LLM (Reg-floor eligible)
- **Trigger:** Agent submit campaign với content_type + title + body + ref_id
- **Scope (v1.13+):** Rule 1.6 check **2 axes alignment**:
  1. **CT ↔ Content semantic** (axis nguyên gốc) — content có khớp semantic của `content_type` không
  2. **RefID ↔ Content keyword** (axis mới — BMC Rule #3.0) — landing page (resolved từ ref_id name) có khớp chủ đề noti không

#### Axis 1 — CT semantic mismatch
- **Câu hỏi cho LLM (semantic expectation mapping):**
  - `WARNING` (Cảnh báo): sự cố / lỗi hệ thống / cảnh báo bảo mật user cần biết ngay?
  - `SERVICE` (Dịch vụ): thông báo service-critical (thay đổi phí, policy change, bảo trì, cập nhật ToS)?
  - `REMIND` (Nhắc nhở): nhắc nhở service (mật khẩu sắp hết, KYC cần xác minh, giao dịch chờ xử lý)?
  - `PROMOTION_SERVICE` (Khuyến mãi dịch vụ): ưu đãi gắn với dịch vụ MoMo cụ thể (VD: giảm phí nạp thẻ)?
  - `ADVERTISING` (Quảng cáo): quảng bá sản phẩm/đối tác với giá trị rõ ràng?
  - `EVENT` (Sự kiện): thematic campaign lớn như Lắc Xì, 8/3, Tết...?
  - `SURVEY` (Khảo sát): mời user tham gia khảo sát/nghiên cứu thị trường?

- **Failure mode điển hình:** Content voucher/ưu đãi tagged `SERVICE` (thực ra nên là `PROMOTION_SERVICE`), content marketing tips tagged `WARNING`...

- **Pattern tightening v1.17+ — Gift card reminder explicit detection:** Khi Tier 1 đã trigger Rule 2.13 (`gift_card_reminder_duplicate_risk` tag), LLM Tier 2 **PHẢI** confirm CT semantic mismatch với confidence cao. Pattern:
  - Content: "Bạn còn voucher/quà..." / "Voucher đã sẵn sàng" / "Thu thập ngay"
  - Body mention: voucher, thẻ quà, đặc quyền thành viên, ưu đãi sinh nhật
  - Semantic intent: PROMOTIONAL REMINDER (nhắc dùng voucher) — KHÔNG phải service notification
  - Expected CT: `PROMOTION` / `PROMOTION_SERVICE` (Group Ưu đãi → BMC)
  - Actual CT thường bị BU dùng sai: `REMIND` (Group Quan trọng → PCS) → escape BMC review

- **Action khi pattern match v1.17+:**
  - Sub-score = 25 → Reg-floor force HITL bất kể overall score
  - Routing: theo CT default (KHÔNG override) — vd `CT=REMIND` → PCS, `CT=PROMOTION*` → BMC
  - HITL message bổ sung suggested CT: `"Content type 'REMIND' không khớp — nội dung gợi nhớ voucher promotional, suggest CT='PROMOTION' hoặc 'PROMOTION_SERVICE'. Approver xác nhận routing."`

- **Complement với Rule 2.13:**
  - **Rule 2.13** (Tier 1 script): catch pattern cụ thể với AND 3 signals → emit advisory HITL trigger (KHÔNG hard block)
  - **Rule 1.6 axis 1** (Tier 2 LLM): catch broader semantic mismatch + assign suggested CT
  - Two-layer defense: Tier 1 catch known pattern fast/cheap, Tier 2 catch broader nuance qua LLM judgment

#### Axis 2 — RefID ↔ Content alignment (BMC Rule #3.0)
- **Source:** BMC: *"Nội dung noti phải liên quan đến tính năng/offer trên landing page. VD: noti 'Nạp tiền giảm 20%' → landing page phải là màn nạp tiền"*
- **Logic (Phase 2):**
  1. Lookup tên màn từ refid: `awk -F'\t' -v r="<refid>" '$2==r{print $1}' assets/refid-glossary.tsv`
  2. So sánh keyword giữa tên màn vs title+body của noti
  3. Mismatch detect → HITL re-confirm (không hard block — false positive risk)
- **Failure mode điển hình:**
  - noti "Nạp tiền giảm 20%" + `ref_id=cinema_mini` (Mua vé xem phim) → ❌ mismatch
  - noti "Mua vé Avatar 3" + `ref_id=topup_phone` (Nạp tiền điện thoại) → ❌ mismatch
  - noti "An toàn thiết bị" + `ref_id=check_security` (An toàn thiết bị) → ✅ match (như TT77 campaign)
- **Carve-out:** Một số refid là entry chung (`home`, `tab_main`) — content có thể về bất kỳ topic nào → KHÔNG flag. Maintain list "generic refids" trong implementation note (vd `home`, `wallet`, `tab_*`, `homepage_*`).

#### Sub-score (combined cả 2 axes)
- 100: CT khớp semantic + refid landing khớp content
- 75: 1 axis có gray area (CT borderline HOẶC refid generic — không xác định)
- 50: 1 axis mismatch rõ (CT sai nhưng refid OK, hoặc ngược lại)
- 25: Cả 2 axes mismatch → Reg-floor trigger HITL
- 0: Mismatch rõ + có evidence vi phạm intent (vd CT=SERVICE nhưng content khuyến mãi + refid game) → Reg-floor + tag `intent_violation`

#### Error/HITL messages
- **CT mismatch (axis 1):** `"Content type '[X]' không khớp với nội dung — nội dung có vẻ thuộc '[CT_gợi_ý]'. Approver cần xác nhận routing."`
- **RefID mismatch (axis 2):** `"RefID '[X]' resolve tới màn '[name]' — không khớp với chủ đề noti '[title]'. Approver cần xác nhận hoặc đổi refid."`
- **Tags (Phase 5):** `ct_mismatch` (axis 1), `refid_content_mismatch` (axis 2 — NEW)

- **Implementation note:** Dim này là **Reg-floor eligible** (như DIM-4.x) — sub_score ≤ 25 → force HITL bất kể overall. Axis 2 phụ thuộc vào Rule 1.8 glossary file — nếu refid không tồn tại trong glossary thì Rule 1.8 đã flag riêng (`refid_not_in_whitelist`), Rule 1.6 axis 2 skip case đó.

---

### Rule 1.7 — EVENT chỉ dành cho thematic campaign lớn
- **Tier:** 🔵 HITL + 🔴 Script confirmation
- **Trigger:** Agent propose `content_type = EVENT`
- **Logic:** `EVENT` được thiết kế cho các big campaign / thematic lớn của MoMo (Lắc Xì, 8/3, 20/10, Tết Nguyên đán, 2/9, Black Friday, World Cup…). **KHÔNG** dùng cho promotion thường hoặc voucher thông thường.
- **Hành động 2-bước:**
  1. **Confirm người tạo:** Agent hỏi owner: *"Bạn đang tạo campaign EVENT — nội dung có thuộc thematic campaign lớn nào không? (VD: Lắc Xì 2026, Tết 2027, 8/3/2027…). Nếu không phải thematic campaign, hãy chuyển CT sang PROMOTION_SERVICE hoặc ADVERTISING."*
  2. **Flag HITL agent duyệt:** Bất kể confirm từ owner, route HITL cho approver (BMC) manual — approver xác nhận thematic context trước khi approve.
- **Error message (non-thematic):** `"EVENT chỉ dành cho thematic campaign lớn. Content này có vẻ là promotion thường — vui lòng chuyển CT sang PROMOTION_SERVICE hoặc ADVERTISING."`
- **HITL message:** `"Campaign EVENT cần BMC xác nhận thematic context (Lắc Xì / Tết / 8-3…) trước khi approve."`
- **Implementation note:** `hitl_triggered: true` cho mọi EVENT campaign; bỏ qua auto-approve route dù score ≥ 85.

---

### Rule 1.8 — RefID typo check (glossary là tham khảo, không hard rule)
- **Tier:** 🔵 HITL re-confirm (KHÔNG hard block)
- **Trigger:** Agent review/create campaign có `notification_reference.ref_id` set
- **Mục đích chính (v1.4.4+ — clarified):** **TYPO check** cho refid format ngắn (vd `check_security`, `cinema_mini`) — tránh BU điền tay sai chính tả. **KHÔNG** dùng để hard-enforce list màn hình.
- **2 format ref_id BU dùng hợp pháp:**
  1. **Screen identifier ngắn** (vd `check_security`, `onlinepanel_entry`, `home`) → check glossary cho typo
  2. **URL deeplink in-app webview** (vd `https://www.momo.vn/tin-tuc/...`) → ✅ pass (hợp lệ, BU chạy campaign trỏ về trang web in-app)
- **Source file:** `assets/refid-glossary.tsv` (~2827 unique refids, format `name<TAB>refid` sorted ASC by refid, derived từ `assets/MoMo RefID update 18 May 26.xlsx` của team Product, cập nhật mỗi đợt release màn mới)
- **3 lookup patterns (1 file phục vụ cả approve + create skill):**

  ```bash
  # Pattern 1 — Validate refid exists (approve flow, Rule 1.8 enforcement):
  awk -F'\t' -v r="<refid>" '$2==r{ok=1;exit} END{exit !ok}' assets/refid-glossary.tsv
  # exit 0 = valid → ✅ pass
  # exit 1 = not found → ⚠️ HITL re-confirm

  # Pattern 2 — Get human-readable name (approve flow enrichment + create flow display):
  awk -F'\t' -v r="<refid>" '$2==r{print $1}' assets/refid-glossary.tsv
  # → "Mua vé xem phim" (empty nếu không tồn tại)

  # Pattern 3 — Search refid theo keyword tên (create flow auto-suggest):
  grep -i "<keyword>" assets/refid-glossary.tsv
  # → list candidate refids matching tên có chứa keyword (case-insensitive)
  ```

- **Logic verdict (v1.4.4+):**
  - **URL format** (`https://...` / `http://...`) → ✅ pass (deeplink in-app webview hợp lệ, KHÔNG check glossary)
  - **Identifier format + trong glossary** → ✅ pass (bonus: enrich tên màn)
  - **Identifier format + không trong glossary** → ⚠️ HITL re-confirm (có thể typo BU điền tay, hoặc màn mới chưa update glossary)
- **HITL message:** *"RefID `{value}` không có trong MoMo screen glossary. Có thể typo hoặc màn mới. Approver xác nhận giùm refid này có hợp lệ không."*
- **Tag (Phase 5 structured log):** `refid_not_in_whitelist` — đã có trong Common tag dictionary.
- **Use case approve flow extension (UX nicety, optional):** Phase 3 summary table có thể enrich cột Content với tên màn auto-lookup (Pattern 2) — approver scan nhanh hơn, không cần tự nhớ refid → tên.
- **Use case create flow:** Khi user mô tả ý định campaign ("push về vé xem phim") → agent dùng Pattern 3 search keyword "phim/cinema/vé" → list candidate refids → user confirm chọn.
- **Update procedure:** Khi Product team release màn mới, replace `assets/MoMo RefID update 18 May 26.xlsx` bằng file mới, re-generate `refid-glossary.tsv` bằng script Python (xem regen snippet trong `admin-setup.md`).
- **Implementation note:** Skill **KHÔNG** preload full glossary trong Phase 0 (117KB rarely change) — chỉ load on-demand trong Phase 2 (validate) hoặc Phase 3 (enrich tên) khi cần. File reference đủ.

---

