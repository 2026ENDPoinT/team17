"""data/extracted/에 data/reviewed/의 사람 수정값을 덮어써서 화면용 scholarships.json 하나를 만든다.

실행: uv run python classifier/build.py [--out 경로]
입력: data/extracted/{bidx}.json, data/reviewed/{bidx}.json (있으면)
출력: web/public/scholarships.json (형식: data/scholarships.sample.json). '모집' 공지만 넣는다.

reviewed 파일에는 고칠 필드만 적는다. 예: {"deadline": "2026-11-20", "amount": {"value": 3000000}}
특별한 키: "exclude": true 이면 목록에서 뺀다.
"""

import argparse
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

from config import BUILD_OUT, EXTRACTED_DIR, REVIEWED_DIR

KST = timezone(timedelta(hours=9))
INTERNAL_KEYS = ["notice_kind", "notice_kind_reason", "content_hash", "exclude", "filtered_conditions"]  # 화면에 넘기지 않는 필드


def merge(base: dict, patch: dict) -> dict:
    """patch의 값으로 base를 덮어쓴다. 둘 다 dict인 필드는 안쪽까지 합친다."""
    result = dict(base)
    for key, value in patch.items():
        if key.startswith("_"):  # "_comment" 같은 메모는 무시
            continue
        if isinstance(value, dict) and isinstance(result.get(key), dict):
            result[key] = merge(result[key], value)
        else:
            result[key] = value
    return result


def load_items() -> list[dict]:
    items = []
    for path in sorted(EXTRACTED_DIR.glob("*.json")):
        item = json.loads(path.read_text(encoding="utf-8"))
        reviewed_path = REVIEWED_DIR / path.name
        if reviewed_path.exists():
            item = merge(item, json.loads(reviewed_path.read_text(encoding="utf-8")))
            item["reviewed"] = True
        if item.get("exclude") or item.get("notice_kind") != "모집":
            continue
        for key in INTERNAL_KEYS:
            item.pop(key, None)
        items.append(item)
    return items


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path, default=BUILD_OUT)
    args = parser.parse_args()

    items = load_items()
    data = {
        "version": 1,
        "generated_at": datetime.now(KST).isoformat(timespec="seconds"),
        "items": items,
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    reviewed = sum(1 for i in items if i.get("reviewed"))
    print(f"모집 공지 {len(items)}건 (검수 {reviewed}건) → {args.out}")


if __name__ == "__main__":
    main()
