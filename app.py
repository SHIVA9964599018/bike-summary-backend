from supabase import create_client, Client
from datetime import datetime, timedelta
from collections import defaultdict, OrderedDict
import os
from dotenv import load_dotenv

load_dotenv()

SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

MONTH_ORDER = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]


def calculate_summary(data):
    if not data or len(data) < 2:
        print("❌ Not enough data to calculate summary")
        return

    data = sorted(data, key=lambda x: x["at_distance"])
    total_distance = data[-1]["at_distance"] - data[0]["at_distance"]
    total_expense = sum(row["amount"] for row in data[:-1])
    total_fuel = total_expense / 103
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


def calculate_expenses(data):
    monthly_grouped = defaultdict(lambda: defaultdict(lambda: {"amount": 0.0, "distance": 0.0}))
    weekly_grouped = defaultdict(float)

    today = datetime.today()
    one_week_ago = today - timedelta(days=7)

    for row in data:
        try:
            date = datetime.fromisoformat(row["date_changed"])
            year = str(date.year)
            month = date.strftime("%b")
            amount = float(row["amount"])
            distance = float(row["at_distance"])

            monthly_grouped[year][month]["amount"] += amount
            monthly_grouped[year][month]["distance"] += distance

            if date >= one_week_ago:
                week_label = date.strftime("%Y-%m-%d")
                weekly_grouped[week_label] += amount

        except Exception as parse_err:
            print(f"⚠️ Skipping row due to error: {parse_err}")
            continue

    # Sort the months using MONTH_ORDER
    ordered_monthly = {}
    for year, months in monthly_grouped.items():
        sorted_months = OrderedDict()
        for month in MONTH_ORDER:
            if month in months:
                sorted_months[month] = months[month]
        ordered_monthly[year] = sorted_months

    # Format nicely
    final_monthly_expenses = {
        year: {
            month: {
                "amount": round(info["amount"], 2),
                "distance": round(info["distance"], 2)
            } for month, info in months.items()
        } for year, months in ordered_monthly.items()
    }

    print("📊 Monthly Expenses with Distance:", final_monthly_expenses)
    print("📈 Weekly Expenses:", dict(weekly_grouped))


def main():
    try:
        response = supabase.table("bike_history").select("*").execute()
        data = response.data
        sorted_data = sorted(data, key=lambda x: x["at_distance"])
        print("\n📦 Fetched Data:")
        for row in sorted_data:
            print(row)

        print("\n------ Summary ------")
        calculate_summary(data)

        print("\n------ Expenses ------")
        calculate_expenses(data)

    except Exception as e:
        print("🚨 Error fetching data:", e)


if __name__ == "__main__":
    main()
