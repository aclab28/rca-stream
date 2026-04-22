import json, os, requests, re, time

API_KEY   = "e42883f67023429590c1b7a8468eda67"
list_path = '/home/ubuntu/listings.json'

listings = json.load(open(list_path))
missing  = [l for l in listings if not l.get('image_url')]
print(f"Fetching images for {len(missing)} listings...")

def fetch_image(link):
    try:
        m = re.search(r'opensea\.io/item/polygon/(0x[a-fA-F0-9]+)/(\d+)', link)
        if not m:
            return ''
        contract, token = m.group(1), m.group(2)
        url = f"https://api.opensea.io/api/v2/metadata/polygon/{contract}/{token}"
        r = requests.get(url, headers={
            "accept": "*/*",
            "x-api-key": API_KEY
        }, timeout=10)
        if r.status_code != 200:
            return ''
        return r.json().get("image", "")
    except:
        return ''

fixed = 0
for i, listing in enumerate(listings):
    if listing.get('image_url'):
        continue
    link = listing.get('link', '')
    img  = fetch_image(link)
    if img:
        listing['image_url'] = img
        fixed += 1
        print(f"  Fixed: {listing.get('name','')} ")
    else:
        print(f"  No image: {listing.get('name','')} — {link[:60]}")
    time.sleep(0.3)

json.dump(listings, open(list_path, 'w'), indent=2)
print(f'Done — fixed {fixed} of {len(missing)} missing images')
