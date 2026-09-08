"""Generate scripts/*_data.py từ assets/*.json — single source of truth vẫn là assets/.

Vì sandbox skill_script (E2B của athena-copilot) CHỈ ship file .py dưới scripts/
(assets/ KHÔNG được upload), các loader Rule 2.11/2.14 cần 1 bản data đóng gói
dạng Python để fall back khi assets/*.json không với tới được. File .py sinh ra
ở đây là bản COMPILE của assets/*.json — KHÔNG sửa tay; Legal cập nhật ở assets/
rồi chạy lại: `python scripts/gen_data.py`.

Chạy được ở mọi runtime (chỉ dùng stdlib).
"""
from pathlib import Path
import json

ROOT = Path(__file__).resolve().parents[1]
MAP = [
    ("banned-phrases.json", "banned_data.py"),
    ("brand-dictionary.json", "brand_data.py"),
]


def main() -> None:
    for src, out in MAP:
        src_path = ROOT / "assets" / src
        data = json.loads(src_path.read_text(encoding="utf-8"))
        body = (
            f"# AUTO-GENERATED from assets/{src} by scripts/gen_data.py — DO NOT EDIT BY HAND.\n"
            f"# Single source of truth = assets/{src}. Regenerate: python scripts/gen_data.py\n"
            f"DATA = {data!r}\n"
        )
        out_path = ROOT / "scripts" / out
        out_path.write_text(body, encoding="utf-8")
        print(f"wrote scripts/{out}  ({len(body.encode('utf-8'))} bytes  <- assets/{src})")


if __name__ == "__main__":
    main()
