from flask import Flask, jsonify, render_template, request
import requests

app = Flask(__name__)

JSONBIN_BIN_ID = "6a640bd8da38895dfe8c7903"
JSONBIN_ACCESS_KEY = "$2a$10$yjx9LlbvtXkus3Ny9sNE3eSaqE1czDp..yFA6lBccOwHmG.KM7Vp2"

def fetch_data():
    url = f"https://api.jsonbin.io/v3/b/{JSONBIN_BIN_ID}/latest"
    headers = {"X-Access-Key": JSONBIN_ACCESS_KEY}
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        data = response.json().get("record", {})
        return data.get("expenses", []), data.get("monthlyPayments", {})
    except:
        return [], {}

def save_data(expenses, monthly_payments):
    url = f"https://api.jsonbin.io/v3/b/{JSONBIN_BIN_ID}"
    headers = {
        "Content-Type": "application/json",
        "X-Access-Key": JSONBIN_ACCESS_KEY,
    }
    try:
        current_resp = requests.get(url, headers={"X-Access-Key": JSONBIN_ACCESS_KEY})
        record = current_resp.json().get("record", {})
    except:
        record = {}

    record["expenses"] = expenses
    record["monthlyPayments"] = monthly_payments

    try:
        response = requests.put(url, headers=headers, json=record)
        response.raise_for_status()
        return True
    except:
        return False

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/api/data", methods=["GET"])
def get_data():
    expenses, monthly_payments = fetch_data()
    return jsonify({
        "expenses": expenses,
        "monthlyPayments": monthly_payments
    })

@app.route("/api/save", methods=["POST"])
def save_expense_data():
    req = request.json
    expenses = req.get("expenses", [])
    monthly_payments = req.get("monthlyPayments", {})
    success = save_data(expenses, monthly_payments)
    return jsonify({"success": success})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
