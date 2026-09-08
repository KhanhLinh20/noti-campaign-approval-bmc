# 07 — LLM Judge Prompt — PROMO subset
## Noti Campaign Agent — Promotional content DIMs (lazy load)

> **Phiên bản:** v1.12 — 05/2026 (split from monolith v1.11)
> **Scope:** DIMs specific cho promotional content (CT ∈ PROMOTION* / GAME / ADVERTISING / EVENT)
> **Load:** Lazy — chỉ load khi content_type match promo group
> **Companion core:** `07-llm-judge-core_v1.12.md` (load đồng thời cho schema + universal DIMs)
> **Phối hợp với:**
> - DIM-4.8 (cashback) trong file này
> - DIM-4.9 (FS products) tách trong `07-llm-judge-domain_v1.12.md` vì cần keyword detect
>
> **DIMs covered:** 3.6 · 3.7 · 3.15 · 3.16 · 3.17 · 3.18 · 4.8 (7 DIMs)

---

## Dimensions — Promo subset

### Nhóm 3 — Content Quality (promotional-specific)

#### [DIM-3.6] No warning emoji for Ưu đãi
**Áp dụng khi:** Group = Ưu đãi (Khuyến mãi/Khuyến mãi dịch vụ/Khuyến mãi hết hạn/Game/Quảng cáo/Sự kiện)
**Câu hỏi:** Có dùng emoji cảnh báo không?
- ❌ Không được dùng: ⚠️ ❗ ‼️ 🚨 🔴 cho Group Ưu đãi/Quảng cáo

#### [DIM-3.7] No misleading offers — Không gây hiểu lầm điều kiện ưu đãi `[HITL-trigger]`

> **Cơ chế:** Agent không thể tự xác minh tính hợp lệ của claim (có thể là campaign đối tác hợp lệ). Nếu phát hiện dấu hiệu đáng ngờ → `hitl_triggered: true`, không tính vào score.

**Câu hỏi:** Nội dung có nêu con số lợi ích hoặc giải thưởng mà không có điều kiện rõ ràng không? Có claim chắc chắn tuyệt đối không?
- 🔵 HITL: "Nhận 100k không cần điều kiện" — không thể verify, cần Growth/approver xác nhận
- 🔵 HITL: "Đảm bảo hoàn 50%" — claim tuyệt đối, cần xác nhận với đối tác
- 🔵 HITL: "Khách hàng thứ X triệu nhận quà" — claim giải thưởng cần đối tác xác nhận
- ✅ Không trigger: "Hoàn 50k khi thanh toán lần đầu" — điều kiện nêu rõ, không cần xác minh thêm
- ✅ Không trigger: "Giảm 20% tối đa 100k" — có cap và điều kiện rõ ràng

**Carve-out — Game mechanic:** Cụm "100% trúng", "100% nhận", "chắc chắn trúng" **KHÔNG trigger** khi có cơ chế game cụ thể đi kèm (vòng quay, gạch thẻ cào, mini-game). Đây là thể lệ game đã xác định, không phải claim tài chính tùy tiện.
- ✅ Không trigger: "100% trúng thưởng khi quay vòng xoay" — game mechanic rõ ràng
- ✅ Không trigger: "Gạch thẻ cào — chắc chắn nhận quà" — cơ chế cào thẻ xác định
- 🔵 Vẫn HITL: "100% trúng thưởng" đứng một mình không có cơ chế — không xác minh được

**Lưu ý phân công:** Các cụm urgency/FOMO thuần túy ("kẻo hết", "giờ vàng", "hôm nay thôi") **KHÔNG thuộc DIM-3.7** — xem DIM-3.17 (FOMO validation).

#### [DIM-3.15] Personalization token — Sử dụng biến cá nhân hoá `[Advisory]`
**Nguồn:** BMC Campaign XL Best Practice
**Câu hỏi:** Title hoặc body có sử dụng biến cá nhân hoá không?

> **Advisory:** Dimension này không ảnh hưởng score. Chỉ ghi nhận và gợi ý nếu không có personalization — không block approve.

**Tại sao quan trọng:** Biến `${fullname}` hoặc `${lastname}` trong title tương quan với CTR cao hơn đáng kể so với nội dung generic.

**Kiểm tra:**
- ✅ Tốt: "${lastname} ơi, ưu đãi dành riêng cho bạn!" — personalized, tăng relevance
- ✅ Tốt: "Chào ${fullname}, ưu đãi mới đã sẵn sàng!" — cụ thể cho từng user
- 📝 Gợi ý: Title/body generic, không có biến cá nhân hoá → suggestion_note: "Cân nhắc thêm ${lastname} hoặc ${fullname} vào title/body để tăng CTR"
- ℹ️ Bỏ qua: Group Quan trọng (Giao dịch/Nhắc nhở/Cảnh báo/Dịch vụ) — personalization không phải ưu tiên cho nội dung hệ thống

**Whitelist biến Noti Campaign (v1.9+):** Chỉ có `${fullname}` và `${lastname}`. Các biến khác (firstname, amount, phone, email…) KHÔNG áp dụng cho Noti Campaign — xem Rule 2.6 trong `05-guardrail-rule-sheet_v1.8.md`.

**Output:**
```json
{
  "id": "DIM-3.15",
  "type": "advisory",
  "has_suggestion": true,
  "suggestion_note": "Không có biến cá nhân hoá. Cân nhắc thêm ${lastname} hoặc ${fullname} vào title để tăng CTR (best practice: CTR tăng đáng kể khi có personalization token)"
}
```

#### [DIM-3.16] Number specificity — Độ cụ thể của con số `[Score-based, promoted v1.9]`
**Nguồn:** BMC Campaign XL Best Practice
**Câu hỏi:** Nội dung có dùng số liệu cụ thể thay vì cụm từ mơ hồ không?

> **Score-based (v1.9+):** Promoted từ advisory → score-based, weight = 1. Lý do: các cụm vague ("hấp dẫn", "lớn", "khủng", "nhiều") trước đây lọt qua score và auto-APPROVED. Score-based giúp catch các trường hợp content mơ hồ.

**Tại sao quan trọng:** Số cụ thể (50.000đ, 3 ưu đãi, 7 ngày) tạo kỳ vọng rõ ràng và tăng độ tin cậy hơn cụm chung chung.

**Sub-score 5 mức:**
- **100:** Có ≥ 1 số cụ thể trong title/body (VD: "Hoàn 50K", "Giảm 20%", "3 ưu đãi", "87 tỷ", "tối đa 100K")
- **75:** Có số cụ thể nhưng chưa đầy đủ (VD: "tiết kiệm tới 200K" — có số nhưng thiếu điều kiện)
- **50:** Có cụm mơ hồ nhưng đi kèm ≥ 1 anchor cụ thể (VD: "ưu đãi lớn đến hết 30/4" — anchor = date)
- **25:** Chỉ có cụm mơ hồ không anchor nào ("hấp dẫn", "lớn", "khủng", "nhiều ưu đãi") — **fail**
- **0:** Content toàn bộ là mơ hồ, không có số hay anchor nào

**Phân biệt với Rule 3.7 và 4.1:**
- **DIM-3.16** (đây): vague claims KHÔNG có số ("hấp dẫn", "nhiều", "lớn")
- **DIM-3.7:** số cụ thể nhưng thiếu conditions ("Hoàn 50%" không cap)
- **DIM-4.1:** absolute superlatives ("tốt nhất", "duy nhất")

**Output:**
```json
{
  "id": "DIM-3.16",
  "type": "score-based",
  "applicable": true,
  "sub_score": 25,
  "issue": "Nội dung có cụm mơ hồ 'hoàn tiền hấp dẫn' không đi kèm số cụ thể hay anchor nào",
  "suggestion": "Thay bằng số cụ thể — VD: 'hoàn 10K mỗi giao dịch' hoặc 'hoàn tối đa 50K'"
}
```

#### [DIM-3.17] FOMO validation — Urgency phrase có cơ sở thực tế `[Score-based]`
**Nguồn:** BMC Campaign XL Best Practice — Urgency Best Practice
**Áp dụng khi:** Group = Ưu đãi hoặc Tương tác (trừ SURVEY)
**Câu hỏi:** Nếu có cụm urgency/FOMO, có kèm deadline hoặc cơ sở cụ thể không?

**Nguyên tắc:** FOMO hợp lệ khi có anchor thực tế (deadline, số lượng, thời gian cụ thể). FOMO không có cơ sở = tạo sự cấp bách giả → làm giảm tin tưởng.

**Phát hiện cụm urgency:**
- "kẻo hết", "sắp hết", "còn ít suất", "chỉ hôm nay", "giờ vàng", "flash sale", "đừng bỏ lỡ", "cuối cùng", "hôm nay thôi"

**Đánh giá:**
- sub_score 100: Không có cụm urgency — không cần kiểm tra
- sub_score 100: Có urgency + có anchor rõ ràng (deadline, số lượng cụ thể)
  - ✅ "Kẻo hết — chỉ còn 50 suất" → urgency có số lượng
  - ✅ "Flash sale đến 23:59 hôm nay" → urgency có deadline giờ cụ thể
  - ✅ "Giờ vàng 12:00 - 14:00" → urgency có khung giờ rõ
- sub_score 50: Có urgency + có anchor ngày nhưng mơ hồ ("hôm nay", "tuần này" không có giờ)
  - 📝 "Ưu đãi chỉ hôm nay" — biết ngày nhưng không rõ giờ kết thúc
- sub_score 25: Có urgency + **không có anchor** nào — FOMO hoàn toàn không có cơ sở
  - ❌ "Kẻo hết! Nhận ngay ưu đãi" — không rõ hết lúc nào, còn bao nhiêu suất
  - ❌ "Đừng bỏ lỡ cơ hội hiếm có" — claim hiếm có không có cơ sở

#### [DIM-3.18] Segment-title alignment — Title phù hợp với segment mục tiêu `[Advisory]`
**Nguồn:** BMC Campaign XL Best Practice — Segment Strategy
**Áp dụng khi:** Có thông tin segment trong context campaign (newbie, lapsed, loyal, v.v.)
**Câu hỏi:** Title/body có nhắm đúng vào điểm quan tâm của segment không?

> **Advisory:** Không ảnh hưởng score. Gợi ý khi phát hiện title chưa phù hợp với insight của segment.

**Mapping segment → góc tiếp cận hiệu quả:**
- **Newbie (user mới):** Tập trung vào **phần thưởng/quà tặng** cụ thể — không nhắc tên game hay cơ chế phức tạp
  - ✅ "Tân thủ nhận ngay 50K vào ví" — clear benefit
  - 📝 "Khám phá Túi Thần Tài ngay" — game name, newbie chưa biết → ít hấp dẫn
- **Lapsed (user ngủ đông):** Nhắc lại lợi ích đã từng dùng + ưu đãi "quay lại"
  - ✅ "Lâu rồi không gặp — hoàn 30K khi quay lại"
- **Loyal (user trung thành):** Exclusive feeling — "dành riêng", "ưu tiên", VIP perks
  - ✅ "Ưu đãi VIP dành riêng cho bạn"
- **Generic (không xác định segment):** Bỏ qua dimension này

**Output khi phát hiện mismatch:**
```json
{
  "id": "DIM-3.18",
  "type": "advisory",
  "has_suggestion": true,
  "suggestion_note": "Segment: Newbie — title đang nhắc tên game (Túi Thần Tài) mà user mới chưa quen. Cân nhắc đổi sang góc benefit cụ thể: 'Tân thủ nhận ngay [X]K vào ví'"
}
```

---

### Nhóm 4 — Regulatory (promo-specific)

#### [DIM-4.8] Fintech cashback with conditions `[Reg-floor eligible, expanded v1.9]`
**Áp dụng khi:** body hoặc title chứa từ khoá "hoàn tiền", "cashback", "lãi suất"
**Nguồn:** Quy định NHNN về ví điện tử

**Câu hỏi (v1.9+ — expanded scope):**
- (a) Nội dung nêu **% hoàn tiền / lãi suất cụ thể** mà không có điều kiện tối thiểu không?
- (b) Nội dung đề cập "hoàn tiền / cashback / lãi suất" kiểu **vague** ("hấp dẫn", "ưu đãi", "lớn", "khủng") mà **không có specifics** nào không?
- (c) Có ≥ 1 điều kiện rõ ràng (tối đa X, mỗi giao dịch, chỉ user mới, lần đầu…) không?

**Sub-score:**
- **100:** Có ≥ 1 điều kiện rõ ràng ("Hoàn 20% tối đa 100k cho giao dịch đầu tiên")
- **50:** Có % cụ thể nhưng điều kiện chưa đầy đủ ("Hoàn 20% cho đơn đầu" — thiếu cap)
- **25:** Vague cashback không specifics ("hoàn tiền hấp dẫn", "cashback ưu đãi", "lãi suất tốt") — **Reg-floor HITL**
- **0:** % cụ thể + zero conditions ("Hoàn 50% không giới hạn") — **Reg-floor HITL**

**Fail examples:**
- ❌ 0: "Hoàn 50% không giới hạn" (% cụ thể + không cap/điều kiện)
- ❌ 25: "Hoàn tiền hấp dẫn cho mỗi giao dịch" (vague + không số)
- ❌ 25: "Lãi suất ưu đãi" (vague, không %)
- ✅ 100: "Hoàn 20% tối đa 100k cho giao dịch đầu tiên"
- ✅ 100: "Lãi suất 6.5%/năm, kỳ hạn 12 tháng, áp dụng từ 01/5/2026"
