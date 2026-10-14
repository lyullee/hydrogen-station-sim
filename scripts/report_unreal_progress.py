import json
from pathlib import Path

root = Path(__file__).resolve().parents[1]
progress = json.loads((root / "unreal/progress.json").read_text(encoding="utf-8"))
done = total = 0
for phase in progress["phases"]:
    count = sum(item["status"] == "verified" for item in phase["items"])
    size = len(phase["items"])
    done += count
    total += size
    print(f'{phase["name"]}: {count}/{size} ({100*count/size:.1f}%)')
print(f"전체 검증 완료: {done}/{total} ({100*done/total:.1f}%)")
print("source_ready 항목은 UE 실행 검증 전까지 완료율에 포함하지 않습니다.")
