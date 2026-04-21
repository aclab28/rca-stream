#!/usr/bin/env python3
import websocket
import json
import threading
import time
import os
import smtplib
import urllib.request
import requests
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import pytz

API_KEY    = "e42883f67023429590c1b7a8468eda67"
LOG_FILE   = os.path.expanduser("~/rca_listings.log")
EMAIL_TO   = "rca.lert1000@gmail.com"
EMAIL_FROM = "rca.lert1000@gmail.com"
EASTERN    = pytz.timezone("America/New_York")
WETH_USD   = None
LISTING_COUNT  = 0
LAST_CONNECTED = None

SMTP_HOST = "smtp.gmail.com"
SMTP_PORT = 587
SMTP_USER = "rca.lert1000@gmail.com"
SMTP_PASS = "pbgq axma hbxa moii"

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

def send_email(subject, html_body):
    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"]    = EMAIL_FROM
        msg["To"]      = EMAIL_TO
        msg.attach(MIMEText(html_body, "html"))
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
            server.ehlo()
            server.starttls()
            server.login(SMTP_USER, SMTP_PASS)
            server.sendmail(EMAIL_FROM, EMAIL_TO, msg.as_string())
        log("📧 Email sent")
    except Exception as e:
        log(f"⚠️  Email failed: {e}")

def listing_html(name, slug, price, maker, expiry, link, image_url, prefix=""):
    img_tag = f"<img src='{image_url}' style='width:120px;height:120px;object-fit:cover;border-radius:8px;float:right;margin-left:12px;' />" if image_url else ""
    return f"""
    <div style="font-family:sans-serif; border:1px solid #ddd;
                border-radius:8px; padding:16px; margin-bottom:16px;
                max-width:500px;">
      <div style="font-size:11px; color:#888; margin-bottom:8px;">{prefix}</div>
      {img_tag}
      <h3 style="margin:0 0 8px 0; color:#333;">{name}</h3>
      <p style="margin:4px 0; font-size:14px;">💰 <strong>{price}</strong></p>
      <p style="margin:4px 0; font-size:12px; color:#555;">📁 {slug}</p>
      <p style="margin:4px 0; font-size:12px; color:#555;">💼 {maker[:10]}...{maker[-6:]}</p>
      <p style="margin:4px 0; font-size:12px; color:#555;">⏰ Expires: {expiry}</p>
      <a href="{link}" style="display:inline-block; margin-top:10px;
         background:#2081e2; color:white; padding:8px 16px;
         border-radius:6px; text-decoration:none; font-size:13px;">
        View on OpenSea
      </a>
      <div style="clear:both;"></div>
    </div>
    """

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

def log_and_email_listing(name, slug, price, maker, expiry, link,
                           image_url="", prefix=""):
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

    html = f"""
    <html><body style="background:#f5f5f5; padding:16px;">
    <h2 style="color:#2081e2;">🆕 New Reddit Avatar Listed</h2>
    {listing_html(name, slug, price, maker, expiry, link, image_url, prefix)}
    </body></html>
    """
    send_email(f"🆕 RCA: {name} — {price}", html)

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
            link   = next((l.split("🔗 ")[-1].strip() for l in block if "🔗" in l), "")
            cards += listing_html(name, slug, price, maker, expiry, link, "")

        html = f"""
        <html><body style="background:#f5f5f5; padding:16px;">
        <h2 style="color:#2081e2;">📋 Recent RCA Listings (Last 20)</h2>
        {cards if cards else "<p>No listings yet.</p>"}
        </body></html>
        """
        send_email("📋 Recent RCA Listings", html)
    except Exception as e:
        log(f"⚠️  Recent listings email failed: {e}")

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

def handle_event(data):
    try:
        outer = data.get("payload", {})
        if outer.get("event_type") != "item_listed":
            return
        p      = outer.get("payload", {})
        slug   = p.get("collection", {}).get("slug", "")
        if not is_rca(slug):
            return
        item   = p.get("item", {})
        meta   = item.get("metadata", {})
        name   = meta.get("name", "Unknown Avatar")
        link   = item.get("permalink", "")
        symbol = p.get("payment_token", {}).get("symbol", "WETH")
        price  = fmt_price(p.get("base_price", "0"), symbol)
        maker  = p.get("maker", {}).get("address", "?")
        expiry = p.get("expiration_date", "?")[:10]

        image_url = meta.get("image_url", "")
        if not image_url:
            nft_id = item.get("nft_id", "")
            if nft_id:
                parts = nft_id.split("/")
                if len(parts) == 3:
                    _, contract, token_id = parts
                    image_url = fetch_image_url(contract, token_id)

        log_and_email_listing(name, slug, price, maker, expiry,
                              link, image_url)
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
