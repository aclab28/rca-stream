import json
from datetime import datetime, timezone

f = '/home/ubuntu/listings.json'
d = json.load(open(f))

def normalize_ts(ts):
    if not ts:
        return ''
    try:
        # Parse and reformat to consistent UTC string
        dt = datetime.fromisoformat(ts.replace('Z', '+00:00'))
        return dt.astimezone(timezone.utc).strftime('%Y-%m-%dT%H:%M:%S')
    except:
        return ts

seen = set()
deduped = []

for l in d:
    link = l.get('link', '')
    ts   = normalize_ts(l.get('listed_at', ''))
    key  = f"{link}_{ts}"
    if key not in seen:
        seen.add(key)
        deduped.append(l)

print(f'Reduced from {len(d)} to {len(deduped)} ({len(d)-len(deduped)} duplicates removed)')
json.dump(deduped, open(f, 'w'), indent=2)
print('Done')
