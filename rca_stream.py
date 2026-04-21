#!/usr/bin/env python3
import websocket
import json
import threading
import time
import os
import smtplib
import urllib.request
import requests
import base64
import re
from datetime import datetime, timezone
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import pytz

API_KEY        = "e42883f67023429590c1b7a8468eda67"
LOG_FILE       = os.path.expanduser("~/rca_listings.log")
LISTINGS_FILE  = os.path.expanduser("~/listings.json")
EMAIL_TO       = "rca.lert1000@gmail.com"
EMAIL_FROM     = "rca.lert1000@gmail.com"
EASTERN        = pytz.timezone("America/New_York")
WETH_USD       = None
LISTING_COUNT  = 0
LAST_CONNECTED = None
MAX_LISTINGS   = 200

SMTP_HOST = "smtp.gmail.com"
SMTP_PORT = 587
SMTP_USER = "rca.lert1000@gmail.com"
SMTP_PASS = "pbgq axma hbxa moii"

GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN", "")
GITHUB_REPO  = "Aclab28/rca-stream"
GITHUB_FILE  = "listings.json"

def log(msg):
    ts   = datetime.now(pytz.utc).astimezone(EASTERN).strftime("%H:%M:%S %Z")
    line = f"[{ts}] {msg}"
    print(line, flush=True)
    try:
        with open(LOG_FILE, "a") as f:
            f.write(line + "\n")
    except:
        pass

def is_rca(slug):
    return "reddit" in slug.lower()

# ── Email ─────────────────────────────────────────────────────
def send_email(subject, html_body, to=None):
    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"]    = EMAIL_FROM
        msg["To"]      = to or EMAIL_TO
        msg.attach(MIMEText(html_body, "html"))
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
            server.ehlo()
            server.starttls()
            server.login(SMTP_USER, SMTP_PASS)
            server.sendmail(EMAIL_FROM, to or EMAIL_TO, msg.as_string())
        log(f"📧 Email sent to {to or EMAIL_TO}")
    except Exception as e:
        log(f"⚠️  Email failed: {e}")

def load_subscribers():
    path = os.path.expanduser("~/subscribers.txt")
    if not os.path.exists(path):
        return []
    with open(path) as f:
        return [line.strip() for line in f if line.strip()]

def broadcast_to_subscribers(name, price, link, image_url, slug, maker, expiry):
    subscribers = load_subscribers()
    if not subscribers:
        log("📭 No subscribers to broadcast to")
        return
    img_tag = f"<img src='{image_url}' style='width:120px;height:120px;object-fit:cover;border-radius:8px;float:right;margin-left:12px;'/>" if image_url else ""
    html = f"""
    <html><body style="background:#121212; padding:16px; font-family:sans-serif;">
    <h2 style="color:#2081e2;">🆕 New Reddit Avatar Listed</h2>
    <div style="background:#1e1e1e; border:1px solid #2a2a2a; border-radius:12px;
                padding:16px; max-width:500px; color:#e0e0e0;">
      {img_tag}
      <h3 style="margin:0 0 8px 0; color:white;">{name}</h3>
      <p style="font-size:16px; font-weight:700; color:#2081e2;">💰 {price}</p>
      <p style="font-size:12px; color:#888;">📁 {slug}</p>
      <p style="font-size:12px; color:#888;">💼 {maker}</p>
      <p style="font-size:12px; color:#888;">⏰ Expires: {expiry}</p>
      <div style="clear:both; margin-top:12px;">
        <a href="{link}" style="background:#2081e2; color:white; padding:8px 16px;
           border-radius:8px; text-decoration:none; font-size:13px;">
          View on OpenSea ↗
        </a>
      </div>
    </div>
    <p style="font-size:11px; color:#444; margin-top:16px;">
      You are receiving this because you subscribed at
      <a href="https://aclab28.github.io/rca-stream" style="color:#2081e2;">RCA Listings</a>.
    </p>
    </body></html>
    """
    subject = f"🆕 RCA Listed: {name} — {price}"
    for email in subscribers:
        try:
            msg = MIMEMultipart("alternative")
            msg["Subject"] = subject
            msg["From"]    = EMAIL_FROM
            msg["To"]      = email
            msg.attach(MIMEText(html, "html"))
            with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
                server.ehlo()
                server.starttls()
                server.login(SMTP_USER, SMTP_PASS)
                server.sendmail(EMAIL_FROM, email, msg.as_string())
            log(f"📨 Subscriber email sent to {email}")
        except Exception as e:
            log(f"⚠️  Subscriber email failed for {email}: {e}")

def listing_html(name, slug, price, maker, expiry, link, image_url, prefix=""):
    img_tag = f"<img src='{image_url}' style='width:120px;height:120px;object-fit:cover;border-radius:8px;float:right;margin-left:12px;'/>" if image_url else ""
    return f"""
    <div style="font-family:sans-serif; background:#1e1e1e; border:1px solid #2a2a2a;
                border-radius:12px; padding:16px; margin-bottom:16px;
                max-width:500px; color:#e0e0e0;">
      <div style="font-size:11px; color:#888; margin-bottom:8px;">{prefix}</div>
      {img_tag}
      <h3 style="margin:0 0 8px 0; color:white;">{name}</h3>
      <p style="margin:4px 0; font-size:14px; color:#2081e2;">💰 <strong>{price}</strong></p>
      <p style="margin:4px 0; font-size:12px; color:#888;">📁 {slug}</p>
      <p style="margin:4px 0; font-size:12px; color:#888;">💼 {maker[:10]}...{maker[-6:]}</p>
      <p style="margin:4px 0; font-size:12px; color:#888;">⏰ Expires: {expiry}</p>
      <div style="clear:both; margin-top:12px;">
        <a href="{link}" style="background:#2081e2; color:white; padding:8px 16px;
           border-radius:8px; text-decoration:none; font-size:13px;">
          View on OpenSea ↗
        </a>
      </div>
    </div>
    """

# ── WETH ──────────────────────────────────────────────────────
def fetch_weth():
    global WETH_USD
    try:
        url = "https://api.coingecko.com/api/v3/simple/price?ids=weth&vs_currencies=usd"
        with urllib.request.urlopen(url, timeout=10) as r:
            WETH_USD = json.loads(r.read())["weth"]["usd"]
        log(f"💱 WETH = ${WETH_USD:,.2f}")
    except Exception as e:
        log(f"⚠️  WETH price failed: {e}")

def weth_refresh_loop():
    while True:
        time.sleep(600)
        fetch_weth()

def fmt_price(base_price, symbol="WETH"):
    try:
        amount = int(base_price) / 1e18
        if WETH_USD and symbol in ("WETH", "ETH"):
            return f"${amount * WETH_USD:,.2f}  ({amount:.4f} {symbol})"
        return f"{amount:.4f} {symbol}"
    except:
        return str(base_price)

# ── Image ─────────────────────────────────────────────────────
def fetch_image_url(contract, token_id):
    try:
        if not contract or not token_id:
            return ""
        url = f"https://api.opensea.io/api/v2/metadata/polygon/{contract}/{token_id}"
        r = requests.get(url, headers={
            "accept": "*/*",
            "x-api-key": API_KEY
        }, timeout=10)
        data = r.json()
        return data.get("image", data.get("image_url", ""))
    except Exception as e:
        log(f"⚠️  Image fetch failed: {e}")
        return ""

# ── GitHub push ───────────────────────────────────────────────
def push_to_github(listing):
    try:
        listings = []
        if os.path.exists(LISTINGS_FILE):
            with open(LISTINGS_FILE) as f:
                listings = json.load(f)

        listings.append(listing)
        listings = listings[-MAX_LISTINGS:]

        with open(LISTINGS_FILE, "w") as f:
            json.dump(listings, f, indent=2)

        if not GITHUB_TOKEN:
            log("⚠️  No GitHub token — skipping GitHub push")
            return

        api_url = f"https://api.github.com/repos/{GITHUB_REPO}/contents/{GITHUB_FILE}"
        r = requests.get(api_url, headers={
            "Authorization": f"token {GITHUB_TOKEN}",
            "Accept": "application/vnd.github.v3+json"
        })
        sha = r.json().get("sha", "")

        content = base64.b64encode(
            json.dumps(listings, indent=2).encode()
        ).decode()

        requests.put(api_url, headers={
            "Authorization": f"token {GITHUB_TOKEN}",
            "Accept": "application/vnd.github.v3+json"
        }, json={
            "message": f"New listing: {listing.get('name', 'RCA')}",
            "content": content,
            "sha": sha
        })
        log("📤 Pushed to GitHub")
    except Exception as e:
        log(f"⚠️  GitHub push failed: {e}")

# ── Recent listings email (your email only) ───────────────────
def send_recent_listings_email():
    try:
        log("📧 Building recent listings email...")
        lines = open(LOG_FILE).readlines()
        blocks = []
        current = []
        for line in lines:
            if "RCA LISTING" in line:
                if current:
                    blocks.append(current)
                current = [line]
            elif current:
                current.append(line)
        if current:
            blocks.append(current)

        recent = blocks[-20:][::-1]

        cards = ""
        for block in recent:
            name   = next((l.split("🖼  ")[-1].strip() for l in block if "🖼" in l), "Unknown")
            slug   = next((l.split("📁 ")[-1].strip() for l in block if "📁" in l), "")
            price  = next((l.split("💰 ")[-1].strip() for l in block if "💰" in l), "")
            maker  = next((l.split("💼 ")[-1].strip() for l in block if "💼" in l), "")
            expiry = next((l.split("⏰ Expires: ")[-1].strip() for l in block if "⏰" in l), "")
            link   = next((re.search(r'https://\S+', l).group(0) for l in block if "https://" in l), "")
            cards += listing_html(name, slug, price, maker, expiry, link, "")

        html = f"""
        <html><body style="background:#121212; padding:16px;">
        <h2 style="color:#2081e2; font-family:sans-serif;">📋 Recent RCA Listings (Last 20)</h2>
        {cards if cards else "<p style='color:#888;'>No listings yet.</p>"}
        </body></html>
        """
        send_email("📋 Recent RCA Listings", html)
    except Exception as e:
        log(f"⚠️  Recent listings email failed: {e}")

# ── Log and notify ────────────────────────────────────────────
def log_and_email_listing(name, slug, price, maker, expiry, link,
                           image_url="", prefix="", listed_at=None):
    global LISTING_COUNT
    LISTING_COUNT += 1
    log("=" * 45)
    log(f"{prefix}🆕 RCA LISTING #{LISTING_COUNT}")
    log(f"🖼  {name}")
    log(f"📁 {slug}")
    log(f"💰 {price}")
    log(f"💼 {maker[:10]}...{maker[-6:]}")
    log(f"⏰ Expires: {expiry}")
    log(f"🔗 {link}")

    listing = {
        "name":      name,
        "slug":      slug,
        "price":     price,
        "maker":     f"{maker[:10]}...{maker[-6:]}",
        "expiry":    expiry,
        "link":      link,
        "image_url": image_url,
        "listed_at": listed_at or datetime.now(timezone.utc).isoformat(),
        "catchup":   bool(prefix)
    }

    # Push to GitHub and local file
    threading.Thread(target=push_to_github, args=(listing,), daemon=True).start()

    # Email to your address
    html = f"""
    <html><body style="background:#121212; padding:16px;">
    <h2 style="color:#2081e2; font-family:sans-serif;">🆕 New Reddit Avatar Listed</h2>
    {listing_html(name, slug, price, maker, expiry, link, image_url, prefix)}
    </body></html>
    """
    send_email(f"🆕 RCA: {name} — {price}", html)

    # Broadcast to subscribers
    threading.Thread(
        target=broadcast_to_subscribers,
        args=(name, price, link, image_url, slug,
              f"{maker[:10]}...{maker[-6:]}", expiry),
        daemon=True
    ).start()

# ── REST catchup ──────────────────────────────────────────────
def rest_catchup(since_timestamp):
    log("🔍 Catching up on missed listings...")
    try:
        found = 0
        next_cursor = None
        while True:
            url = "https://api.opensea.io/api/v2/events?event_type=listing&limit=200"
            if next_cursor:
                url += f"&next={next_cursor}"
            r = requests.get(url, headers={
                "accept": "application/json",
                "x-api-key": API_KEY
            }, timeout=15)
            data = r.json()

            events = data.get("asset_events", [])
            if not events:
                break

            done = False
            for event in events:
                ts = event.get("event_timestamp", 0)
                if ts < since_timestamp:
                    done = True
                    break

                slug = event.get("asset", {}).get("collection", "")
                if not is_rca(slug):
                    continue

                name      = event.get("asset", {}).get("name", "Unknown Avatar")
                link      = event.get("asset", {}).get("opensea_url", "")
                image_url = event.get("asset", {}).get("image_url", "")
                maker     = event.get("maker", "?")
                expiry    = str(event.get("closing_date", "?"))[:10]
                symbol    = event.get("payment", {}).get("symbol", "WETH")
                qty       = event.get("payment", {}).get("quantity", "0")
                decs      = event.get("payment", {}).get("decimals", 18)

                if not image_url:
                    m = re.search(r'opensea\.io/item/polygon/(0x[a-fA-F0-9]+)/(\d+)', link)
                    if m:
                        image_url = fetch_image_url(m.group(1), m.group(2))

                try:
                    amount = int(qty) / (10 ** decs)
                    price  = f"${amount * WETH_USD:,.2f}  ({amount:.4f} {symbol})" if WETH_USD else f"{amount:.4f} {symbol}"
                except:
                    price = qty

                log_and_email_listing(name, slug, price, maker, expiry,
                                      link, image_url, prefix="[CATCHUP] ")
                found += 1

            if done or not data.get("next"):
                break
            next_cursor = data.get("next")

        log(f"✅ Caught up {found} missed listing(s)" if found else "✅ No missed listings")
    except Exception as e:
        log(f"⚠️  Catchup failed: {e}")

# ── Stream handlers ───────────────────────────────────────────
def handle_event(data):
    try:
        outer = data.get("payload", {})
        if outer.get("event_type") != "item_listed":
            return
        p      = outer.get("payload", {})
        slug   = p.get("collection", {}).get("slug", "")
        if not is_rca(slug):
            return
        item      = p.get("item", {})
        meta      = item.get("metadata", {})
        name      = meta.get("name", "Unknown Avatar")
        link      = item.get("permalink", "")
        symbol    = p.get("payment_token", {}).get("symbol", "WETH")
        price     = fmt_price(p.get("base_price", "0"), symbol)
        maker     = p.get("maker", {}).get("address", "?")
        expiry    = p.get("expiration_date", "?")[:10]
        listed_at = p.get("event_timestamp", "")

        image_url = meta.get("image_url", "")
        if not image_url:
            nft_id = item.get("nft_id", "")
            if nft_id:
                parts = nft_id.split("/")
                if len(parts) == 3:
                    _, contract, token_id = parts
                    image_url = fetch_image_url(contract, token_id)

        log_and_email_listing(name, slug, price, maker, expiry,
                              link, image_url, listed_at=listed_at)
    except:
        pass

def on_open(ws):
    global LAST_CONNECTED
    log("🔌 Connected!")
    log("👀 Watching for Reddit Avatar listings...")

    if LAST_CONNECTED is not None:
        since = LAST_CONNECTED - 60
        threading.Thread(target=rest_catchup, args=(since,), daemon=True).start()

    LAST_CONNECTED = time.time()

    def heartbeat():
        i = 0
        while True:
            time.sleep(25)
            try:
                ws.send(json.dumps({"topic": "phoenix", "event": "heartbeat", "payload": {}, "ref": i}))
                i += 1
            except:
                break

    threading.Thread(target=heartbeat, daemon=True).start()
    ws.send(json.dumps({"topic": "collection:*", "event": "phx_join", "payload": {}, "ref": 1}))
    log("📡 Subscribed to global stream")
    log("⏳ Waiting for listings...\n")

def on_message(ws, msg):
    try:
        handle_event(json.loads(msg))
    except:
        pass

def on_error(ws, err):
    log(f"❌ Error: {err}")

def on_close(ws, code, msg):
    log(f"🔴 Disconnected ({code})")

def connect():
    url = f"wss://stream.openseabeta.com/socket/websocket?token={API_KEY}"
    ws  = websocket.WebSocketApp(
        url,
        on_open=on_open,
        on_message=on_message,
        on_error=on_error,
        on_close=on_close,
    )
    ws.run_forever()

if __name__ == "__main__":
    log("🚀 RCA Stream Listener starting...")
    log(f"📝 Log: {LOG_FILE}")
    fetch_weth()
    threading.Thread(target=weth_refresh_loop, daemon=True).start()
    while True:
        try:
            connect()
        except KeyboardInterrupt:
            log("👋 Stopped")
            break
        except Exception as e:
            log(f"⚠️  Crash: {e}")
        log("⏳ Reconnecting in 3s...")
        time.sleep(3)
