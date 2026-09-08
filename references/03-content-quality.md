# 03 — Content Quality (LLM Judge Input)
## Noti Campaign Agent — Group Nhóm 3

> **Phiên bản:** v1.17 — 06/2026 (add cross-ref Rule 2.14 ở 3.4b — brand "MoMo" sai = hard block Tier 1)
> **Scope:** Rules 3.1 – 3.18 (Title quality, body, capitalization, spelling, emoji, CTA, FOMO, segment-title alignment)
> **Load:** Always (Tier 2 LLM Judge input — file 07 reference)
> **Script coverage:** None — toàn bộ Tier 2 LLM. Rule 3.5b emoji modern + 3.4b spelling cần LLM identify.

---

## Nhóm 3 — Content Quality (LLM Judge Input)

> Các rule sau đây là **input dimensions cho LLM Judge** (file 07-llm-judge-prompt). LLM Judge trả về score 0–100 và danh sách issues. Chi tiết rubric xem file 07.

### Rule 3.1 — Title mang thông tin quan trọng nhất
- **Tier:** 🟡 LLM
- **Nguồn:** Content Guideline 2025 tr.17–22
- **Câu hỏi cho LLM:** Title có nêu được lợi ích/nội dung chính của noti không? (VD: "eSIM du lịch giảm 50%" đúng; "Có hẹn với mùa hoa anh đào" sai)

### Rule 3.2 — Body bổ sung cho title, không lặp lại
- **Tier:** 🟡 LLM
- **Nguồn:** Content Guideline 2025 tr.23–25
- **Câu hỏi cho LLM:** Body có cung cấp thông tin mới (điều kiện, hạn dùng, cách thực hiện) hay chỉ nhắc lại title?

### Rule 3.3 — Không viết tắt từ ngữ phổ thông
- **Tier:** 🟡 LLM
- **Nguồn:** Content Guideline 2025 tr.28
- **Câu hỏi cho LLM:** Có từ viết tắt nào không phải tên riêng/thương hiệu không? (VD: "TKKM", "TKNH", "KM")

### Rule 3.4 — Viết hoa đúng chính tả
- **Tier:** 🟡 LLM
- **Nguồn:** Content Guideline 2025 tr.27
- **Câu hỏi cho LLM:** Có từ thông thường bị viết hoa toàn bộ không? (VD: "HOÀN TIỀN", "DEAL HOT", "ƯU ĐÃI")

### Rule 3.4b — Kiểm tra chính tả tiếng Việt và tiếng Anh
- **Tier:** 🟡 LLM (HITL-trigger — v2.7+)
- **Câu hỏi cho LLM:** Scan toàn bộ title và body (sau khi đã bỏ qua các biến `${fullname}`, `${lastname}` và tên thương hiệu/dịch vụ) và thực hiện:
  1. **Tiếng Việt:** Phát hiện từ sai dấu thanh, thiếu dấu, hoặc dùng sai từ (VD: "hoàm tiền" → "hoàn tiền", "đăng kí" → "đăng ký", "riênh" → "rinh")
  2. **Tiếng Anh:** Phát hiện lỗi spelling thông thường (VD: "recieve" → "receive", "cashbak" → "cashback")
  3. **Tên riêng không rõ:** Nếu gặp từ viết hoa không khớp với tên thương hiệu/dịch vụ đã biết và nghi ngờ là tên riêng → **HITL-trigger** để approver xác nhận
- **Hành động khi phát hiện lỗi (v2.7+):** **HITL bắt buộc — block auto-approve.** DIM-3.4b set `hitl_triggered: true`, orchestrator override verdict thành `HITL_REQUIRED` bất kể score Tier 2 LLM. Approver review checklist lỗi cụ thể + gợi ý sửa, sau đó:
  - Approver xác nhận typo thật → yêu cầu owner fix + resubmit
  - Approver xác nhận false positive (slang/regional/brand mới) → approve thủ công với note giải thích
- **Hành động khi gặp tên riêng nghi ngờ:** Same as trên — HITL với `hitl_reason: "Từ '[X]' có vẻ là tên riêng hoặc tên dịch vụ — approver xác nhận cách viết đúng trước khi approve."`
- **Lưu ý:** Không flag các từ là tên thương hiệu đã biết (MoMo, Vietlott, Highlands, MobiFone, VinID, Grab, Shopee, VNPay, Moca, v.v.) và không flag các biến `${fullname}`, `${lastname}`. **Danh sách brand được maintain external `assets/brand-dictionary.json`** (field `known_partner_brands[]`) — team content update brand mới qua JSON, không cần thay skill code.
- **⚠️ Cross-ref Rule 2.14 (v1.19+):** Whitelist brand ở đây chỉ áp dụng cho tên viết **ĐÚNG**. Tên "MoMo" viết **SAI** (Mô Mô, Momo, MOMO, Mo Mo, ...) bị **hard block bởi Rule 2.14** (Tier 1 deterministic), KHÔNG đi qua spelling judgment mềm của 3.4b. Đừng coi "Mô Mô" là brand hợp lệ để bỏ qua.
- **Routing HITL:** Theo Group/Content Type của campaign — xem 06-hitl-policy_v1.9.md (Decision Matrix row "Tier 2 LLM phát hiện typo").

### Rule 3.5 — Emoji đúng vị trí và có dấu cách (v1.13+ — expanded)
- **Tier:** 🟡 LLM
- **Nguồn:** Content Guideline 2025 tr.34 + BMC Rule #20.0
- **Câu hỏi cho LLM (3 sub-checks):**
  1. **Vị trí cuối câu:** Emoji có đứng ở cuối câu/cuối Title/cuối Body không? (canonical position theo Content Guideline)
  2. **Dấu cách:** Có dấu cách giữa text và emoji không? (VD: "Nhận ngay 50K 🎁" OK, "Nhận ngay 50K🎁" sai)
  3. **Không đầu Title/Body (BMC sub-rule):** Emoji KHÔNG được đứng đầu Title hoặc Body. (VD: "🎁 Nhận ngay 50K" sai → flag; "Nhận ngay 50K 🎁" OK)
- **Tag (Phase 5):** `emoji_at_start` (sub-check 3)

### Rule 3.5b — Emoji render compatibility (Unicode version check)
- **Tier:** 🟡 LLM (HITL re-confirm khi gặp Unicode modern)
- **Nguồn:** BMC Rule #20.0 — *"Emoji phải render đúng trên iOS & Android; tránh emoji mới (Unicode 15+)"*
- **Trigger:** Title hoặc Body có emoji
- **Câu hỏi cho LLM (pretrained knowledge — không cần external file):**
  *"Có emoji nào thuộc Unicode 14+ (released sau 2021) không? Reference safe cutoff = Unicode 13.0 (Sep 2020) — emoji ra trước thì OK trên mọi device hiện hành; emoji ra sau có thể render lỗi (□) trên iOS < 15.4 hoặc Android < 12."*
- **Examples flag (Unicode 14-16):**
  - 🫠 🫥 🫡 🫢 🫣 (Unicode 14 — 2021): iOS 15.4+, Android 12+
  - 🩷 🩵 🩶 🪻 🪼 (Unicode 15 — 2022): iOS 16.4+, Android 13+
  - 🐦‍🔥 🍋‍🟩 (Unicode 15.1 — 2023): iOS 17.4+ only
  - 🫟 🪾 (Unicode 16 — 2024): iOS 18+ only
- **Safe baseline:** Unicode 13.0 trở về trước (5+ năm phổ biến, mọi device support).
- **Logic:** Phát hiện emoji modern → HITL re-confirm (không hard block — approver quyết có chấp nhận render risk không).
- **HITL message:** `"Phát hiện emoji '[X]' thuộc Unicode [version]+ — có thể render lỗi (□) trên device cũ. Approver xác nhận có chấp nhận render risk không?"`
- **Tag (Phase 5):** `emoji_unicode_modern`
- **Implementation note:** **Không có external file** — chỉ là câu hỏi cho LLM dùng pretrained knowledge. Rule 3.5b là **lightest implementation** — không file maintain, không codepoint table, không regex pattern. Trade-off: LLM có thể miss emoji ít phổ biến, accept rate false negative thấp vì approver có HITL chốt cuối.

### Rule 3.6 — Không dùng emoji cảnh báo cho noti Ưu đãi
- **Tier:** 🟡 LLM
- **Nguồn:** Content Guideline 2025 tr.33
- **Áp dụng khi:** `group = Ưu đãi` (PROMOTION*, GAME, ADVERTISING, EVENT)
- **Câu hỏi cho LLM:** Có dùng emoji cảnh báo (⚠️ ❗ ‼️ 🚨) không?

### Rule 3.7 — Không gây hiểu lầm về điều kiện ưu đãi (promotional claims)
- **Tier:** 🟡 LLM (HITL-trigger khi gặp sensitive action)
- **Nguồn:** Content Guideline 2025 tr.14
- **Scope (v1.8+ — phân biệt rõ với Rule 4.1):** Rule 3.7 tập trung vào **promotional claims có con số cụ thể** mà thiếu điều kiện, hoặc claim chắc chắn về kết quả ưu đãi.
- **Câu hỏi cho LLM:**
  - Có con số lợi ích (%, số tiền, bội số) mà thiếu điều kiện áp dụng không? VD: "Hoàn 50%" (0) vs "Hoàn 50% tối đa 100k đơn đầu" (100)
  - Có claim chắc chắn về kết quả ("đảm bảo trúng", "100% nhận được", "cam kết lợi nhuận") không?
- **Carve-out — Game mechanic:** "100% trúng/nhận" KHÔNG vi phạm khi có cơ chế game cụ thể đi kèm (vòng quay, gạch thẻ cào, mini-game). Đây là thể lệ game đã xác định, không phải claim tài chính tùy tiện.
- **Phân biệt với các Rule liên quan:**
  - **Rule 3.7** (đây) = promotional claims với số cụ thể thiếu điều kiện
  - **Rule 4.1** = absolute product claims ("tốt nhất", "duy nhất", "tuyệt đối") — xem dưới
  - **Rule 3.17** = FOMO phrases thuần túy ("kẻo hết", "giờ vàng") không có số cụ thể
  - **Rule 3.16** = vague claims không có số ("hấp dẫn", "nhiều ưu đãi", "lớn") — promoted thành score-based v1.8

### Rule 3.8 — Không dùng từ ngữ tiêu cực không kèm giải pháp
- **Tier:** 🟡 LLM
- **Nguồn:** Athena Notification Guideline tr.6, Content Guideline 2025 tr.15
- **Câu hỏi cho LLM:** Có từ ngữ gây áp lực/tiêu cực mà không đi kèm giải pháp tích cực không?
- **Danh sách từ tiêu cực tham chiếu (extensible — maintain `assets/negative-words.json`):**
  - Tài chính: "bị phạt", "mất tiền", "trễ hạn", "quá hạn", "lãi suất cao", "nợ xấu"
  - Tài khoản: "bị khóa", "bị đình chỉ", "bị chặn", "bị hủy", "bị thu hồi"
  - Pháp lý: "vi phạm", "xử phạt", "truy cứu", "tố cáo"
  - Cảm xúc: "mất cơ hội", "lỡ mất", "tiếc nuối", "hối hận"
- **Pass pattern:** từ tiêu cực + solution trong cùng câu/cụm. VD: "Hệ thống bảo trì 22:00–23:00. Vui lòng hoàn thành giao dịch trước 22:00" (OK).
- **Implementation note:** Brand/negative-word dict load external JSON để team content có thể extend mà không cần thay skill code.

### Rule 3.9 — Angle phù hợp với content type
- **Tier:** 🟡 LLM
- **Nguồn:** Content Guideline 2025 tr.8–13
- **Câu hỏi cho LLM:** Angle được dùng có phù hợp với content type không?
  - Group Ưu đãi (Khuyến mãi*, Game, Quảng cáo, Sự kiện) → Benefits-driven, Urgency, Exclusive, Personalized, Gamification
  - Group Quan trọng (Giao dịch, Nhắc nhở, Cảnh báo, Dịch vụ) → không dùng Gamification hay Emotional Connection
  - Group Tương tác (Bạn bè, Business Page, Social, Khảo sát) → Engagement, Content-driven

### Rule 3.10 — CTA rõ ràng
- **Tier:** 🟡 LLM
- **Nguồn:** Detail Guideline (CTA = Y cho Dịch vụ/Nhắc nhở) + BMC Campaign XL Best Practice (CTA cho Ưu đãi/Tương tác)
- **Áp dụng khi (v1.8+ — sync với 07-llm-judge v1.2):** `content_type IN [SERVICE, REMIND]` HOẶC `group IN [Ưu đãi, Tương tác]` trừ `SURVEY`
- **Câu hỏi cho LLM:** Body có chứa động từ hành động rõ ràng không (pattern `[động từ]+ngay` hoặc CTA implicit)?
- **Ví dụ pass:** "Mở ngay", "Mua ngay", "Xem chi tiết ngay", "Đăng ký ngay", "Nhận ngay", "Nhấn vào đây"
- **Ví dụ fail:** Body chỉ mô tả ưu đãi/tình huống mà không có lời kêu gọi hành động nào

### Rule 3.11 — Không xâm phạm quyền riêng tư
- **Tier:** 🟡 LLM
- **Nguồn:** Content Guideline 2025 tr.16
- **Câu hỏi cho LLM:** Nội dung có đề cập hành vi cá nhân quá chi tiết theo kiểu "theo dõi" không? (số tiền giao dịch cụ thể vừa xảy ra, địa điểm, thời gian thao tác vừa rồi)

### Rule 3.12 — WARNING/SERVICE Bảo trì: push time hợp lệ
- **Tier:** 🟡 LLM
- **Nguồn:** Detail Guideline (Cảnh báo / Dịch vụ — bảo trì)
- **Áp dụng khi:** `content_type IN [WARNING, SERVICE]`
- **Câu hỏi cho LLM:** Nội dung có đề cập thời gian bảo trì cụ thể không? Nếu có, push time đề xuất có đảm bảo trước thời điểm bảo trì ít nhất 24h không?

### Rule 3.15 — Personalization token
- **Tier:** 🟡 LLM (Advisory)
- **Nguồn:** BMC Campaign XL Best Practice
- **Áp dụng khi:** Group Ưu đãi (Khuyến mãi*, Game, Quảng cáo, Sự kiện) hoặc Tương tác (Bạn bè, Business Page, Social — trừ SURVEY)
- **Câu hỏi cho LLM:** Title hoặc body có sử dụng biến cá nhân hoá (`${fullname}`, `${lastname}`) không?
- **Advisory:** Không ảnh hưởng score. Gợi ý thêm personalization nếu thiếu — CTR tăng đáng kể khi có personalization token trong title.

### Rule 3.16 — Độ cụ thể của con số (PROMOTED từ Advisory → Score-based v1.9)
- **Tier:** 🟡 LLM (Score-based, weight = 1)
- **Nguồn:** BMC Campaign XL Best Practice
- **Câu hỏi cho LLM:** Nội dung có dùng cụm mơ hồ ("nhiều ưu đãi", "ưu đãi lớn", "hấp dẫn", "tuyệt vời", "khủng") thay vì số cụ thể (50K, 20%, 3 ưu đãi) không?
- **Sub-score:**
  - **100:** Có ≥ 1 số cụ thể trong title/body (50K, 20%, 3 ưu đãi, 87 tỷ…)
  - **50:** Có cụm mơ hồ nhưng đi kèm ≥ 1 anchor rõ (VD: "ưu đãi lớn" + "đến hết 30/4")
  - **25:** Chỉ có cụm mơ hồ không anchor ("hấp dẫn", "lớn", "khủng", "nhiều") — **fail**
- **Lý do promote v1.9:** Khi còn Advisory, các cụm như "hoàn tiền hấp dẫn", "nhiều ưu đãi" lọt qua score và auto-APPROVED. Promote score-based để catch vague claims này.
- **Phân biệt với Rule 3.7:** Rule 3.7 catch **có số cụ thể nhưng thiếu điều kiện**; Rule 3.16 catch **không có số nào hết** (vague).

### Rule 3.17 — FOMO validation
- **Tier:** 🟡 LLM (Score-based, WARNING)
- **Nguồn:** BMC Campaign XL Best Practice — Urgency Best Practice
- **Áp dụng khi:** Group Ưu đãi (Khuyến mãi*, Game, Quảng cáo, Sự kiện) và có cụm urgency
- **Câu hỏi cho LLM:** Nếu có cụm urgency, có kèm **anchor cụ thể** (deadline giờ cụ thể / số lượng còn lại / điều kiện kết thúc rõ ràng) không?
- **Ví dụ anchor rõ ràng (pass 100):**
  - "Chỉ còn 2h nữa" / "Đến 23:59 hôm nay" / "Hết hạn 30/04/2026 00:00"
  - "Chỉ còn 50 suất" / "100 vé cuối cùng"
  - "Tặng 100 đơn đầu tiên"
- **Ví dụ mơ hồ (score 50 nếu có ngày không giờ, 25 nếu không anchor):**
  - "Trong ngày hôm nay" (50 — có ngày, không giờ)
  - "Sớm nhất có thể" / "Kẻo lỡ" / "Đừng bỏ lỡ cơ hội" (25 — không anchor nào)
  - "Chỉ hôm nay" (50)
- **Score thresholds:**
  - **100:** Không có urgency phrase, HOẶC có urgency + anchor rõ ràng (giờ cụ thể / số lượng cụ thể)
  - **50:** Có urgency + có ngày nhưng thiếu giờ cụ thể
  - **25:** Urgency không kèm anchor nào → WARNING

### Rule 3.18 — Segment-title alignment
- **Tier:** 🟡 LLM (Advisory)
- **Nguồn:** BMC Campaign XL Best Practice — Segment Strategy
- **Áp dụng khi:** Có thông tin segment trong context (newbie, lapsed, loyal)
- **Câu hỏi cho LLM:** Title/body có nhắm đúng vào điểm quan tâm của segment không? (Newbie → prize focus; Lapsed → quay lại; Loyal → exclusive)
- **Advisory:** Không ảnh hưởng score. Gợi ý nếu title chưa phù hợp với insight của segment.

---

