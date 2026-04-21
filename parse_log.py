import re, json, os

log = open(os.path.expanduser('~/rca_listings.log')).read()
blocks = re.split(r'={10,}', log)
listings = []

for b in blocks:
    n = re.search(r'LISTING #\d+\n\[\S+ \S+\] (.+)', b)
    s = re.search(r'\] \xf0\x9f\x93\x81 (.+)', b)
    p = re.search(r'\] \xf0\x9f\x92\xb0 (.+)', b)
    m = re.search(r'\] \xf0\x9f\x92\xbc (.+)', b)
    e = re.search(r'Expires: (.+)', b)
    l = re.search(r'\] https://opensea\.io/\S+', b)
    if all([n, s, p, m, e, l]):
        listings.append({
            'name':      n.group(1).strip(),
            'slug':      s.group(1).strip(),
            'price':     p.group(1).strip(),
            'maker':     m.group(1).strip(),
            'expiry':    e.group(1).strip(),
            'link':      l.group(0).split('] ')[1].strip(),
            'image_url': '',
            'listed_at': '',
            'catchup':   False
        })

print(f'Found {len(listings)} listings')
with open(os.path.expanduser('~/listings.json'), 'w') as f:
    json.dump(listings, f, indent=2)
print('Saved')
