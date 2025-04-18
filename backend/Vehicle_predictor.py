# File: merged_backend.py
import threading
from flask import Flask, request, jsonify
from flask_cors import CORS
import joblib
from datetime import datetime
import pandas as pd

# =============================================
# Vehicle Prediction App (Port 8000)
# =============================================
app_vehicle = Flask("vehicle_app")
CORS(app_vehicle)

# ----------------------------
# Load the Random Forest Vehicle Model
# ----------------------------
model_vehicle_filename = "random_forest_vehicle_model.joblib"
try:
    vehicle_model = joblib.load(model_vehicle_filename)
    print("Random Forest vehicle model loaded successfully.")
except Exception as e:
    print("Error loading Random Forest vehicle model:", e)
    vehicle_model = None

# ----------------------------
# Helper Function: Preprocess Input for Vehicle Model
# ----------------------------
def preprocess_input(data):
    """
    Expects a JSON payload with:
      - "date" (in "YYYY-MM-DD" format),
      - "time" (in "HH:MM:SS" or "HH:MM" format),
      - "junction" (numeric, one of 1, 2, or 3).
      
    Converts the date and time into a Unix timestamp and constructs
    a feature vector: [timestamp, junction] in a pandas DataFrame.
    Returns the feature DataFrame and None if successful; otherwise, returns None and an error message.
    """
    try:
        date_str = data.get("date")
        time_str = data.get("time")
        junction_val = data.get("junction")
        if not date_str or not time_str or junction_val is None:
            raise ValueError("Missing one or more required keys: 'date', 'time', 'junction'")

        # Parse date and time; support both "HH:MM:SS" and "HH:MM"
        try:
            target_datetime = datetime.strptime(f"{date_str} {time_str}", "%Y-%m-%d %H:%M:%S")
        except ValueError:
            target_datetime = datetime.strptime(f"{date_str} {time_str}", "%Y-%m-%d %H:%M")
        
        # Convert DateTime to Unix timestamp
        timestamp_value = target_datetime.timestamp()

        # Validate and convert junction value to int (must be 1, 2, or 3)
        junction_num = int(junction_val)
        if junction_num not in [1, 2, 3]:
            raise ValueError("Junction value must be 1, 2, or 3.")

        # Create the feature vector in a DataFrame with correct column names
        feature_vector = pd.DataFrame([[timestamp_value, junction_num]], columns=["timestamp", "Junction"])
        return feature_vector, None
    except Exception as e:
        return None, str(e)

# ----------------------------
# API Endpoint: Predict Vehicle Count
# ----------------------------
@app_vehicle.route('/api/predict', methods=['POST'])
def predict_vehicle():
    try:
        if vehicle_model is None:
            return jsonify({"error": "Vehicle model not loaded."}), 500

        input_json = request.get_json(force=True)
        print("Received JSON input for vehicle prediction:", input_json)
        # Validate required keys
        if "date" not in input_json or "time" not in input_json or "junction" not in input_json:
            error_msg = "JSON input must contain 'date', 'time', and 'junction' keys."
            return jsonify({"error": error_msg}), 400
        
        # Preprocess the input
        features, error_msg = preprocess_input(input_json)
        if error_msg:
            return jsonify({"error": error_msg}), 400

        # Make prediction using the Random Forest model
        prediction = vehicle_model.predict(features)[0]
        response = {
            "predicted_vehicle_count": prediction
        }
        return jsonify(response), 200

    except Exception as e:
        error_msg = f"Error during prediction: {e}"
        return jsonify({"error": error_msg}), 500

# =============================================
# Air Quality Prediction App (Port 8050)
# =============================================
app_air = Flask("air_quality_app")
CORS(app_air)

# -------------------------------
# Load the Random Forest Air Quality Model
# -------------------------------
try:
    air_model = joblib.load("random_forest_air_quality_model.pkl")
    print("Loaded Random Forest air quality model successfully.")
except Exception as e:
    print("Error loading air quality model:", e)
    air_model = None

# -------------------------------
# Define AQI Calculation Functions for SO₂ and NO₂
# -------------------------------
def calculate_sub_index(C, bp_low, bp_high, index_low, index_high):
    """
    Calculate the pollutant sub-index using linear interpolation.
    """
    return ((index_high - index_low) / (bp_high - bp_low)) * (C - bp_low) + index_low

def get_sub_index(C, breakpoints, AQI_values):
    """
    Determine the pollutant sub-index given a concentration.
    """
    for i in range(len(breakpoints) - 1):
        if breakpoints[i] <= C <= breakpoints[i + 1]:
            return calculate_sub_index(C, breakpoints[i], breakpoints[i + 1],
                                       AQI_values[i], AQI_values[i + 1])
    return AQI_values[-1]

# Hypothetical breakpoint definitions (update with official values if needed)
NO2_breakpoints = [0, 40, 80, 180, 280, 400]
NO2_AQI_values  = [0, 50, 100, 200, 300, 400]
SO2_breakpoints = [0, 40, 80, 380, 800, 1600]
SO2_AQI_values  = [0, 50, 100, 200, 300, 400]

# -------------------------------
# API Endpoint: Predict AQI
# -------------------------------
@app_air.route('/predict_aqi', methods=['POST'])
def predict_aqi():
    try:
        if air_model is None:
            return jsonify({"error": "Air quality model not loaded."}), 500

        # Get JSON input from the POST request.
        data = request.get_json()
        date_input = data.get("date")            # Expected format: "YYYY-MM-DD"
        loc_choice = data.get("loc_choice")        # Expected: "1", "2", or "3"
        
        # Define location features based on loc_choice
        if loc_choice == "1":
            loc_features = {
                'type_Industrial Areas': 1,
                'type_Residential and others': 0,
                'type_Residential, Rural and other Areas': 0
            }
        elif loc_choice == "2":
            loc_features = {
                'type_Industrial Areas': 0,
                'type_Residential and others': 1,
                'type_Residential, Rural and other Areas': 0
            }
        elif loc_choice == "3":
            loc_features = {
                'type_Industrial Areas': 0,
                'type_Residential and others': 0,
                'type_Residential, Rural and other Areas': 1
            }
        else:
            # Default to "Residential, Rural and other Areas" if invalid choice.
            loc_features = {
                'type_Industrial Areas': 0,
                'type_Residential and others': 0,
                'type_Residential, Rural and other Areas': 1
            }
        
        # Prepare Feature Input for the Model
        dt = datetime.strptime(date_input, "%Y-%m-%d")
        year = dt.year
        month = dt.month

        features = {
            'year': year,
            'month': month
        }
        features.update(loc_features)
        X_new = pd.DataFrame([features])
        
        # Predict pollutant levels using the loaded model
        predicted_values = air_model.predict(X_new)
        # Assume the model outputs pollutant levels in the order: [so2, no2, rspm, spm]
        pred_so2, pred_no2, _, _ = predicted_values[0]
        print(f"Predicted SO₂: {pred_so2:.4f}, NO₂: {pred_no2:.4f}")

        # Calculate AQI Sub-Indices for SO₂ and NO₂
        so2_index = get_sub_index(pred_so2, SO2_breakpoints, SO2_AQI_values)
        no2_index = get_sub_index(pred_no2, NO2_breakpoints, NO2_AQI_values)
        overall_AQI = max(so2_index, no2_index)
        
        return jsonify({
            "predicted_so2": pred_so2,
            "predicted_no2": pred_no2,
            "so2_index": so2_index,
            "no2_index": no2_index,
            "overall_AQI": overall_AQI
        })
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# =============================================
# Running Both Apps Concurrently on Different Ports
# =============================================
def run_vehicle_app():
    app_vehicle.run(host="0.0.0.0", port=8000, debug=True, use_reloader=False)

def run_air_app():
    app_air.run(host="0.0.0.0", port=8050, debug=True, use_reloader=False)

if __name__ == '__main__':
    vehicle_thread = threading.Thread(target=run_vehicle_app)
    air_thread = threading.Thread(target=run_air_app)
    vehicle_thread.start()
    air_thread.start()
    vehicle_thread.join()
    air_thread.join()
