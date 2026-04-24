import json
import re

f = '/home/ubuntu/listings.json'
d = json.load(open(f))

def weth_amount(price):
    m = re.search(r'\(([0-9.]+) WETH\)', price)
    return m.group(1) if m else price

seen = {}
for l in d:
    key = f"{l.get('link','')}_{weth_amount(l.get('price',''))}_{l.get('maker','')}"
    if key not in seen:
        seen[key] = l
    else:
        existing_ts = seen[key].get('listed_at', '')
        current_ts  = l.get('listed_at', '')
        if current_ts > existing_ts:
            seen[key] = l

deduped = list(seen.values())
deduped.sort(key=lambda l: l.get('listed_at', ''))

print(f'Reduced from {len(d)} to {len(deduped)} ({len(d)-len(deduped)} duplicates removed)')
json.dump(deduped, open(f, 'w'), indent=2)
print('Done')
