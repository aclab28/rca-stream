import json, os, requests, re, time

API_KEY   = "e42883f67023429590c1b7a8468eda67"
log_path  = os.path.expanduser('~/rca_listings.log')
list_path = '/home/ubuntu/listings.json'

# Load the current file (37 listings with images from GitHub)
old = json.load(open(list_path))

# Build image lookup by name
image_map = {l['name']: l['image_url'] for l in old if l.get('image_url')}
print(f"Image map has {len(image_map)} entries")

# Parse all listings from log
lines    = open(log_path).readlines()
listings = []
current  = None
current_ts = None

def strip_ts(line):
    return re.sub(r'^\[\S+.*?\] ', '', line).strip()

def clean(s):
    return re.sub(r'[^\x00-\x7F]+', '', str(s)).strip()

for line in lines:
    ts_match = re.match(r'^\[(\d{2}:\d{2}:\d{2})[^\]]*\]', line)
    if ts_match:
        current_ts = ts_match.group(1)

    c = strip_ts(line)
    if 'RCA LISTING #' in c:
        if current and current.get('link'):
            listings.append(current)
        current = {
            'image_url': '',
            'listed_at': '',
            'catchup':   '[CATCHUP]' in c
        }

    elif current is not None:
        if c and not c.startswith('='):
            if 'name' not in current:
                current['name'] = clean(c)
            elif 'slug' not in current:
                current['slug'] = clean(c)
            elif 'price' not in current:
                current['price'] = clean(c)
            elif 'maker' not in current:
                current['maker'] = clean(c)
            elif 'expiry' not in current and 'Expires:' in c:
                current['expiry'] = c.replace('Expires:', '').strip()
            elif 'link' not in current and 'https://' in c:
                m = re.search(r'https://\S+', c)
                if m:
                    current['link'] = m.group(0).strip()
                    from datetime import datetime, timezone
                    today = datetime.now(timezone.utc).strftime('%Y-%m-%d')
                    current['listed_at'] = f"{today}T{current_ts}Z" if current_ts else ''

if current and current.get('link'):
    listings.append(current)

print(f"Parsed {len(listings)} listings from log")

# Apply images from map first, then fetch missing ones
def fetch_image(link):
    try:
        m = re.search(r'opensea\.io/item/polygon/(0x[a-fA-F0-9]+)/(\d+)', link)
        if not m:
            print(f"    No contract match in: {link}")
            return ''
        contract, token = m.group(1), m.group(2)
        url = f"https://api.opensea.io/api/v2/metadata/polygon/{contract}/{token}"
        r = requests.get(url, headers={"accept": "*/*", "x-api-key": API_KEY}, timeout=10)
        if r.status_code != 200:
            print(f"    API error {r.status_code} for {contract}/{token}")
            return ''
        data = r.json()
        img = data.get("image", "")
        if not img:
            print(f"    No image field for {contract}/{token}: {list(data.keys())}")
        return img
    except Exception as e:
        print(f"    Exception: {e}")
        return ''

for i, listing in enumerate(listings):
    name = listing.get('name', '')
    if name in image_map and image_map[name]:
        listing['image_url'] = image_map[name]
        print(f"  {i+1}/{len(listings)} {name} — from cache")
    else:
        img = fetch_image(listing.get('link', ''))
        listing['image_url'] = img
        print(f"  {i+1}/{len(listings)} {name} — {'fetched' if img else 'no image'}")
        time.sleep(0.5)

json.dump(listings, open(list_path, 'w'), indent=2)
print(f'Done — {len(listings)} listings saved')
