from datetime import datetime
import pandas as pd
import requests
import streamlit as st

# --- JSONBIN.IO CONFIGURATION ---
JSONBIN_BIN_ID = "6a640bd8da38895dfe8c7903"
JSONBIN_ACCESS_KEY = (
    "$2a$10$yjx9LlbvtXkus3Ny9sNE3eSaqE1czDp..yFA6lBccOwHmG.KM7Vp2"
)

st.set_page_config(
    page_title="253 Herron Mews Expense Tracker",
    page_icon="🏠",
    layout="wide",
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


# --- CLOUD FETCH/SAVE FUNCTIONS ---
def fetch_data_from_cloud():
  url = f"https://api.jsonbin.io/v3/b/{JSONBIN_BIN_ID}/latest"
  headers = {"X-Access-Key": JSONBIN_ACCESS_KEY}
  try:
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    data = response.json().get("record", {})
    return data.get("expenses", []), data.get("monthlyPayments", {})
  except Exception as e:
    st.error(f"Error connecting to cloud storage: {e}")
    return [], {"householdPaid": {}, "prevMonthPaid": {}}


def save_data_to_cloud(expenses, monthly_payments):
  url = f"https://api.jsonbin.io/v3/b/{JSONBIN_BIN_ID}"
  headers = {
      "Content-Type": "application/json",
      "X-Access-Key": JSONBIN_ACCESS_KEY,
  }
  payload = {"expenses": expenses, "monthlyPayments": monthly_payments}
  try:
    response = requests.put(url, headers=headers, json=payload)
    response.raise_for_status()
    return True
  except Exception as e:
    st.error(f"Error saving to cloud: {e}")
    return False


# --- INITIALIZE SESSION STATE ---
if "expenses" not in st.session_state or "monthly_payments" not in st.session_state:
  exps, mp = fetch_data_from_cloud()
  st.session_state.expenses = exps
  st.session_state.monthly_payments = mp

# --- URL PARAMETER AUTHENTICATION ---
# Example: http://localhost:8501/?user=Jigneshkumar&role=admin
query_params = st.query_params
current_user = query_params.get("user", "Jigneshkumar")
user_role = query_params.get("role", "admin")

# --- SIDEBAR UI ---
st.sidebar.title("🏠 Navigation")
st.sidebar.info(
    f"👤 Logged in as: **{current_user.capitalize()}**\n\n🛡️ Role: **{user_role.upper()}**"
)

# Populate available months dynamically from expenses + current month
all_months = sorted(
    list(
        set(
            [e.get("date", "")[:7] for e in st.session_state.expenses if e.get("date")]
        )
    ),
    reverse=True,
)
current_ym = datetime.now().strftime("%Y-%m")
if current_ym not in all_months:
  all_months.insert(0, current_ym)

selected_month = st.sidebar.selectbox("📅 View Month (YYYY-MM)", all_months)
st.sidebar.divider()

# --- MAIN PAGE HEADER ---
st.title("🏠 253 Herron Mews Main Floor Household Expense Tracker")
st.markdown(
    f"Currently viewing settlement breakdown and expenses for **{selected_month}**."
)

# --- CALCULATIONS FOR SELECTED MONTH ---
is_august_2026 = selected_month == "2026-08"
upstairs_shares = (
    ["Jigneshkumar", "Jaimin & Ishani"]
    if is_august_2026
    else ["Jigneshkumar", "Jaimin & Ishani", "Viru & Drashti"]
)

month_expenses = [
    e for e in st.session_state.expenses if e.get("date", "").startswith(selected_month)
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

# --- METRIC CARDS ---
col1, col2, col3 = st.columns(3)
col1.metric("Total 3-Way Household Split", f"${household_total:.2f}")
col2.metric(
    "Total Utilities (Shaw + Enmax + Atco)",
    f"${shaw_total + enmax_total + atco_total:.2f}",
)
col3.metric("Total Records in Month", len(month_expenses))

st.divider()

# --- TABS FOR ORGANIZATION ---
tab1, tab2, tab3 = st.tabs(
    ["📊 Settlement Summary", "➕ Add Expense", "📝 Manage Expenses"]
)

with tab1:
  st.subheader(f"Individual Balances & Net Standing ({selected_month})")

  summary_data = []
  for share_unit in upstairs_shares:
    h_spent = share_household_spent[share_unit]
    u_spent = share_utility_spent[share_unit]
    paid = h_spent + u_spent

    h_target = base_household_share * resident_count_map[share_unit]
    u_target = utility_share_per_resident * resident_count_map[share_unit]
    target = h_target + u_target

    net = paid - target
    status_str = (
        f"Gets back ${net:.2f}"
        if net >= 0
        else f"Owes ${abs(net):.2f} (Deficit)"
    )

    summary_data.append({
        "Share Unit": share_unit,
        "Total Paid": f"${paid:.2f}",
        "Target Share": f"${target:.2f}",
        "Net Status": status_str,
    })

  st.dataframe(pd.DataFrame(summary_data), use_container_width=True)

with tab2:
  st.subheader("Add New Household Expense")
  # Pre-fill 'Paid By' with the user from URL if they match
  default_payer_index = 0
  payers = ["Jigneshkumar", "Jaimin", "Viru", "Ishani", "Drashti"]
  for idx, p in enumerate(payers):
    if p.lower() in current_user.lower():
      default_payer_index = idx
      break

  with st.form("expense_form"):
    c1, c2 = st.columns(2)
    desc = c1.text_input("Description / Item Name")
    amount = c2.number_input("Amount ($)", min_value=0.0, step=0.01)

    c3, c4, c5 = st.columns(3)
    category = c3.selectbox(
        "Category", ["Groceries", "Household", "shaw", "enmax", "atco", "Other"]
    )
    paid_by = c4.selectbox("Paid By", payers, index=default_payer_index)
    exp_date = c5.date_input("Expense Date", datetime.now())

    submitted = st.form_submit_button("Save Expense", use_container_width=True)
    if submitted and desc:
      new_entry = {
          "id": str(int(datetime.now().timestamp() * 1000)),
          "description": desc,
          "amount": amount,
          "category": category,
          "paidBy": paid_by,
          "date": exp_date.strftime("%Y-%m-%d"),
      }
      st.session_state.expenses.append(new_entry)
      if save_data_to_cloud(
          st.session_state.expenses, st.session_state.monthly_payments
      ):
        st.success("Expense successfully added and synced to cloud bin!")
        st.rerun()

with tab3:
  st.subheader("Manage & Delete Logged Expenses")
  if user_role.lower() != "admin":
    st.warning("⚠️ You are in read-only mode. Admin rights required to delete.")
  else:
    if st.session_state.expenses:
      exp_df = pd.DataFrame(st.session_state.expenses)
      st.dataframe(exp_df, use_container_width=True)

      del_id = st.text_input(
          "Enter the Expense ID to delete (copy from table above):"
      )
      if st.button("Delete Expense Record", type="primary"):
        st.session_state.expenses = [
            e for e in st.session_state.expenses if str(e.get("id")) != del_id
        ]
        if save_data_to_cloud(
            st.session_state.expenses, st.session_state.monthly_payments
        ):
          st.success("Expense successfully deleted from cloud!")
          st.rerun()
    else:
      st.info("No expense records found.")
