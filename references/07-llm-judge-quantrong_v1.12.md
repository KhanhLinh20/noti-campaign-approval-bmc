# 07 — LLM Judge Prompt — QUAN TRỌNG subset
## Noti Campaign Agent — Service/Transaction content DIMs (lazy load)

> **Phiên bản:** v1.12 — 05/2026 (split from monolith v1.11)
> **Scope:** DIMs specific cho Group Quan trọng (CT ∈ TRANSACTION / REMIND / WARNING / SERVICE)
> **Load:** Lazy — chỉ load khi content_type match Quan trọng group
> **Companion core:** `07-llm-judge-core_v1.12.md` (load đồng thời cho schema + universal DIMs)
>
> **DIMs covered:** 3.9 · 3.10 · 3.12 (3 DIMs)

---

## Dimensions — Quan trọng subset

### Nhóm 3 — Content Quality (service-specific)

#### [DIM-3.9] Angle fit — Angle và Tone phù hợp với use case `[HITL-trigger khi phát hiện sensitive action]`

> **Cơ chế kép:**
> - **Score-based** (Angle/Tone fit): Sub-score bình thường, đóng góp vào weighted average
> - **HITL-trigger** (Sensitive action / Dark Pattern): Nếu phát hiện hành động nhạy cảm → `hitl_triggered: true`, không tính vào score

**Nguồn:** Content Guideline 2025 tr.8–13, UX Writing Guide — Tone
**Câu hỏi — Phần Score-based:** Angle và tone có phù hợp với content type và cảm xúc user không?

**Mapping angle → content type:**
- **Ưu đãi (Khuyến mãi/Khuyến mãi dịch vụ/Khuyến mãi hết hạn/Game/Quảng cáo/Sự kiện):** Benefits-driven ✅, Urgency ✅, Exclusive ✅, Personalized ✅, Gamification ✅
  - Tone: Enthusiastic, có thể Funny nhẹ
  - Không dùng: Emotional manipulation, tạo cấp bách giả (Dark Pattern)
- **Quan trọng (Giao dịch/Nhắc nhở/Cảnh báo/Dịch vụ):** Informative ✅, Clear action ✅
  - Tone: Serious, Matter-of-fact — không đùa khi user đang lo lắng
  - Không dùng: Gamification ❌, Emotional Connection ❌, Dấu "!" ❌
- **Tương tác (Bạn bè/Business Page/Social/Khảo sát):** Engagement ✅, Content-driven ✅
  - Tone: Friendly, không quá nghiêm túc

**Dark Pattern — Score-based (agent có thể đánh giá):**
- sub_score 0: Tạo sự cấp bách giả rõ ràng — "CHỈ CÒN 1 SUẤT!" khi không có cơ sở
- sub_score 0: Claim không có cơ sở — "Tốt nhất", "Duy nhất", "Đảm bảo"
- sub_score 25: Mập mờ về chi phí / điều kiện — không nêu rõ nhưng không claim sai

**Sensitive Action — HITL-trigger (agent không thể xác minh flow hợp lệ):**

> Nếu phát hiện BẤT KỲ dấu hiệu nào dưới đây → `hitl_triggered: true`, ghi rõ `hitl_reason`

- 🔵 HITL: Yêu cầu user **đổi mật khẩu / nhập OTP / cung cấp thông tin đăng nhập** — cần approver xác nhận đây là flow hợp lệ
- 🔵 HITL: Yêu cầu gọi **số điện thoại cụ thể** — cần xác nhận số hợp lệ của đối tác
- 🔵 HITL: Yêu cầu truy cập **link ngoài hệ thống MoMo** — cần xác nhận domain hợp lệ
- ✅ Không trigger: CTA thông thường như "Mở app", "Xem ngay", "Dán link", "Lấy ngay"

#### [DIM-3.10] CTA clarity — CTA rõ ràng cho Quan trọng/Dịch vụ, Quan trọng/Nhắc nhở, và content Ưu đãi/Tương tác
**Áp dụng khi:** content_type IN ["SERVICE", "REMIND"] hoặc group IN ["Ưu đãi", "Tương tác"] (trừ SURVEY)
**Câu hỏi:** Body có chứa động từ hành động rõ ràng không?

**Định nghĩa CTA hợp lệ:** Bất kỳ **[động từ hành động] + "ngay"** hoặc cụm từ thúc đẩy hành động rõ ràng đều được tính là CTA. Không giới hạn vào whitelist cứng.
- ✅ Pass — pattern `[động từ] + ngay`: "Mở ngay", "Mua ngay", "Trang bị ngay", "Thực hiện ngay", "Sở hữu ngay", "Bảo vệ ngay", "Gia hạn ngay", "Tải ngay", "Đăng ký ngay", "Khám phá ngay", v.v.
- ✅ Pass — CTA không có "ngay": "Mua thôi", "Đặt mua", "Nhấn vào đây để xem", "Mở app để cập nhật"
- ✅ Pass — CTA implicit trong câu cuối: "Thực hiện ngay!", "Trang bị thôi!"
- ❌ Fail: Body chỉ mô tả tình huống / ưu đãi mà không có bất kỳ lời kêu gọi hành động nào

#### [DIM-3.12] Maintenance timing — Push time trước bảo trì ít nhất 24h
**Áp dụng khi:** content_type IN ["WARNING", "SERVICE"] và body đề cập thời gian bảo trì
**Câu hỏi:** Nếu body đề cập thời gian bảo trì cụ thể, schedule_time có trước đó ít nhất 24h không?
- Parse thời gian bảo trì từ body (VD: "bảo trì từ 22h ngày 16/4/2025")
- So sánh với schedule_time
- ❌ Fail: Push lúc 20h cùng ngày cho bảo trì lúc 22h (chỉ còn 2h)
- ✅ Pass: Push lúc 10h ngày 15/4 cho bảo trì lúc 22h ngày 16/4 (còn 36h)
