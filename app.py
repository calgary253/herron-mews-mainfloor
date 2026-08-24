from datetime import datetime
from flask import Flask, jsonify, render_template, request
import requests

app = Flask(__name__)

JSONBIN_BIN_ID = "6a640bd8da38895dfe8c7903"
JSONBIN_ACCESS_KEY = (
    "$2a$10$yjx9LlbvtXkus3Ny9sNE3eSaqE1czDp..yFA6lBccOwHmG.KM7Vp2"
)


def fetch_data():
  url = f"https://api.jsonbin.io/v3/b/{JSONBIN_BIN_ID}/latest"
  headers = {"X-Access-Key": JSONBIN_ACCESS_KEY}
  try:
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    data = response.json().get("record", {})
    return data.get("expenses", []), data.get("basement_expenses", [])
  except:
    return [], []


def save_data(expenses, basement_expenses):
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
  record["basement_expenses"] = basement_expenses

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
  expenses, basement_expenses = fetch_data()
  return jsonify(
      {"expenses": expenses, "basement_expenses": basement_expenses}
  )


@app.route("/api/add", methods=["POST"])
def add_expense():
  req = request.json
  unit = req.get("unit")  # 'main' or 'basement'
  item = {
      "id": str(int(datetime.now().timestamp() * 1000)),
      "description": req.get("description"),
      "amount": float(req.get("amount", 0)),
      "category": req.get("category"),
      "paidBy": req.get("paidBy"),
      "date": req.get("date"),
  }

  expenses, basement_expenses = fetch_data()
  if unit == "basement":
    basement_expenses.append(item)
  else:
    expenses.append(item)

  success = save_data(expenses, basement_expenses)
  return jsonify({"success": success})


@app.route("/api/delete", methods=["POST"])
def delete_expense():
  req = request.json
  unit = req.get("unit")
  exp_id = req.get("id")

  expenses, basement_expenses = fetch_data()
  if unit == "basement":
    basement_expenses = [e for e in basement_expenses if str(e.get("id")) != exp_id]
  else:
    expenses = [e for e in expenses if str(e.get("id")) != exp_id]

  success = save_data(expenses, basement_expenses)
  return jsonify({"success": success})


if __name__ == "__main__":
  app.run(host="0.0.0.0", port=5000)
