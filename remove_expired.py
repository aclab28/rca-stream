import json
from datetime import datetime, timezone

f = '/home/ubuntu/listings.json'
d = json.load(open(f))

now = datetime.now(timezone.utc)

def is_expired(listing):
    expiry = listing.get('expiry', '')
    if not expiry:
        return False
    # Strip any non-date characters
    expiry = expiry.strip().replace('⏰', '').replace('Expires:', '').strip()
    try:
        dt = datetime.fromisoformat(expiry).replace(tzinfo=timezone.utc) if len(expiry) == 10 else datetime.fromisoformat(expiry.replace('Z', '+00:00'))
        return dt < now
    except:
        return False

active  = [l for l in d if not is_expired(l)]
expired = len(d) - len(active)

print(f'Removed {expired} expired listings, {len(active)} remain')
json.dump(active, open(f, 'w'), indent=2)
print('Done')
