from flask import Flask, jsonify
from supabase import create_client, Client
from datetime import datetime, timedelta
from collections import defaultdict, OrderedDict
import os
from dotenv import load_dotenv
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

# Load environment variables
load_dotenv()
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")

# Connect to Supabase
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# Month order for sorting
MONTH_ORDER = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun',
               'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']


def calculate_summary(data):
    if not data or len(data) < 2:
        print("❌ Not enough data to calculate summary")
        return {}

    data = sorted(data, key=lambda x: x["at_distance"])
    total_distance = data[-1]["at_distance"] - data[0]["at_distance"]
    total_expense = sum(row["amount"] for row in data[:-1])
    total_fuel = total_expense / 103  # ₹103/litre assumption
    mileage = round(total_distance / total_fuel, 2)

    today = datetime.today()
    this_month = today.strftime("%Y-%m")
    one_week_ago = today - timedelta(days=7)

    monthly_expense = sum(
        row["amount"] for row in data
        if row["date_changed"].startswith(this_month)
    )

    weekly_expense = sum(
        row["amount"] for row in data
        if datetime.fromisoformat(row["date_changed"]) >= one_week_ago
    )

    summary = {
        "total_distance_km": total_distance,
        "total_fuel_liters": round(total_fuel, 2),
        "mileage_kmpl": mileage,
        "total_expense": total_expense,
        "monthly_expense": monthly_expense,
        "weekly_expense": weekly_expense,
    }

    print("✅ Summary:", summary)
    return summary


def calculate_expenses(data):
    monthly_grouped = defaultdict(lambda: defaultdict(lambda: {"amount": 0.0, "distance": 0.0}))
    weekly_grouped = defaultdict(float)

    today = datetime.today()
    one_week_ago = today - timedelta(days=7)

    for i, row in enumerate(data):
        try:
            date = datetime.fromisoformat(row["date_changed"])
            year = str(date.year)
            month = date.strftime("%b")
            amount = float(row["amount"])
            current_distance = row["at_distance"]
            prev_distance = data[i - 1]["at_distance"] if i > 0 else current_distance
            distance_covered = max(0, current_distance - prev_distance)

            monthly_grouped[year][month]["amount"] += amount
            monthly_grouped[year][month]["distance"] += distance_covered

            if date >= one_week_ago:
                week_label = date.strftime("%Y-%m-%d")
                weekly_grouped[week_label] += amount

        except Exception as parse_err:
            print(f"⚠️ Skipping row due to error: {parse_err}")
            continue

    ordered_monthly = {}
    for year, months in monthly_grouped.items():
        sorted_months = OrderedDict()
        for month in MONTH_ORDER:
            if month in months:
                sorted_months[month] = {
                    "amount": round(months[month]["amount"], 2),
                    "distance": round(months[month]["distance"], 2)
                }
        ordered_monthly[year] = sorted_months

    print("📊 Monthly Expenses with Distance:", ordered_monthly)
    print("📈 Weekly Expenses:", dict(weekly_grouped))

    return ordered_monthly, dict(weekly_grouped)


@app.route("/api/bike-summary", methods=["GET"])
def bike_summary():
    try:
        response = supabase.table("bike_history").select("*").execute()
        data = sorted(response.data, key=lambda x: x["at_distance"])
        summary = calculate_summary(data)
        return jsonify(summary)
    except Exception as e:
        print("🚨 Error fetching summary:", e)
        return jsonify({"error": "Failed to fetch summary"}), 500


@app.route("/api/bike-expenses", methods=["GET"])
def bike_expenses():
    try:
        response = supabase.table("bike_history").select("*").execute()
        data = sorted(response.data, key=lambda x: x["at_distance"])
        monthly, weekly = calculate_expenses(data)

        return jsonify({
            "monthly_expenses": monthly,
            "weekly_expenses": weekly
        })

    except Exception as e:
        print("🚨 Error fetching expenses:", e)
        return jsonify({"error": "Failed to fetch expenses"}), 500


@app.route("/", methods=["GET"])
def index():
    return "🚴 Bike Tracker API is running."


if __name__ == "__main__":
    app.run(debug=True)
