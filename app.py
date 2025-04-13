from flask import Flask, jsonify
from flask_cors import CORS
from supabase import create_client, Client
import os
from dotenv import load_dotenv
from datetime import datetime, timedelta
from collections import defaultdict

load_dotenv()

app = Flask(__name__)
CORS(app, origins=["https://shiva9964599018.github.io"])


# Replace these with your Supabase project details
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

def calculate_summary(data):
    if not data or len(data) < 2:
        return {"error": "Not enough data"}

    data = sorted(data, key=lambda x: x["at_distance"])
    total_distance = data[-1]["at_distance"] - data[0]["at_distance"]
   # total_expense = sum(row["amount"] for row in data)
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

    return {
        "total_distance_km": total_distance,
        "total_fuel_liters": round(total_fuel, 2),
        "mileage_kmpl": mileage,
        "total_expense": total_expense,
        "monthly_expense": monthly_expense,
        "weekly_expense": weekly_expense,
    }

@app.route("/api/bike-summary")
def bike_summary():
    try:
        response = supabase.table("bike_history").select("*").execute()
        data = response.data
        summary = calculate_summary(data)
        return jsonify(summary)
    except Exception as e:
        print("🚨 Error in /api/bike-summary:", e)
        return jsonify({"error": str(e)}), 500

@app.route("/api/bike-expenses")
def bike_expenses():
    try:
        response = supabase.table("bike_history").select("*").execute()
        data = response.data

        # Monthly Expenses grouped by year and month
        monthly_grouped = defaultdict(lambda: defaultdict(float))
        weekly_grouped = defaultdict(float)

        today = datetime.today()
        one_week_ago = today - timedelta(days=7)

        for row in data:
            try:
                date = datetime.fromisoformat(row["date_changed"])
                year = str(date.year)
                month = date.strftime("%b")  # Jan, Feb, etc.
                amount = float(row["amount"])

                monthly_grouped[year][month] += amount

                if date >= one_week_ago:
                    week_label = date.strftime("%Y-%m-%d")
                    weekly_grouped[week_label] += amount
            except Exception as parse_err:
                print(f"Skipping row due to error: {parse_err}")
                continue

        return jsonify({
            "monthly_expenses": monthly_grouped,
            "weekly_expenses": weekly_grouped
        })
from collections import defaultdict

def organize_expenses(data):
    monthly_data = defaultdict(lambda: defaultdict(float))  # year -> month -> total
    weekly_data = defaultdict(float)  # date (yyyy-mm-dd) -> total

    today = datetime.today()
    one_week_ago = today - timedelta(days=7)

    for row in data:
        date_str = row["date_changed"]
        try:
            date_obj = datetime.fromisoformat(date_str)
        except ValueError:
            continue

        amount = row["amount"]
        year = str(date_obj.year)
        month = date_obj.strftime("%b")  # Jan, Feb, etc.
        monthly_data[year][month] += amount

        if date_obj >= one_week_ago:
            week_day = date_obj.strftime("%Y-%m-%d")
            weekly_data[week_day] += amount

    return {
        "monthly_breakdown": monthly_data,
        "weekly_breakdown": weekly_data,
    }

@app.route("/api/bike-summary")
def bike_summary():
    try:
        response = supabase.table("bike_history").select("*").execute()
        data = response.data
        summary = calculate_summary(data)
        expenses = organize_expenses(data)

        return jsonify({**summary, **expenses})
    except Exception as e:
        print("🚨 Error in /api/bike-summary:", e)
        return jsonify({"error": str(e)}), 500

    except Exception as e:
        print("🚨 Error in /api/bike-expenses:", e)
        return jsonify({"error": str(e)}), 500


