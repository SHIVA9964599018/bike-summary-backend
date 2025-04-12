from flask import Flask, jsonify
from flask_cors import CORS
from supabase import create_client, Client
import os
from dotenv import load_dotenv
from datetime import datetime, timedelta

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


