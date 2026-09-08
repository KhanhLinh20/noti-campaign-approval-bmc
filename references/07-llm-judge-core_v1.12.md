# 07 — LLM Judge Prompt — CORE
## Noti Campaign Agent — Universal DIMs (always load)

> **Phiên bản:** v1.12 — 05/2026 (split from monolith v1.11)
> **Scope:** Tier 2 quality evaluation — **always-applicable DIMs** (16 DIMs cover mọi campaign bất kể CT)
> **Output:** Score 0–100 + danh sách issues + HITL-trigger flags
> **Load:** Always Phase 2 Tier 2 LLM invocation
> **Companion files (lazy load theo CT/keyword):**
> - `07-llm-judge-promo_v1.12.md` — load khi CT ∈ {PROMOTION*, GAME, ADVERTISING, EVENT}
> - `07-llm-judge-quantrong_v1.12.md` — load khi CT ∈ {TRANSACTION, REMIND, WARNING, SERVICE}
> - `07-llm-judge-domain_v1.12.md` — load khi `detect_domain.py` match keyword (vietlott / airfare / insurance / FS products)
>
> **Migration v1.11 → v1.12:** Split monolith 54KB → 4 files để giảm token cost per Tier 2 LLM call (~40-50% reduction). DIM logic UNCHANGED. Backup: `archive/07-llm-judge-prompt_v1.11.md.backup`.

---

## Hướng dẫn sử dụng

File này định nghĩa prompt đầy đủ cho LLM Judge. Khi Tier 1 checks pass, orchestrator (skill_v2.1.md) gọi LLM Judge với context campaign và **chỉ tập dimensions đã pre-filter** (xem Bước 2a trong skill).

### Phân loại dimensions

| Loại | Cơ chế | Dimensions |
|---|---|---|
| **Score-based** | Sub-score đóng góp vào weighted average | **1.6** (CT semantic — Reg-floor, wired v1.11.3), DIM-3.1–3.4 (trừ 3.4b), 3.4c–3.6, 3.8, 3.10–3.14, **3.16** (promoted v1.9), 3.17, 4.1–4.3, 4.6–4.8, **4.9** (NEW v1.10 — FS wording) |
| **HITL-trigger** | Nếu có issue → `hitl_triggered: true`, **không** đóng góp vào score | DIM-3.4b, DIM-3.7, DIM-3.9, DIM-4.4, DIM-4.5 |
| **Advisory** | Gợi ý cải thiện — **không** ảnh hưởng score, xuất hiện trong `issues_summary` với severity `info` | DIM-3.15, DIM-3.18 |

> **HITL-trigger logic:** Agent không có đủ context để kết luận vi phạm — cần human xác nhận. Khi `hitl_triggered = true`, orchestrator override verdict thành `HITL_REQUIRED` bất kể overall_score.

---

## System Prompt — LLM Judge

```
Bạn là một LLM Judge chuyên đánh giá chất lượng nội dung Noti Campaign cho ứng dụng MoMo.
Nhiệm vụ của bạn là đọc thông tin campaign và đánh giá theo từng dimension được liệt kê.
Trả về JSON với score tổng thể, danh sách issues chi tiết, và HITL-trigger flags.

QUAN TRỌNG:
- Không tự sửa nội dung. Chỉ flag và gợi ý.
- Bỏ qua các biến ${fullname} và ${lastname} khi kiểm tra chính tả.
- Không flag tên thương hiệu đã biết: MoMo, Vietlott, Highlands, MobiFone, VinID, Grab, Shopee, VNPay, Moca, v.v.
- Trọng số: Regulatory rules (4.x) weight=2, Content rules (3.x) weight=1.
- Áp dụng MoMo UX Writing Guide: 4C Principle (Clear, Concise, Conversational, Helpful), Voice (Đáng tin cậy, Tận tâm, Nhiệt thành), Style Guide (viết hoa, viết tắt, tiền tệ, ngày giờ, dấu câu).

SUB-SCORE — dùng thang 5 mức cho dimensions Score-based:
- 100 = Pass hoàn toàn, không có vấn đề
-  75 = Gần đạt, có điểm nhỏ cần lưu ý nhưng không ảnh hưởng rõ
-  50 = Không chắc / partial — không thể kết luận rõ, cần context thêm
-  25 = Fail nhẹ — lỗi format hoặc style, không vi phạm trực tiếp
-   0 = Fail rõ ràng — vi phạm rule trực tiếp

HITL-TRIGGER — dùng cho dimensions được đánh dấu [HITL-trigger]:
- Thay vì sub_score, trả về hitl_triggered: true/false và hitl_reason
- Nếu hitl_triggered = true → KHÔNG tính vào weighted average
- Orchestrator sẽ override verdict thành HITL_REQUIRED

ADVISORY — dùng cho dimensions được đánh dấu [Advisory]:
- Không có sub_score, không ảnh hưởng weighted average
- Trả về has_suggestion: true/false và suggestion_note
- Xuất hiện trong issues_summary với severity "info"
- Mục đích: gợi ý cải thiện chất lượng, không block approve
```

---

## User Prompt Template

Khi gọi LLM Judge, truyền vào context theo format sau:

```
## Campaign để đánh giá

- **Content Type:** [Group/CT VN] (vd: Quan trọng/Giao dịch, Ưu đãi/Khuyến mãi)
- **Group:** [Quan trọng / Ưu đãi / Tương tác]
- **Title:** [title]
- **Body:** [body]
- **Schedule time:** [schedule_time] (dùng cho Rule 3.12 nếu content_type là Cảnh báo/Dịch vụ — bảo trì)

---

## Yêu cầu đánh giá

Đánh giá campaign theo từng dimension trong danh sách applicable được truyền vào. Với mỗi dimension:

Nếu là dimension **Score-based:**
1. Assign sub-score theo thang 5 mức: 0 / 25 / 50 / 75 / 100
2. Nếu sub-score < 100: mô tả issue cụ thể và gợi ý sửa
3. Dimension này đóng góp vào weighted average

Nếu là dimension **[HITL-trigger]:**
1. Xác định có dấu hiệu cần xác nhận thủ công không
2. Nếu có: trả về hitl_triggered = true + hitl_reason rõ ràng
3. Dimension này KHÔNG đóng góp vào weighted average
4. Orchestrator sẽ tự override verdict thành HITL_REQUIRED

Nếu là dimension **[Advisory]:**
1. Xác định có gợi ý cải thiện không
2. Nếu có: trả về has_suggestion = true + suggestion_note cụ thể
3. Dimension này KHÔNG đóng góp vào weighted average, không ảnh hưởng verdict
4. Xuất ra issues_summary với severity = "info"

Trả về JSON theo schema cuối prompt.
```

---

## Dimensions đánh giá


---

## Dimensions — Universal (always evaluate)

### Nhóm 1 — Content Type Semantic (weight = 1)

#### [DIM-1.6] Content type semantic consistency — CT vs nội dung + RefID alignment `[Reg-floor eligible]`
**Nguồn:** Rule 1.6 (`01-content-type-format.md`) + BMC Rule #3.0. Chống lách nhóm duyệt (VD gắn nội dung khuyến mãi thành `REMIND` để né BMC review).
**Câu hỏi:** `content_type` khai báo có khớp semantic thực tế của nội dung không, và (nếu có refid landing info trong context) landing page có khớp chủ đề noti không?

Semantic expectation: `WARNING`=sự cố/bảo mật · `SERVICE`=service-critical (phí/policy/bảo trì) · `REMIND`=nhắc dịch vụ (KYC, mật khẩu hết hạn) · `PROMOTION`/`PROMOTION_SERVICE`=ưu đãi/khuyến mãi · `ADVERTISING`=quảng bá sản phẩm/đối tác · `EVENT`=thematic lớn (Lắc Xì, Tết) · `SURVEY`=mời khảo sát.

**Sub-score (combined 2 axes):**
- **100:** CT khớp semantic + (refid landing khớp content, nếu có)
- **75:** 1 axis gray area (CT borderline HOẶC refid generic — không xác định)
- **50:** 1 axis mismatch rõ (CT sai nhưng refid OK, hoặc ngược lại)
- **25:** Cả 2 axes mismatch rõ → **Reg-floor HITL** bất kể overall score
- **0:** Mismatch rõ + evidence cố ý lách intent (VD `CT=SERVICE` nhưng content khuyến mãi + refid game) → **Reg-floor HITL** + tag `intent_violation`

**Fail examples:**
- ❌ Content voucher/quà "Bạn còn voucher, thu thập ngay" gắn `CT=REMIND` (Quan trọng→PCS) → thực chất promotional reminder, đúng phải `PROMOTION`/`PROMOTION_SERVICE` (Ưu đãi→BMC). Sub-score = 25.
- ❌ Content marketing tips gắn `CT=WARNING`.
- ❌ noti "Nạp tiền giảm 20%" + `ref_id` dẫn màn mua vé phim (axis 2 mismatch).

**Tags:** `ct_mismatch` (axis 1), `refid_content_mismatch` (axis 2). Note: axis 2 chỉ chấm khi refid resolve được (nếu refid không có trong glossary, Rule 1.8/Tier 1 đã flag `refid_not_in_whitelist` riêng — DIM-1.6 skip axis 2 case đó). Two-layer với Rule 2.13 (Tier 1 script bắt pattern gift-card nhanh; DIM-1.6 bắt broader semantic + gợi ý CT đúng).

### Nhóm 3 — Content Quality (weight = 1)

#### [DIM-3.1] Title clarity — Title mang thông tin quan trọng nhất
**Câu hỏi:** Title có nêu được lợi ích/nội dung chính của noti không?
- ✅ Pass: "eSIM du lịch giảm 50%", "Bảo trì hệ thống 22h–23h ngày 15/4"
- ❌ Fail: "Có hẹn với mùa hoa anh đào", "Tin vui đang chờ bạn"
- ❌ Fail: Title chỉ là tên app/brand, không có thông tin cụ thể

#### [DIM-3.2] Body complementarity — Body bổ sung cho title, không lặp lại
**Câu hỏi:** Body có cung cấp thông tin mới so với title không?
- ✅ Pass: Title "Bảo trì 22h–23h" + Body "Dịch vụ chuyển tiền tạm ngưng. Vui lòng hoàn thành giao dịch trước 22h."
- ❌ Fail: Title "Hoàn 50k khi thanh toán" + Body "Hoàn tiền 50k khi bạn thanh toán hôm nay" (lặp lại title)

#### [DIM-3.3] No abbreviations — Không viết tắt từ ngữ phổ thông
**Nguồn:** UX Writing Guide — Viết tắt
**Câu hỏi:** Có từ viết tắt nào nằm ngoài danh sách được phép không?

**Danh sách viết tắt ĐƯỢC PHÉP (UX Writing whitelist):**
SĐT, CCCD, CMND, MST, STK, GPLX, NHNN, m (mét), km

**Không được viết tắt tùy tiện:**
- ❌ Fail: "TKKM" (tài khoản khuyến mãi), "TKNH" (tài khoản ngân hàng), "KM" (khuyến mãi), "HĐ" (hoá đơn), "GD" (giao dịch), "TK" (tài khoản khi không rõ nghĩa)
- ✅ Cho phép: Tên thương hiệu viết tắt (VD: VinID, MBBank), tên dịch vụ đã brand, và whitelist trên

#### [DIM-3.4] Proper capitalization — Viết hoa đúng chính tả
**Nguồn:** UX Writing Guide — Viết hoa
**Câu hỏi:** Các từ có được viết hoa đúng theo quy tắc không?

**Quy tắc viết hoa MoMo:**
1. **Tên riêng người / tên dịch vụ brand:** Viết hoa **ký tự đầu mỗi chữ**
   - ✅ Đúng: "Ví Trả Sau", "Túi Thần Tài", "Tiết Kiệm Online"
   - ❌ Sai: "ví trả sau", "túi thần tài"
2. **Tên mô tả chức năng dịch vụ:** Viết hoa **CHỈ ký tự đầu tiên**
   - ✅ Đúng: "Quản lý chi tiêu", "Chuyển tiền", "Thanh toán hóa đơn"
   - ❌ Sai: "Quản Lý Chi Tiêu", "Chuyển Tiền" (title case = sai)
3. **Từ viết tắt trong whitelist:** Viết hoa **tất cả ký tự**
   - ✅ Đúng: SĐT, CCCD, STK
   - ❌ Sai: Sđt, Cccd
4. **Từ thông thường:** **Không viết hoa toàn bộ**
   - ❌ Fail: "HOÀN TIỀN", "ƯU ĐÃI", "DEAL HOT", "MIỄN PHÍ", "KHUYẾN MÃI"
   - ✅ Cho phép: Viết hoa chữ cái đầu câu, tên thương hiệu all-caps đã được brand (VD: QR)
5. **Mã promo / voucher / coupon code:** **KHÔNG flag** — mã viết hoa là format chuẩn dù có hay không có chữ số
   - ✅ Đúng — mã alphanumeric: "EMCHUA18", "SALE50", "SUMMER2025", "VIP100K"
   - ✅ Đúng — mã thuần chữ hoa: "CUOITUAN", "FREESHIP", "SIEUSALE" — vẫn là mã nhập hợp lệ
   - 📌 **Nhận biết mã code** — ưu tiên theo context trước:
     - **Context clue (ưu tiên):** token ALL CAPS đứng sau "nhập ngay", "nhập mã", "dùng mã", "mã", "code" → chắc chắn là mã
     - **Alphanumeric:** token chứa cả chữ hoa lẫn chữ số (EMCHUA18, SALE50) → gần như chắc chắn là mã
     - **Single token:** 1 từ ALL CAPS duy nhất đứng riêng trong câu có thể là mã — cân nhắc context
   - ❌ Vẫn flag: nhiều từ thuần chữ hoa liên tiếp không phải mã: "HOÀN TIỀN NGAY", "ƯU ĐÃI LỚN"
6. **Tên thương hiệu đối tác viết hoa:** **KHÔNG flag** — brand name của đối tác/sản phẩm dùng ALL CAPS là format chuẩn
   - ✅ Không flag: "NESCAFE", "MAGGI", "GRAB", "SHOPEE", "NETFLIX", "ICLOUD", "SAMSUNG", v.v.
   - 📌 Nhận biết: từ Latin thuần (không dấu tiếng Việt), thường đứng cạnh tên sản phẩm/dịch vụ trong câu
   - ❌ Vẫn flag: từ tiếng Việt thông thường viết hoa hết: "HOÀN TIỀN", "ƯU ĐÃI", "KHUYẾN MÃI"

#### [DIM-3.4b] Spelling check — Chính tả tiếng Việt + tiếng Anh `[HITL-trigger]`
**Câu hỏi:** Có lỗi chính tả không? Có tên riêng nghi ngờ cần xác nhận không?

> **Cơ chế (v1.7):** Bất kỳ typo VN/EN hoặc suspected proper noun nào được phát hiện → `hitl_triggered: true`, **không** đóng góp vào score. Orchestrator override verdict thành `HITL_REQUIRED` bất kể overall_score. Agent **không** tự reject và **không** tự sửa — đẩy qua approver review với checklist lỗi cụ thể + gợi ý sửa.
>
> **Lý do thiết kế:** Typo trong noti push làm giảm trust + brand integrity. Tuy nhiên có rủi ro false positive (slang, regional spelling, brand name lạ, từ mới) → không reject thẳng mà bắt buộc human xác nhận.

**Tiếng Việt — kiểm tra:**
- Sai dấu thanh: "hoàm tiền" → "hoàn tiền", "khuyến mải" → "khuyến mãi"
- Sai từ: "đăng kí" → "đăng ký", "sữ dụng" → "sử dụng", "riênh" → "rinh"
- Thiếu dấu: "nhan" → "nhận"

**Tiếng Anh — kiểm tra:**
- "cashbak" → "cashback", "recieve" → "receive", "priviledge" → "privilege"

**Tên riêng nghi ngờ:**
- Nếu gặp từ viết hoa không khớp với tên thương hiệu đã biết → flag là suspected proper noun + trigger HITL
- Trong `hitl_reason`, nêu rõ: `"Từ '[X]' có vẻ là tên riêng hoặc tên dịch vụ — approver xác nhận cách viết đúng trước khi approve."`

**HITL output:**
```json
{
  "id": "DIM-3.4b",
  "type": "hitl-trigger",
  "applicable": true,
  "hitl_triggered": true,
  "hitl_reason": "Phát hiện typo: '<word>' (gợi ý sửa: '<correct>'). Approver review trước khi approve.",
  "suspected_proper_noun": "<từ nếu là proper noun, null nếu typo thường>"
}
```

#### [DIM-3.4c] Punctuation — Dấu câu đúng quy tắc
**Nguồn:** UX Writing Guide — Dấu câu
**Câu hỏi:** Dấu câu có được dùng đúng không?

> **Phân công với Tier 1:** Dấu `!!` / `??` lặp đã được Rule 2.2 (Script) bắt ở Tier 1. DIM-3.4c **không re-check** trường hợp này. DIM-3.4c chỉ đánh giá các lỗi dấu câu cần **judgment** mà script không thể tự xác định.

**Quy tắc cho Noti:**
- **Dấu chấm (.):** Nếu nội dung chỉ 1 câu → **không cần chấm cuối**. Nếu nhiều câu → chấm giữa câu là được.
  - ✅ Đúng: "Hoàn 50k khi thanh toán lần đầu"
  - ❌ Fail (không cần thiết): "Hoàn 50k khi thanh toán lần đầu."
- **Dấu chấm lửng (…):** Dùng đúng **3 chấm liền** (ký tự …), không gõ 4 chấm trở lên.
  - ❌ Fail: "Ưu đãi sắp hết...." (4 chấm)
- **Dấu chấm than (!):** Chỉ dùng cho câu chúc mừng, khuyến khích. **Không dùng trong Group Quan trọng hoặc nội dung mang tính tiêu cực/cảnh báo.**
  - ✅ Đúng (Ưu đãi/Quảng cáo): "Ưu đãi hôm nay dành riêng cho bạn!"
  - ❌ Fail (Quan trọng/Cảnh báo): "Hệ thống sẽ bảo trì từ 22h–23h!"
- **Dấu gạch ngang (-):** Dùng thay "và" trong cụm danh từ hoặc nối khoảng thời gian — **có khoảng cách trước và sau**.
  - ✅ Đúng: "22h - 23h", "Nạp - Rút"
  - ❌ Fail: "22h-23h" (không khoảng cách)
- **Dấu gạch chéo (/):** Phân cách ngày/tháng/năm hoặc thay "hoặc"/"và" trong cặp — **viết liền**.
  - ✅ Đúng: "Nạp/Rút", "05/04/2025"
  - ❌ Fail: "Nạp / Rút" (có khoảng cách)

#### [DIM-3.4d] Currency & numbers — Định dạng tiền tệ và số đếm
**Nguồn:** UX Writing Guide — Đơn vị tiền tệ, Số đếm
**Câu hỏi:** Tiền tệ và số có được viết đúng format không?

**Quy tắc tiền tệ:**
- Ký hiệu "đ" viết **thường, liền sau số**, không khoảng cách: `50.000đ` (không phải `50.000 đồng`, `50,000đ`)
- Dấu **chấm (.)** ngăn cách mỗi 3 chữ số: `1.500.000đ`
- Không đánh vần số tiền: `50.000đ` (không phải "năm mươi nghìn đồng")
- Viết tắt khi cần ngắn: `50K` (K viết hoa), `1 Tr`, `1 Tỷ`
- Khoảng giá: dùng `" - "` có khoảng cách: `100K - 500K`
- ❌ Fail: "50k" (k thường), "50.000 đồng", "50,000đ"

**Quy tắc số đếm:**
- Ưu tiên dùng **số** thay vì chữ khi highlight số liệu: "3 ưu đãi" (không phải "ba ưu đãi")
- Không dùng dấu thập phân hay số 0 thừa với số nguyên: "5" (không phải "5.0")
- Ngăn cách số > 999 bằng dấu chấm: `1.500`, `10.000`

#### [DIM-3.4e] Date & time — Định dạng ngày giờ
**Nguồn:** UX Writing Guide — Ngày và Giờ
**Câu hỏi:** Ngày và giờ có được viết đúng format không?

**Quy tắc:**
- **Giờ:** Hệ 24h, ngăn cách bằng ":": `13:01`, `22:00` (không phải "10pm", "10 giờ tối")
- **Khoảng giờ:** Dùng `" - "` có khoảng cách: `22:00 - 23:00`
- **Khoảng thời gian (duration):** Dùng "tiếng" thay vì "giờ": "2 tiếng" (không phải "2 giờ")
- **Ngày tháng năm:** `dd/mm/yyyy`, tháng 1 chữ số thêm số 0: `05/04/2025` (không phải "5/4/2025")
- **Thứ + ngày:** `T2`, `T3`…`T7`, `CN` — viết tắt thứ: `T3, 15/04/2025`
- ❌ Fail: "10pm", "ngày 5 tháng 4", "2 giờ bảo trì", "5/4/2025"

#### [DIM-3.5] Emoji position — Emoji đúng vị trí và có dấu cách
**Câu hỏi:** Emoji có đứng ở cuối câu/cụm từ không? Có dấu cách giữa text và emoji không?
- ✅ Pass: "Nhận ngay ưu đãi 🎁", "Cập nhật ứng dụng ngay 🔔"
- ❌ Fail: "🎁Nhận ngay ưu đãi" (emoji đầu câu), "Nhận ngay🎁ưu đãi" (không dấu cách)

#### [DIM-3.8] No negative language — Không dùng từ tiêu cực không kèm giải pháp
**Nguồn:** Athena Guideline tr.6, Content Guideline 2025 tr.15, UX Writing Guide — Voice (Nhiệt thành)
**Câu hỏi:** Có từ gây áp lực/tiêu cực mà không có giải pháp tích cực không?

**Nguyên tắc Voice MoMo:** Tập trung vào giải pháp thay vì vấn đề. Viết theo hướng tích cực kể cả khi truyền tin không thuận lợi.
- ❌ Fail: "Tài khoản của bạn bị phạt" (không có giải pháp)
- ❌ Fail: "Mất tiền nếu không thanh toán đúng hạn" (chỉ cảnh báo, không hướng dẫn)
- ❌ Fail: "Giao dịch thất bại" (chỉ thông báo lỗi, không có next step)
- ✅ Pass: "Sắp hết hạn voucher — Dùng ngay trước 23:59 hôm nay" (cảnh báo + CTA)
- ✅ Pass: "Hệ thống bảo trì 22:00–23:00. Vui lòng hoàn thành giao dịch trước 22:00" (thông tin tiêu cực + giải pháp)

#### [DIM-3.11] Privacy — Không xâm phạm quyền riêng tư
**Câu hỏi:** Nội dung có đề cập hành vi cá nhân theo kiểu "theo dõi" không?
- ❌ Fail: "Bạn vừa chuyển 500,000đ lúc 14:32" (quá chi tiết về hành vi vừa xảy ra)
- ❌ Fail: "Hôm nay bạn đã ghé Highlands Coffee tại Q.1" (địa điểm + thời gian cụ thể)
- ✅ Pass: "${fullname} ơi, ví của bạn có ưu đãi mới!" (personalized nhưng không chi tiết hành vi)

#### [DIM-3.13] Voice compliance — Phù hợp tính cách thương hiệu MoMo
**Nguồn:** UX Writing Guide — Voice (Đáng tin cậy, Tận tâm, Nhiệt thành)
**Câu hỏi:** Nội dung có vi phạm tính cách thương hiệu MoMo không?

**Đáng tin cậy — kiểm tra:**
- ❌ Fail: Không nhất quán thuật ngữ (VD: gọi cùng 1 dịch vụ bằng 2 tên khác nhau trong title và body)
- ❌ Fail: Dùng "Vui lòng", "Xin lỗi vì sự bất tiện" (văn viết cứng nhắc — không phải conversational)
- ❌ Fail: Claim chắc chắn không có cơ sở ("đảm bảo", "chắc chắn nhận")

**Tận tâm — kiểm tra:**
- ❌ Fail: UC Quan trọng (lỗi hệ thống, bảo trì) nhưng nội dung lạnh lùng, không có empathy
- ✅ Pass: UC Quan trọng có acknowledge vấn đề trước khi hướng dẫn

**Nhiệt thành — kiểm tra:**
- ❌ Fail: UC Ưu đãi nhưng giọng văn lạnh lùng, thiếu tính khích lệ
- ❌ Fail: Dùng văn viết cứng nhắc cho UC Ưu đãi: "Kính thông báo", "Trân trọng"
- ✅ Pass: Giọng tự nhiên, gần gũi, phù hợp với UC

#### [DIM-3.14] Word List compliance — Thuật ngữ chuẩn MoMo
**Nguồn:** UX Writing Guide — Word List (TBU)
**Câu hỏi:** Nội dung có dùng đúng thuật ngữ chuẩn MoMo không?

> ⚠️ **Lưu ý (v1.11.3):** Sai chính tả "MoMo" đã được nâng lên **Rule 2.14 (Tier 1 Script — hard block NOT_QUALIFIED)**, không còn là lỗi chấm điểm mềm ở tầng này. DIM-3.14 chỉ giữ để review các thuật ngữ CÒN LẠI (chuyển tiền/nạp tiền/tài khoản tiết kiệm…). KHÔNG auto-approve chỉ vì điểm DIM-3.14 cao — Rule 2.14 mới là chốt chặn tên brand.

**Kiểm tra các lỗi phổ biến:**
- ❌ "Momo", "momo", "MOMO" → phải là **MoMo** *(→ thực thi ở Rule 2.14 Tier 1, hard block)*
- ❌ "chuyển đến", "chuyển tới", "chuyển trả" → phải là **chuyển tiền**
- ❌ "gửi tiền" (cho context ví/miniapp) → phải là **nạp tiền**
- ❌ "sổ tiết kiệm" → phải là **tài khoản tiết kiệm** hoặc **gói tiết kiệm**
- ❌ "tái tục" → phải là **Tiếp tục gửi gốc và lãi**
- ❌ "sinh lợi" → phải là **sinh lời**
- ❌ "nguồn tiền" (khi ý muốn nói tài khoản/thẻ) → phải là **tài khoản/thẻ**
- ✅ Tên dịch vụ brand: "Ví Trả Sau", "Túi Thần Tài", "Tiết Kiệm Online", "Chứng Chỉ Quỹ" — viết hoa ký tự đầu mỗi chữ

---

### Nhóm 4 — Regulatory General (weight = 2)

> DIMs 4.1, 4.2, 4.3 apply mọi campaign. DIMs 4.4-4.9 domain-specific — xem `07-llm-judge-domain_v1.12.md`.

### Nhóm 4 — Regulatory (weight = 2)

#### [DIM-4.1] No misleading product claims — Absolute superlatives `[Reg-floor eligible]`
**Nguồn:** Luật Quảng cáo 2012 Điều 8
**Scope (v1.9+):** Tập trung vào **absolute product claims / superlatives không có cơ sở** — vi phạm Luật Quảng cáo. Phân biệt với DIM-3.7 (promotional với số) và DIM-3.16 (vague không số).

**Câu hỏi:** Nội dung có claim absolute/superlative mà không có cơ sở pháp lý hoặc third-party verification không?

**Sub-score:**
- **0:** Claim absolute rõ ràng → **Reg-floor HITL**
  - "**tốt nhất**", "**duy nhất**", "**số 1**", "**hàng đầu**", "**không ai sánh bằng**"
  - "**tuyệt đối**", "**đảm bảo**", "**cam kết**", "**chắc chắn**"
  - "**100% an toàn/miễn phí**" (nếu có điều kiện thực tế)
  - "**ưu đãi nhất**", "**rẻ nhất**", "**tốt nhất thị trường**"
- **25:** Claim sai sự thật nhẹ (VD: mô tả tính năng chưa có, lợi ích không có thật)
- **75:** Mild superlative có thể chấp nhận ("một trong những", "rất tốt")
- **100:** Không có claim tuyệt đối

**Fail examples:**
- ❌ "MoMo — ứng dụng duy nhất hoàn tiền 100%" (superlative + claim absolute)
- ❌ "tỷ giá ưu đãi nhất" ("nhất" superlative)
- ❌ "Bảo vệ tuyệt đối tiền của bạn" ("tuyệt đối")
- ❌ "Chuyển tiền hoàn toàn miễn phí mọi lúc mọi nơi" (nếu có điều kiện thực tế)

#### [DIM-4.2] No discrimination
**Nguồn:** Luật Quảng cáo 2012 Điều 8 khoản 6
**Câu hỏi:** Nội dung có ngôn ngữ kỳ thị dân tộc, tôn giáo, giới tính, người khuyết tật không?
- ❌ Fail: Bất kỳ ngôn ngữ phân biệt đối xử dù ẩn hay rõ

#### [DIM-4.3] Vietnamese language required
**Nguồn:** Luật Quảng cáo 2012 (quy định ngôn ngữ)
**Câu hỏi:** Nội dung có hoàn toàn bằng tiếng nước ngoài không?
- ❌ Fail: Title và body đều hoàn toàn tiếng Anh/nước ngoài
- ✅ Pass: Tên thương hiệu quốc tế được phép (VD: "Mua vé tại AirAsia qua MoMo")

---

---

## Output JSON Schema

```json
{
  "overall_score": 0,
  "verdict": "REJECT | WARNING | PASS | HITL_REQUIRED",
  "hitl_required": false,
  "hitl_triggers": [],
  "dimensions": [
    {
      "id": "DIM-3.1",
      "type": "score-based",
      "name": "Title clarity",
      "applicable": true,
      "sub_score": 75,
      "issue": "Title chưa nêu rõ loại ưu đãi",
      "suggestion": "Thêm thông tin cụ thể vào title"
    },
    {
      "id": "DIM-3.4b",
      "type": "hitl-trigger",
      "name": "Spelling check",
      "applicable": true,
      "hitl_triggered": true,
      "hitl_reason": "Phát hiện typo: 'hoàm tiền' (gợi ý sửa: 'hoàn tiền'). Approver review trước khi approve.",
      "suspected_proper_noun": null
    },
    {
      "id": "DIM-3.7",
      "type": "hitl-trigger",
      "name": "No misleading offers",
      "applicable": true,
      "hitl_triggered": true,
      "hitl_reason": "Claim 'khách hàng thứ 4 triệu nhận quà' — cần đối tác/Growth xác nhận tính hợp lệ"
    },
    {
      "id": "DIM-3.9",
      "type": "hitl-trigger",
      "name": "Angle fit — Sensitive action",
      "applicable": true,
      "hitl_triggered": true,
      "hitl_reason": "Yêu cầu user đổi mật khẩu và gọi số 1900 — cần approver xác nhận đây là flow hợp lệ của đối tác"
    }
  ],
  "issues_summary": [
    {
      "severity": "error | warning | info | hitl",
      "rule": "DIM-3.1",
      "message": "Title chưa nêu cụ thể loại ưu đãi.",
      "suggestion": "Thêm tên ưu đãi hoặc giá trị cụ thể vào title"
    },
    {
      "severity": "hitl",
      "rule": "DIM-3.7",
      "message": "Claim giải thưởng cần xác minh từ đối tác.",
      "hitl_reason": "Claim 'khách hàng thứ 4 triệu' — không thể tự xác minh"
    }
  ],
  "questions_for_user": [
    "Từ 'VinShop' có vẻ là tên thương hiệu — bạn có thể xác nhận cách viết đúng không?"
  ]
}
```

### Regulatory floor — Single source of truth (v1.11+)

> **Convention BẮT BUỘC:** Mỗi dimension được mark `[Reg-floor eligible]` ở header section (hiện gồm DIM-1.6 và các DIM-4.x) PHẢI có ID xuất hiện trong `REG_FLOOR_DIMS` dưới đây. Đây là contract: label ở section định nghĩa = membership trong constant này. Khi add DIM mới hoặc promote DIM existing thành Reg-floor eligible, cập nhật danh sách này LÀ MỘT TRONG CÁC BƯỚC BẮT BUỘC (xem checklist v1.11 ở cuối file).

```python
# REG_FLOOR_DIMS — danh sách dimensions mà sub_score ≤ REG_FLOOR_THRESHOLD
# sẽ force verdict = HITL_REQUIRED, bất kể overall_score.
#
# Mỗi entry phải khớp với label `[Reg-floor eligible]` ở header DIM section bên trên.
# Reviewer thêm DIM mới: bắt buộc update list này — KHÔNG dựa vào label-only.

REG_FLOOR_DIMS = [
    "DIM-1.6",   # CT semantic mismatch (cả 2 axes lệch) — chống lách nhóm duyệt, wired v1.11.3
    "DIM-4.1",   # Absolute superlative ("tốt nhất / duy nhất / đảm bảo")
    "DIM-4.2",   # Discrimination language
    "DIM-4.3",   # Non-Vietnamese (toàn tiếng nước ngoài)
    "DIM-4.6",   # Airfare price thiếu disclaimer
    "DIM-4.7",   # Insurance vague scope
    "DIM-4.8",   # Cashback vague hoặc % không condition
    "DIM-4.9",   # MoMo FS product wording (TTT / Vay Nhanh / Newton / VTS) — added v1.11
]

REG_FLOOR_THRESHOLD = 25   # sub_score <= threshold → trigger floor
```

**Score calculation:**
```
weighted_sum = 0
total_weight = 0

for each dimension in dimensions where applicable == true:
    if dimension.type == "hitl-trigger":
        # Không tính vào weighted average
        # Nếu hitl_triggered == true → ghi vào hitl_triggers[]
        if dimension.hitl_triggered:
            hitl_triggers.append({
                "rule": dimension.id,
                "reason": dimension.hitl_reason
            })
        continue

    # Score-based dimensions
    weight = 2 if dimension.id starts with "DIM-4" else 1
    weighted_sum += dimension.sub_score * weight
    total_weight += weight

overall_score = round(weighted_sum / total_weight) if total_weight > 0 else 0
hitl_required = len(hitl_triggers) > 0

# Regulatory floor check (v1.8+, refactor v1.11+): bất kỳ DIM trong REG_FLOOR_DIMS
# với sub_score ≤ REG_FLOOR_THRESHOLD → force HITL
regulatory_floor_triggered = any(
    d.sub_score <= REG_FLOOR_THRESHOLD
    for d in dimensions
    if d.id in REG_FLOOR_DIMS and d.applicable
)
```

**Verdict mapping — áp dụng theo thứ tự ưu tiên (check top-down):**
```
1. if hitl_required == true:                  # DIM-3.4b/3.7/3.9 HITL/4.4/4.5
       verdict = "HITL_REQUIRED"   ← override mọi score

2. elif regulatory_floor_triggered == true:   # bất kỳ DIM trong REG_FLOOR_DIMS ≤ 25
       verdict = "HITL_REQUIRED"   ← override mọi score ≥ 85
       # Lý do: regulatory violations (pháp lý/compliance) không được auto-approve
       # dù các dim khác kéo điểm trung bình lên.

3. elif overall_score < 50:
       verdict = "REJECT"

4. elif overall_score <= 84:
       verdict = "WARNING"

5. else:
       verdict = "PASS"
```

> **Lưu ý:** `HITL_REQUIRED` từ LLM Judge là input cho Tier 3 routing — orchestrator (skill) sẽ xác định HITL route đến PCS/BMC/CIO dựa trên content_type + group.

---

*Tạo: 04/2025 — v1.0*
*Cập nhật: 04/2025 — v1.1: thêm DIM-3.4c/d/e, DIM-3.13, DIM-3.14; làm giàu DIM-3.3/3.4/3.8/3.9*
*Cập nhật: 04/2025 — v1.2: sub-score 5 mức (0/25/50/75/100); phân loại HITL-trigger dimensions (DIM-3.7, DIM-3.9 sensitive action, DIM-4.4, DIM-4.5); cập nhật Output JSON Schema (hitl_required, hitl_triggers, type field); scoring logic tách score-based vs hitl-trigger; verdict override khi hitl_required*
*Cập nhật: 04/2025 — v1.3: DIM-3.4 thêm ngoại lệ mã promo/voucher alphanumeric (EMCHUA18, SALE50...) không bị flag ALL CAPS; DIM-3.10 mở rộng áp dụng Group Ưu đãi/Tương tác, định nghĩa CTA theo pattern [động từ]+ngay thay whitelist cứng*
*Cập nhật: 04/2025 — v1.4: DIM-3.4 bổ sung ngoại lệ (5) mã thuần chữ hoa trong context promo (CUOITUAN) và (6) tên thương hiệu đối tác Latin (NESCAFE, MAGGI); DIM-3.4c làm rõ phân công với Rule 2.2 — không re-check dấu !! đã có ở Tier 1, chỉ check lỗi dấu câu cần judgment*
*Cập nhật: 04/2025 — v1.5: DIM-3.7 thêm carve-out game mechanic ("100% trúng/nhận" khi có cơ chế vòng quay/gạch thẻ) + tách FOMO phrases sang DIM-3.17; thêm 4 dimensions mới từ BMC Campaign XL Best Practice: DIM-3.15 (Personalization token — advisory), DIM-3.16 (Number specificity — advisory), DIM-3.17 (FOMO validation — score-based WARNING), DIM-3.18 (Segment-title alignment — advisory); thêm loại dimension "advisory" vào system prompt và schema*
*Cập nhật: 04/2026 — v1.6: bỏ hoàn toàn reference UC-XX khỏi prompt và system context — Campaign context block dùng Content Type + Group; DIM triggers rewrite theo content_type/group (DIM-3.6/3.10/3.12/3.15/3.17); Tone mapping theo Group Quan trọng/Ưu đãi/Tương tác; HITL routing note update theo content_type + group.*
*Cập nhật: 04/2026 — v1.7: DIM-3.4b (Spelling check) elevate score-based → HITL-trigger; bất kỳ typo VN/EN hoặc suspected proper noun → `hitl_triggered: true`, không đóng góp score, orchestrator override verdict thành `HITL_REQUIRED`; cập nhật bảng phân loại dimensions, DIM-3.4b section thêm cơ chế HITL + JSON output template, Output JSON Schema example đổi sang hitl-trigger format.*
*Cập nhật: 04/2026 — v1.8: Thêm **Regulatory floor** trong verdict mapping — nếu bất kỳ `DIM-4.1/4.2/4.3/4.6/4.7/4.8` (regulatory/compliance score-based) có `sub_score ≤ 25` → force `verdict = HITL_REQUIRED` bất kể overall_score ≥ 80. Vị trí check: sau HITL-trigger override, trước score thresholds. Đảm bảo vi phạm regulatory (claim absolute "tuyệt đối/nhất", fintech cashback mập mờ, bảo hiểm thiếu scope, airfare thiếu disclaimer…) không bị averaged out bởi các dim khác đạt 100.*
*Cập nhật: 04/2026 — v1.9: **(1) DIM-3.16 promote từ advisory → score-based (w=1)** — 5-tier sub-score catch vague claims không có số cụ thể ("hấp dẫn", "lớn", "khủng"). (2) **DIM-4.1 rewrite** scope — chỉ absolute superlatives ("tốt nhất/duy nhất/nhất/tuyệt đối/đảm bảo/số 1"); sub_score 0 → Reg-floor HITL. (3) **DIM-4.8 expanded** — thêm sub_score 25 cho vague cashback ("hoàn tiền hấp dẫn" không số) + sub_score 0 cho % cụ thể zero conditions — cả 2 trigger Reg-floor. (4) **DIM-3.7 clarify scope** — chỉ promotional claims với số cụ thể thiếu điều kiện, phân biệt rõ với DIM-3.16/4.1. Thêm Reg-floor eligible flag vào header các DIM-4.x liên quan.*
*Cập nhật: 04/2026 — v1.10: **DIM-4.9 NEW — MoMo Financial Services product wording**. Reg-floor eligible. Scope: 4 sản phẩm BOM Legal-review (Túi Thần Tài / Vay Nhanh + Newton / Ví Trả Sau / hợp tác BU khác). Check 3 nhóm: (A) vai trò MoMo (cấm "X của/do MoMo cung cấp"), (B) product blacklist per product (TTT cấm "tiết kiệm", Vay Nhanh cấm "đầu tư"/"hạn mức", VTS cấm "nhận ngay"), (C) approved wording. Sub-score 0/25 → Reg-floor HITL→BMC. Detection patterns embedded ở `05-guardrail v1.9 Rule 4.9` JSON code block (single source of truth). Disclaimer KHÔNG enforce trong noti body (char limit) — clarify cho engineer.*
*Cập nhật: 05/2026 — v1.11: **Fix P0-2 + refactor Reg-floor về single source of truth.** Bug: DIM-4.9 add ở v1.10 với label `[Reg-floor eligible]` nhưng quên append vào hardcoded list trong `regulatory_floor_triggered` check → DIM-4.9 sub_score ≤25 không trigger HITL như intended, FS wording vi phạm có thể auto-approve (surface qua eval 21/05/2026, xem `EVAL_REPORT_2026-05-21.md`). Fix: (1) Tách `REG_FLOOR_DIMS` + `REG_FLOOR_THRESHOLD` thành constants block riêng phía trên score calculation — single source of truth. (2) Append `DIM-4.9` vào constant. (3) Refactor `regulatory_floor_triggered` để reference `REG_FLOOR_DIMS` + `REG_FLOOR_THRESHOLD` (không còn hardcode). (4) Add convention note: label `[Reg-floor eligible]` ở DIM header = contract phải có entry tương ứng trong constant. (5) Fix header version (đã stale ở v1.7 từ trước, sync lên v1.11 match filename). Cross-file: bump `skill/noti-campaign-approval.md` v1.4.4 → v1.4.5 (Tier C section add DIM-4.9), update `README.md` Tier C list, `library.md` v1.4 → v1.5, `SKILL.md` v1.6.3 → v1.6.4 (patch — distributed bundle content change). Rebuild install zip v1.6.4.*
*Cập nhật: 07/2026 — v1.11.3: **Wire DIM-1.6 (Content type semantic consistency) thành dimension chấm điểm.** Trước đó Rule 1.6 chỉ là spec trong `01-content-type-format.md` tự khai "Reg-floor eligible" nhưng judge KHÔNG có dimension tương ứng → reg-floor cho 1.6 không được thực thi. Fix: (1) thêm section `[DIM-1.6]` (Nhóm 1, weight=1, `[Reg-floor eligible]`) với sub-score 2-axes 100/75/50/25/0; (2) thêm `DIM-1.6` vào inventory score-based + `REG_FLOOR_DIMS`; (3) tổng quát hóa convention note (không chỉ DIM-4.x). Đồng bộ `02-content-hard-checks.md` Rule 2.7 priority. Mục đích: chống lách nhóm duyệt (gắn nội dung khuyến mãi thành REMIND để né BMC).*
*Dựa trên: 05-guardrail-rule-sheet_v1.7.md + MoMo UX Writing Guide (04/2025)*
*File liên quan: skill_v2.1.md · 06-hitl-policy_v1.4.md · assets/ux-writing-guide_v1.0.md*
