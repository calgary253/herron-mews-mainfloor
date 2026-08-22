import streamlit as st
import pandas as pd
from datetime import datetime, date
import requests
import json

# Cloud Storage Configuration (Using your JSONBin keys/IDs)
JSONBIN_BIN_ID = "6a63d85cf5f4af5e29bd604c"
JSONBIN_MASTER_KEY = "$2a$10$aGsMHmzawGqngUYQk4byNO6eOgVEFFObkr5LyuKv1hQ73QECFOWN2"

VALID_USERS = ["Biren", "Akshay", "Kunjalbhabhi", "Biju", "Jaimin", "Manali"]
TOTAL_UTILITY_RESIDENTS = 8

RENT_DISTRIBUTION = {
    "Biren & Manali": 650,
    "Akshay & Kunjal": 650,
    "Biju": 0
}

def fetch_from_cloud():
    try:
        headers = {'X-Master-Key': JSONBIN_MASTER_KEY}
        response = requests.get(f"https://api.jsonbin.io/v3/b/{JSONBIN_BIN_ID}/latest", headers=headers)
        if response.status_code == 200:
            data = response.json().get("record", {})
            return data.get("expenses", []), data.get("monthlyPayments", {})
    except Exception as e:
        st.warning(f"Cloud sync error: {e}")
    return [], {"landlordPayments": {}, "householdPaid": {}}

def save_to_cloud(expenses, monthly_payments):
    try:
        headers = {
            'Content-Type': 'application/json',
            'X-Master-Key': JSONBIN_MASTER_KEY
        }
        payload = {"expenses": expenses, "monthlyPayments": monthly_payments}
        requests.put(f"https://api.jsonbin.io/v3/b/{JSONBIN_BIN_ID}", headers=headers, data=json.dumps(payload))
    except Exception as e:
        st.error(f"Failed to save changes to cloud: {e}")

def run_basement_tracker():
    st.subheader("253 Herron Mews Basement Household Expense Tracker")

    # Handle user query parameter login matching your HTML design (?user=Name)
    query_params = st.query_params
    current_user = query_params.get("user", "")

    if current_user not in VALID_USERS:
        st.error("Access Restricted: You must use your designated personal URL link with your name included (e.g. `?user=Akshay`).")
        return

    is_admin = (current_user == "Biren")
    is_jaimin = (current_user == "Jaimin")

    # Display Role Badge Banner
    if is_admin:
        st.markdown("🟢 **Role:** `ADMIN MODE`")
    elif is_jaimin:
        st.markdown("🟣 **Role:** `LANDLORD / UTILITY MANAGER`")
    else:
        st.markdown("🔵 **Role:** `PERSONAL ACCOUNT`")

    st.write(f"Welcome, **{current_user}**!")

    # Initialize session state for data persistence
    if "basement_expenses" not in st.session_state or "basement_payments" not in st.session_state:
        exp, pay = fetch_from_cloud()
        st.session_state["basement_expenses"] = exp
        st.session_state["basement_payments"] = pay

    expenses = st.session_state["basement_expenses"]
    payments = st.session_state["basement_payments"]

    if "landlordPayments" not in payments:
        payments["landlordPayments"] = {}
    if "householdPaid" not in payments:
        payments["householdPaid"] = {}

    # --- SUBMIT NEW EXPENSE SECTION ---
    with st.expander("Submit New Expense", expanded=True):
        with st.form("basement_expense_form", clear_on_submit=True):
            col1, col2 = st.columns(2)
            with col1:
                exp_date = st.date_input("Date", value=date.today())
                
                # Category choices based on role
                if is_jaimin:
                    category = st.selectbox("Category", ["shaw", "enmax", "atco"], format_func=lambda x: {
                        "shaw": "Shaw Internet (8-Way Split)",
                        "enmax": "Enmax Electricity (8-Way Split)",
                        "atco": "Atco Gas (8-Way Split)"
                    }[x])
                elif is_admin:
                    category = st.selectbox("Category", ["household", "shaw", "enmax", "atco"], format_func=lambda x: {
                        "household": "General Household (4-Way Split)",
                        "shaw": "Shaw Internet (8-Way Split)",
                        "enmax": "Enmax Electricity (8-Way Split)",
                        "atco": "Atco Gas (8-Way Split)"
                    }[x])
                else:
                    category = "household"
                    st.text("Category: General Household (4-Way Split)")

            with col2:
                description = st.text_input("Description (e.g. Milk, Groceries)")
                amount = st.number_input("Amount ($)", min_value=0.01, step=0.01)

            submitted = st.form_submit_button("Submit Expense")
            if submitted:
                if not description.strip():
                    st.error("Please enter a description.")
                else:
                    new_item = {
                        "id": int(datetime.now().timestamp() * 1000),
                        "date": exp_date.strftime("%Y-%m-%d"),
                        "category": category,
                        "paidBy": current_user,
                        "description": description.strip(),
                        "amount": float(amount),
                        "archived": False
                    }
                    expenses.append(new_item)
                    save_to_cloud(expenses, payments)
                    st.success("Expense added successfully!")
                    st.rerun()

    # --- LOGGED EXPENSES & VIEW MONTH ---
    st.markdown("---")
    active_months = sorted(list(set([e["date"][:7] for e in expenses if not e.archived and "date" in e])), reverse=True)
    current_month_str = datetime.now().strftime("%Y-%m")
    if current_month_str not in active_months:
        active_months.insert(0, current_month_str)

    col_m1, col_m2 = st.columns([2, 1])
    with col_m1:
        selected_month = st.selectbox("View Month", active_months)
    with col_m2:
        if st.button("Export CSV"):
            df_export = pd.DataFrame([e for e in expenses if not e.archived and e.get("date", "").startswith(selected_month)])
            if not df_export.empty:
                csv = df_export.to_csv(index=False).encode('utf-8')
                st.download_button("Download CSV File", csv, f"Expenses_{selected_month}.csv", "text/csv")
            else:
                st.info("No data available to export for this month.")

    # Filter expenses for view
    month_expenses = [e for e in expenses if not e.archived and e.get("date", "").startswith(selected_month)]
    
    if month_expenses:
        df_display = pd.DataFrame(month_expenses)[["date", "paidBy", "category", "description", "amount"]]
        st.dataframe(df_display, use_container_width=True)
        
        if is_admin:
            with st.expander("Admin Actions: Delete/Edit Entries"):
                del_id = st.selectbox("Select Expense ID to Delete", [e["id"] for e in month_expenses])
                if st.button("Delete Selected Expense"):
                    expenses = [e for e in expenses if e["id"] != del_id]
                    st.session_state["basement_expenses"] = expenses
                    save_to_cloud(expenses, payments)
                    st.success("Deleted!")
                    st.rerun()
    else:
        st.info(f"No active expenses recorded for {selected_month}.")

    # --- SETTLEMENT REPORT CALCULATION ---
    if is_admin or st.button("Calculate Settlement for Selected Month"):
        st.markdown(f"### Monthly Settlement Report ({selectedMonth})")
        
        household_total = sum(e["amount"] for e in month_expenses if e["category"] == "household")
        shaw_total = sum(e["amount"] for e in month_expenses if e["category"] == "shaw")
        enmax_total = sum(e["amount"] for e in month_expenses if e["category"] == "enmax")
        atco_total = sum(e["amount"] for e in month_expenses if e["category"] == "atco")

        utility_total = shaw_total + enmax_total + atco_total
        utility_share_per_person = utility_total / TOTAL_UTILITY_RESIDENTS
        basement_contribution = utility_share_per_person * 5

        st.info(f"""
        * **General Household Total (4-Way):** ${household_total:.2f} (${household_total/4:.2f} / share)
        * **Combined Utilities (Shaw + Enmax + Atco):** ${utility_total:.2f}
        * **Basement Family Contribution (5/8th Utility):** ${basement_contribution:.2f}
        """)

        # Rent Breakdown
        st.markdown("#### Rent & Utility Breakdown (Payable to Jaimin)")
        landlord_rows = [
            {"key": "Biren & Manali", "name": "Biren & Manali", "mult": 2, "rent": RENT_DISTRIBUTION["Biren & Manali"]},
            {"key": "Akshay & Kunjal", "name": "Akshay & Kunjal", "mult": 2, "rent": RENT_DISTRIBUTION["Akshay & Kunjal"]},
            {"key": "Biju", "name": "Biju", "mult": 1, "rent": RENT_DISTRIBUTION["Biju"]}
        ]
        
        breakdown_data = []
        for r in landlord_rows:
            person_util = utility_share_per_person * r["mult"]
            total_due = person_util + r["rent"]
            breakdown_data.append({
                "Person / Unit": r["name"],
                "Utility Shares": f"${person_util:.2f}",
                "Rent Share": f"${r['rent']:.2f}",
                "Total Payable to Jaimin": f"${total_due:.2f}"
            })
        st.table(pd.DataFrame(breakdown_data))
