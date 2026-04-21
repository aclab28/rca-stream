import re, json, os, requests, time

API_KEY  = "e42883f67023429590c1b7a8468eda67"
log_path = os.path.expanduser('~/rca_listings.log')
lines    = open(log_path).readlines()

def strip_ts(line):
    return re.sub(r'^\[\S+.*?\] ', '', line).strip()

def fetch_image(link):
    try:
        m = re.search(r'opensea\.io/item/polygon/(0x[a-fA-F0-9]+)/(\d+)', link)
        if not m:
            return ''
        contract, token = m.group(1), m.group(2)
        url = f"https://api.opensea.io/api/v2/metadata/polygon/{contract}/{token}"
        r = requests.get(url, headers={"accept": "*/*", "x-api-key": API_KEY}, timeout=10)
        return r.json().get("image", "")
    except:
        return ''

listings = []
current  = None

for line in lines:
    clean = strip_ts(line)

    if 'RCA LISTING #' in clean:
        if current and current.get('link'):
            listings.append(current)
        current = {
            'image_url': '',
            'listed_at': '',
            'catchup':   '[CATCHUP]' in clean
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

print(f'Found {len(listings)} listings — fetching images...')

for i, listing in enumerate(listings):
    img = fetch_image(listing.get('link', ''))
    listing['image_url'] = img
    print(f"  {i+1}/{len(listings)} {listing['name']} — {'✅' if img else '❌'}")
    time.sleep(0.5)  # avoid rate limiting

with open(os.path.expanduser('~/listings.json'), 'w') as f:
    json.dump(listings, f, indent=2)
print('Done')
