import re, json, os, requests, base64

log_path = os.path.expanduser('~/rca_listings.log')
lines = open(log_path).readlines()

listings = []
current = {}

for line in lines:
    # Strip timestamp like [12:34:56 EDT]
    clean = re.sub(r'^\[\S+ \S+\] ', '', line).strip()

    if 'RCA LISTING #' in clean:
        if current and current.get('link'):
            listings.append(current)
        current = {'image_url': '', 'listed_at': '', 'catchup': '[CATCHUP]' in clean}

    elif current is not None:
        if clean.startswith('Name:') or (len(clean) > 2 and clean[1] == '\u200d' or True):
            # Try to match each field by position after emoji
            text = clean[2:].strip() if len(clean) > 2 else clean

            if 'name' not in current and not any(k in clean for k in ['📁','💰','💼','⏰','🔗','=']):
                if not any(c in clean for c in ['#','$','0x','https','Expires']):
                    current['name'] = clean

            elif '📁' in clean or clean.count('-') > 2 and 'reddit' in clean:
                current['slug'] = text

            elif '$' in clean and 'WETH' in clean:
                current['price'] = text

            elif '0x' in clean and '...' in clean:
                current['maker'] = text

            elif 'Expires:' in clean:
                current['expiry'] = clean.split('Expires:')[-1].strip()

            elif 'https://opensea.io' in clean:
                current['link'] = clean

if current and current.get('link'):
    listings.append(current)

print(f'Found {len(listings)} listings')
for l in listings[:3]:
    print(l)

with open(os.path.expanduser('~/listings.json'), 'w') as f:
    json.dump(listings, f, indent=2)
print('Saved')
