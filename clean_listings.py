import json, re

f = '/home/ubuntu/listings.json'
listings = json.load(open(f))

def clean(s):
    return re.sub(r'[^\x00-\x7F]+', '', str(s)).strip()

for l in listings:
    l['name']   = clean(l.get('name', ''))
    l['slug']   = clean(l.get('slug', ''))
    l['price']  = clean(l.get('price', ''))
    l['maker']  = clean(l.get('maker', ''))
    l['expiry'] = clean(l.get('expiry', ''))
    link = l.get('link', '')
    m = re.search(r'https://\S+', link)
    l['link'] = m.group(0) if m else link

json.dump(listings, open(f, 'w'), indent=2)
print(f'Cleaned {len(listings)} listings')
