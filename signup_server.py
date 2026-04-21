#!/usr/bin/env python3
from flask import Flask, request, jsonify, send_file
import os
import re
import ssl

app = Flask(__name__)
SUBSCRIBERS_FILE = "/home/ubuntu/subscribers.txt"
LISTINGS_FILE = "/home/ubuntu/listings.json"

def valid_email(email):
    return re.match(r"[^@]+@[^@]+\.[^@]+", email) is not None

def load_subscribers():
    if not os.path.exists(SUBSCRIBERS_FILE):
        return []
    with open(SUBSCRIBERS_FILE) as f:
        return [line.strip() for line in f if line.strip()]

def save_subscriber(email):
    subscribers = load_subscribers()
    if email in subscribers:
        return False
    with open(SUBSCRIBERS_FILE, "a") as f:
        f.write(email + "\n")
    return True

@app.route("/listings", methods=["GET"])
def listings():
    try:
        response = send_file(LISTINGS_FILE, mimetype="application/json")
        response.headers["Access-Control-Allow-Origin"] = "*"
        response.headers["Cache-Control"] = "no-cache"
        return response
    except:
        response = jsonify([])
        response.headers["Access-Control-Allow-Origin"] = "*"
        return response

@app.route("/subscribe", methods=["POST", "OPTIONS"])
def subscribe():
    if request.method == "OPTIONS":
        response = jsonify({})
        response.headers["Access-Control-Allow-Origin"] = "*"
        response.headers["Access-Control-Allow-Headers"] = "Content-Type"
        response.headers["Access-Control-Allow-Methods"] = "POST"
        return response

    data  = request.get_json(silent=True) or {}
    email = data.get("email", "").strip().lower()

    if not email or not valid_email(email):
        response = jsonify({"status": "error", "message": "Invalid email address"})
        response.headers["Access-Control-Allow-Origin"] = "*"
        return response, 400

    if save_subscriber(email):
        response = jsonify({"status": "success", "message": "Subscribed successfully"})
    else:
        response = jsonify({"status": "already", "message": "Already subscribed"})

    response.headers["Access-Control-Allow-Origin"] = "*"
    return response

@app.route("/health", methods=["GET"])
def health():
    subs = load_subscribers()
    response = jsonify({"status": "ok", "subscribers": len(subs)})
    response.headers["Access-Control-Allow-Origin"] = "*"
    return response

if __name__ == "__main__":
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    context.load_cert_chain(
        '/etc/letsencrypt/live/rca-listings.duckdns.org/fullchain.pem',
        '/etc/letsencrypt/live/rca-listings.duckdns.org/privkey.pem'
    )
    app.run(host="0.0.0.0", port=443, ssl_context=context)
