from flask import Flask, jsonify
from supabase import create_client, Client
from datetime import datetime, timedelta
from collections import defaultdict, OrderedDict
import os
from dotenv import load_dotenv
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

load_dotenv()
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

MONTH_ORDER = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun',
               'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']


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

            current_distance = float(row["at_distance"])
            prev_distance = float(data[i - 1]["at_distance"]) if i > 0 else current_distance
            distance_covered = max(0.0, current_distance - prev_distance)

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
                sorted_months[month] = months[month]
        ordered_monthly[year] = sorted_months

    final_monthly_expenses = {
        year: {
            month: {
                "amount": round(info["amount"], 2),
                "distance": round(info["distance"], 2)
            } for month, info in months.items()
        } for year, months in ordered_monthly.items()
    }

    return final_monthly_expenses, dict(weekly_grouped)


@app.route("/api/bike-summary", methods=["GET"])
def bike_summary():
    try:
        response = supabase.table("bike_history").select("*").execute()
        data = response.data
        sorted_data = sorted(data, key=lambda x: x["at_distance"])

        if not sorted_data or len(sorted_data) < 2:
            return jsonify({"error": "Not enough data"}), 400

        total_distance = sorted_data[-1]["at_distance"] - sorted_data[0]["at_distance"]
        total_expense = sum(row["amount"] for row in sorted_data[:-1])
        total_fuel = total_expense / 103
        mileage = round(total_distance / total_fuel, 2)

        today = datetime.today()
        this_month = today.strftime("%Y-%m")
        one_week_ago = today - timedelta(days=7)

        monthly_expense = sum(
            row["amount"] for row in sorted_data
            if row["date_changed"].startswith(this_month)
        )

        weekly_expense = sum(
            row["amount"] for row in sorted_data
            if datetime.fromisoformat(row["date_changed"]) >= one_week_ago
        )

        monthly_expenses, weekly_expenses = calculate_expenses(sorted_data)

        return jsonify({
            "total_distance_km": round(total_distance, 2),
            "total_fuel_liters": round(total_fuel, 2),
            "mileage_kmpl": mileage,
            "total_expense": round(total_expense, 2),
            "monthly_expense": round(monthly_expense, 2),
            "weekly_expense": round(weekly_expense, 2),
            "monthly_expenses": monthly_expenses,
            "weekly_expenses": weekly_expenses,
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    app.run(debug=True)
