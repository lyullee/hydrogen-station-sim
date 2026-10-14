import json
from pathlib import Path

root = Path(__file__).resolve().parents[1]
progress = json.loads((root / "unreal/progress.json").read_text(encoding="utf-8"))
done = ready = total = 0
for phase in progress["phases"]:
    count = sum(item["status"] == "verified" for item in phase["items"])
    prepared = sum(item["status"] in {"verified", "source_ready"} for item in phase["items"])
    size = len(phase["items"])
    done += count
    ready += prepared
    total += size
    print(f'{phase["name"]}: 검증 {count}/{size} ({100*count/size:.1f}%) · 소스 준비 {prepared}/{size} ({100*prepared/size:.1f}%)')
print(f"전체 검증 완료: {done}/{total} ({100*done/total:.1f}%)")
print(f"전체 소스 준비: {ready}/{total} ({100*ready/total:.1f}%)")
print("source_ready는 UE 빌드·화면·동작 검증 전까지 검증 완료율에 포함하지 않습니다.")
