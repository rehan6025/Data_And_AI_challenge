import json

with open("./docs/candidates.jsonl", "r", encoding="utf-8") as f:
    first = json.loads(f.readline())

print("TOP-LEVEL KEYS:")
for k in first.keys():
    val = first[k]
    if isinstance(val, list):
        print(f"  {k}: list[{len(val)}]")
    elif isinstance(val, dict):
        print(f"  {k}: dict with keys {list(val.keys())}")
    elif isinstance(val, str):
        print(f"  {k}: str (sample: {val[:80]!r})")
    else:
        print(f"  {k}: {type(val).__name__} = {val}")

print("\nFULL FIRST RECORD:")
print(json.dumps(first, indent=2)[:3000])