import json
import shutil
import sys
import os
from datetime import datetime

LISTINGS_FILE = '/home/ubuntu/listings.json'
BACKUP_DIR    = '/home/ubuntu/backups'

def remove_newest_duplicate(name):
    os.makedirs(BACKUP_DIR, exist_ok=True)

    # Load
    with open(LISTINGS_FILE) as f:
        listings = json.load(f)

    # Find matches
    matches = [(i, l) for i, l in enumerate(listings) if l.get('name', '') == name]

    if len(matches) == 0:
        print(f'No listings found with name: {name}')
        return

    if len(matches) == 1:
        print(f'Only one listing found for: {name} — nothing to remove')
        return

    print(f'Found {len(matches)} listings for: {name}')
    for i, l in matches:
        print(f'  Index {i}: {l.get("listed_at","")} — {l.get("price","")}')

    # Sort by listed_at, newest last
    matches.sort(key=lambda x: x[1].get('listed_at', ''))
    newest_index = matches[-1][0]
    newest       = matches[-1][1]

    print(f'\nWill remove newest: index {newest_index} listed at {newest.get("listed_at","")}')
    print(f'Will keep oldest:   index {matches[0][0]} listed at {matches[0][1].get("listed_at","")}')

    # Backup
    ts      = datetime.now().strftime('%Y%m%d_%H%M%S')
    backup  = os.path.join(BACKUP_DIR, f'listings.json.{ts}.bak')
    shutil.copy2(LISTINGS_FILE, backup)
    print(f'\nBackup saved: {backup}')

    # Remove only the newest duplicate
    result = [l for i, l in enumerate(listings) if i != newest_index]

    print(f'Before: {len(listings)}, After: {len(result)}')

    # Save atomically
    tmp = LISTINGS_FILE + '.tmp'
    with open(tmp, 'w') as f:
        json.dump(result, f, indent=2)
    os.replace(tmp, LISTINGS_FILE)

    print('Done')

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print('Usage: python3 remove_duplicate.py "Listing Name"')
        sys.exit(1)
    remove_newest_duplicate(' '.join(sys.argv[1:]))
