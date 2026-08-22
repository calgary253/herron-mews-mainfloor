import datetime
import requests

# --- JSONBIN.IO CONFIGURATION ---
JSONBIN_BIN_ID = "6a640bd8da38895dfe8c7903"
JSONBIN_ACCESS_KEY = (
    "$2a$10$yjx9LlbvtXkus3Ny9sNE3eSaqE1czDp..yFA6lBccOwHmG.KM7Vp2"
)

USER_TO_SHARE_MAP = {
    "jigneshkumar": "Jigneshkumar",
    "jaimin": "Jaimin & Ishani",
    "ishani": "Jaimin & Ishani",
    "ishanibhabhi": "Jaimin & Ishani",
    "jaimin & ishani": "Jaimin & Ishani",
    "viru": "Viru & Drashti",
    "drashti": "Viru & Drashti",
    "viru & drashti": "Viru & Drashti",
}

RESTRICTED_USERS = ["viru", "drashti", "viru & drashti"]
ADMIN_USERS = [
    "jigneshkumar",
    "jaimin",
    "ishani",
    "ishanibhabhi",
    "jaimin & ishani",
]


def fetch_data_from_cloud():
  """Fetches expenses and monthly payments from JSONBin.io"""
  url = f"https://api.jsonbin.io/v3/b/{JSONBIN_BIN_ID}/latest"
  headers = {"X-Access-Key": JSONBIN_ACCESS_KEY}
  try:
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    data = response.json().get("record", {})
    return data.get("expenses", []), data.get("monthlyPayments", {})
  except Exception as e:
    print(f"[-] Error fetching data from cloud: {e}")
    return [], {"householdPaid": {}, "prevMonthPaid": {}}


def save_data_to_cloud(expenses, monthly_payments):
  """Saves expenses and monthly payments back to JSONBin.io"""
  url = f"https://api.jsonbin.io/v3/b/{JSONBIN_BIN_ID}"
  headers = {
      "Content-Type": "application/json",
      "X-Access-Key": JSONBIN_ACCESS_KEY,
  }
  payload = {"expenses": expenses, "monthlyPayments": monthly_payments}
  try:
    response = requests.put(url, headers=headers, json=payload)
    response.raise_for_status()
    print("[+] Successfully saved data to cloud!")
    return True
  except Exception as e:
    print(f"[-] Error saving to cloud: {e}")
    return False


def calculate_settlement(expenses, monthly_payments, target_month):
  """Computes the complete settlement breakdown for a given month (e.g., '2026-08')"""
  is_august_2026 = target_month == "2026-08"
  upstairs_shares = (
      ["Jigneshkumar", "Jaimin & Ishani"]
      if is_august_2026
      else ["Jigneshkumar", "Jaimin & Ishani", "Viru & Drashti"]
  )

  month_expenses = [
      e for e in expenses if e.get("date", "").startswith(target_month)
  ]

  household_total = 0.0
  shaw_total = 0.0
  enmax_total = 0.0
  atco_total = 0.0

  share_household_spent = {s: 0.0 for s in upstairs_shares}
  share_utility_spent = {s: 0.0 for s in upstairs_shares}

  for item in month_expenses:
    paid_by_key = item.get("paidBy", "").lower().strip()
    share_unit = USER_TO_SHARE_MAP.get(paid_by_key)
    if not share_unit or share_unit not in upstairs_shares:
      continue

    cat = item.get("category")
    amount = float(item.get("amount", 0))

    if cat == "shaw":
      shaw_total += amount
      share_utility_spent[share_unit] += amount
    elif cat == "enmax":
      enmax_total += amount
      share_utility_spent[share_unit] += amount
    elif cat == "atco":
      atco_total += amount
      share_utility_spent[share_unit] += amount
    else:
      household_total += amount
      share_household_spent[share_unit] += amount

  household_divisor = 3 if is_august_2026 else 5
  utility_residents = 8 if is_august_2026 else 9
  main_floor_multiplier = 3 if is_august_2026 else 5

  base_household_share = (
      household_total / household_divisor if household_divisor > 0 else 0
  )
  utility_share_per_resident = (
      (shaw_total + enmax_total + atco_total) / utility_residents
      if utility_residents > 0
      else 0
  )

  resident_count_map = (
      {"Jigneshkumar": 1, "Jaimin & Ishani": 2}
      if is_august_2026
      else {"Jigneshkumar": 1, "Jaimin & Ishani": 2, "Viru & Drashti": 2}
  )
  weight_map = resident_count_map

  print(f"\n==================================================")
  print(f" SETTLEMENT REPORT FOR {target_month}")
  print(f"==================================================")
  print(f"Total 3-Way Split Spending: ${household_total:.2f}")
  print(
      f"Utilities (Shaw + Enmax + Atco): ${shaw_total + enmax_total + atco_total:.2f}"
  )
  print(f"--------------------------------------------------")
  print(f"Individual Balances & Net Standing:")

  for share_unit in upstairs_shares:
    h_spent = share_household_spent[share_unit]
    u_spent = share_utility_spent[share_unit]
    paid = h_spent + u_spent

    h_target = base_household_share * weight_map[share_unit]
    u_target = utility_share_per_resident * resident_count_map[share_unit]
    target = h_target + u_target

    net = paid - target

    status_str = (
        f"Gets back ${net:.2f}"
        if net >= 0
        else f"Owes ${abs(net):.2f} (Net: -${abs(net):.2f})"
    )
    print(
        f" - {share_unit:18} | Paid: ${paid:7.2f} | Target: ${target:7.2f} | {status_str}"
    )


def main():
  print("[*] Fetching tracker data from cloud...")
  expenses, monthly_payments = fetch_data_from_cloud()
  print(
      f"[+] Loaded {len(expenses)} expense records successfully from cloud bin."
  )

  # Run calculation for August 2026 by default
  calculate_settlement(expenses, monthly_payments, "2026-08")


if __name__ == "__main__":
  main()
