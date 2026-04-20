#!/usr/bin/env python3
import websocket
import json
import threading
import time
import os
import urllib.request
from datetime import datetime, timezone

API_KEY = "e42883f67023429590c1b7a8468eda67"
LOG_FILE = os.path.expanduser("~/rca_listings.log")
WETH_USD = None
LISTING_COUNT = 0
LAST_CONNECTED = None
CATCHUP_SECONDS = 300  # look back 5 minutes on reconnect

def log(msg):
    ts = datetime.now().strftime("%H:%M:%S")
    line = f"[{ts}] {msg}"
    print(line, flush=True)
    try:
        with open(LOG_FILE, "a") as f:
            f.write(line + "\n")
    except:
        pass

def is_rca(slug):
    return "reddit" in slug.lower()

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

def log_listing(name, slug, price, maker, expiry, link, prefix=""):
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

def rest_catchup(since_timestamp):
    log(f"🔍 Catching up on missed listings since {datetime.fromtimestamp(since_timestamp).strftime('%H:%M:%S')}...")
    try:
        found = 0
        next_cursor = None
        while True:
            url = "https://api.opensea.io/api/v2/events?event_type=listing&chain=matic&limit=50"
            if next_cursor:
                url += f"&next={next_cursor}"
            req = urllib.request.Request(
                url,
                headers={
                    "accept": "application/json",
                    "x-api-key": API_KEY
                }
            )
            with urllib.request.urlopen(req, timeout=15) as r:
                data = json.loads(r.read())

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

                name   = event.get("asset", {}).get("name", "Unknown Avatar")
                link   = event.get("asset", {}).get("opensea_url", "")
                maker  = event.get("maker", "?")
                expiry = event.get("closing_date", "?")
                if expiry and len(expiry) >= 10:
                    expiry = expiry[:10]
                symbol = event.get("payment", {}).get("symbol", "WETH")
                qty    = event.get("payment", {}).get("quantity", "0")
                decs   = event.get("payment", {}).get("decimals", 18)
                try:
                    amount = int(qty) / (10 ** decs)
                    if WETH_USD and symbol in ("WETH", "ETH"):
                        price = f"${amount * WETH_USD:,.2f}  ({amount:.4f} {symbol})"
                    else:
                        price = f"{amount:.4f} {symbol}"
                except:
                    price = qty

                log_listing(name, slug, price, maker, expiry, link, prefix="[CATCHUP] ")
                found += 1

            if done or not data.get("next"):
                break
            next_cursor = data.get("next")

        if found == 0:
            log("✅ No missed listings found")
        else:
            log(f"✅ Caught up {found} missed listing(s)")

    except Exception as e:
        log(f"⚠️  Catchup failed: {e}")

def handle_event(data):
    try:
        outer = data.get("payload", {})
        if outer.get("event_type") != "item_listed":
            return
        p    = outer.get("payload", {})
        slug = p.get("collection", {}).get("slug", "")
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
        log_listing(name, slug, price, maker, expiry, link)
    except:
        pass

def on_open(ws):
    global LAST_CONNECTED
    log("🔌 Connected!")
    log("👀 Watching for Reddit Avatar listings...")

    # Run catchup if we were previously connected
    if LAST_CONNECTED is not None:
        since = LAST_CONNECTED - 60  # overlap by 1 minute to avoid gaps
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
    ws = websocket.WebSocketApp(
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
