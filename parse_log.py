import re, json, os

log_path = os.path.expanduser('~/rca_listings.log')
lines = open(log_path).readlines()

def strip_ts(line):
    return re.sub(r'^\[\S+.*?\] ', '', line).strip()

listings = []
current = None

for line in lines:
    clean = strip_ts(line)

    if 'RCA LISTING #' in clean:
        if current and current.get('link'):
            listings.append(current)
        current = {
            'image_url': '',
            'listed_at': '',
            'catchup': '[CATCHUP]' in clean
        }

    elif current is not None:
        if clean and not clean.startswith('='):
            if 'name' not in current:
                current['name'] = clean
            elif 'slug' not in current:
                current['slug'] = clean
            elif 'price' not in current:
                current['price'] = clean
            elif 'maker' not in current:
                current['maker'] = clean
            elif 'expiry' not in current and 'Expires:' in clean:
                current['expiry'] = clean.replace('Expires:', '').strip()
            elif 'link' not in current and 'https://' in clean:
                current['link'] = clean

if current and current.get('link'):
    listings.append(current)

print(f'Found {len(listings)} listings')
with open(os.path.expanduser('~/listings.json'), 'w') as f:
    json.dump(listings, f, indent=2)
print('Saved')
