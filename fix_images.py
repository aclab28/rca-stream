import json, os

LISTINGS_FILE = os.path.expanduser('~/listings.json')

fixes = {
    'Rudy':           'https://i2c.seadn.io/polygon/0xf6d634527c6454cecf242e43aec59c50f8e79b73/ff3e97f4b4916472bb7116fab4d3e1/8aff3e97f4b4916472bb7116fab4d3e1.png',
    'Stripes':        'https://i2c.seadn.io/polygon/0x2c2c60f114ae3c857bf301d1a1b6c3069d5308dc/6e59f8568b5f4e8cf9d09f404921cf/686e59f8568b5f4e8cf9d09f404921cf.png',
    'Plunger Rabbit': 'https://i2c.seadn.io/polygon/0x5066c0934632bcc2902d139d7c875cbd295429f8/ff21bb8625e0570e6e3eaa1e33c662/65ff21bb8625e0570e6e3eaa1e33c662.png',
}

with open(LISTINGS_FILE) as f:
    listings = json.load(f)

updated = 0
for listing in listings:
    for name, url in fixes.items():
        if name.lower() in listing.get('name', '').lower() and not listing.get('image_url'):
            listing['image_url'] = url
            print(f"Fixed: {listing['name']}")
            updated += 1

with open(LISTINGS_FILE, 'w') as f:
    json.dump(listings, f, indent=2)

print(f'Done — updated {updated} listings')
