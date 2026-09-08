"""Domain detection — Phase 2 helper (v1.4.0+).

Keyword scan title+body+CT → return list of domain guardrails cần load.

Idea: thay vì load full 70KB guardrail mỗi campaign, agent chỉ load domain rules
khi content matching keyword. Tránh waste context window cho rules không apply.

Domains:
    fs-products       — Rule 4.9 (TTT/Vay Nhanh/VTS) — 144 lines
    vietlott          — Rules 4.4, 4.5 — 21 lines
    airfare           — Rule 4.6 — 15 lines
    insurance         — Rule 4.7 — 15 lines
    cashback-fintech  — Rule 4.8 — 25 lines
    survey-cio        — Rule 6.5 — 210 lines

Always-load files (always in Phase 0):
    00-core-rules, 01-content-type-format, 02-content-hard-checks,
    03-content-quality, 04-regulatory-general, 05-segment, 06-routing

False-negative philosophy: keyword list inclusive. Khi nghi ngờ → load (rather safe).

Convention (v1.4.6+): Mỗi constant `_<DOMAIN>_KEYWORDS` dưới đây được mirror ở header file
references/<domain>.md ("Trigger keywords:" line). Khi add/đổi keyword:
    1. Update constant tại đây
    2. Update line "Trigger keywords:" trong file domain tương ứng cho audit-able
    3. Bump file domain version + library row §3 nếu rule logic cũng đổi
"""

# ─── Keyword lists per domain (lowercase for case-insensitive match) ──────────

_FS_PRODUCTS_KEYWORDS = {
    # Túi Thần Tài
    "túi thần tài", "tui than tai", "ttt",
    # Vay Nhanh (bao gồm Newton)
    "vay nhanh", "newton",
    # Ví Trả Sau
    "ví trả sau", "vi tra sau", "vts", "paylater", "trả sau",
    # General FS terms
    "tài chính số", "fs product",
}

_VIETLOTT_KEYWORDS = {
    "vietlott", "xổ số", "xo so", "vé số", "ve so", "lottery",
    "trúng số", "trung so", "jackpot",
}

_AIRFARE_KEYWORDS = {
    "vé máy bay", "ve may bay", "vé bay", "ve bay",
    "flight", "airline", "vietjet", "vietnam airlines", "bamboo airways",
}

_INSURANCE_KEYWORDS = {
    "bảo hiểm", "bao hiem", "insurance",
    "bh ô tô", "bh xe", "bh sức khỏe", "bh nhân thọ",
}

_CASHBACK_FINTECH_KEYWORDS = {
    "hoàn tiền", "hoan tien", "cashback",
    "lãi suất", "lai suat", "tích lũy", "tich luy",
}


def detect_domains(title: str, body: str, content_type: str) -> list[str]:
    """Return list of domain names cần load guardrail cho campaign này.

    Args:
        title: campaign caption
        body: campaign body
        content_type: API code (uppercase expected)

    Returns:
        List of domain names matching `references/<name>.md` files.
        Sorted alphabetical for deterministic output.
        Empty list = không cần load domain guardrail nào.
    """
    text_lower = ((title or "") + " " + (body or "")).lower()
    ct = (content_type or "").upper()
    domains: set[str] = set()

    # FS products
    if any(kw in text_lower for kw in _FS_PRODUCTS_KEYWORDS):
        domains.add("fs-products")

    # Vietlott
    if any(kw in text_lower for kw in _VIETLOTT_KEYWORDS):
        domains.add("vietlott")

    # Airfare
    if any(kw in text_lower for kw in _AIRFARE_KEYWORDS):
        domains.add("airfare")

    # Insurance
    if any(kw in text_lower for kw in _INSURANCE_KEYWORDS):
        domains.add("insurance")

    # Cashback / Fintech
    if any(kw in text_lower for kw in _CASHBACK_FINTECH_KEYWORDS):
        domains.add("cashback-fintech")

    # SURVEY — driven by CT, not keyword
    if ct == "SURVEY":
        domains.add("survey-cio")

    return sorted(domains)


def get_domain_file_paths(domains: list[str]) -> list[str]:
    """Convert domain names → guardrail file paths cho agent load.

    Returns:
        List of `references/<name>.md` paths.
    """
    return [f"references/{d}.md" for d in domains]


# ─── CLI helper for debugging ────────────────────────────────────────────────

if __name__ == "__main__":
    import json
    import sys

    if len(sys.argv) < 2:
        print("Usage: python detect_domain.py '<json with title/body/content_type>'")
        sys.exit(1)

    data = json.loads(sys.argv[1])
    domains = detect_domains(
        data.get("title", ""),
        data.get("body", ""),
        data.get("content_type", "")
    )
    print(json.dumps({
        "domains": domains,
        "files_to_load": get_domain_file_paths(domains),
    }, ensure_ascii=False, indent=2))
