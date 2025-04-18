from flask import Flask, jsonify, request
from flask_cors import CORS
from pymongo import MongoClient
import re
from urllib.parse import unquote
import urllib.parse

app = Flask(__name__)
CORS(app)  # Enable CORS so the frontend can access these endpoints

username = "chudgayeguru7"
password = "MMMT@4_CXON"
encoded_username = urllib.parse.quote_plus(username)
encoded_password = urllib.parse.quote_plus(password)

# MongoDB connection details
mongo_uri = f"mongodb+srv://chudgayeguru7:MMMT%404_CXON@cluster0.a9o67.mongodb.net/"
# Connect to MongoDB (adjust connection string if needed)
client = MongoClient(mongo_uri)

db = client["parking_db"]
collection = db["parking_locations"]

@app.route('/api/parkings', methods=['GET'])
def get_parkings():
    """
    Return all parking location documents from the 'parking_locations' collection.
    Each document includes "Name", "Distance_km", "Total_Slots", "Available_Slots",
    "rfid_scanners", and any fixed coordinates stored.
    """
    parkings = list(collection.find({}, {"_id": 0}))
    return jsonify(parkings)

@app.route('/api/parking/<parking_name>', methods=['GET'])
def get_parking_detail(parking_name):
    """
    Return a single parking document by searching the 'Name' field.
    The parking_name parameter is URL-decoded to ensure it matches the MongoDB data.
    """
    parking_name = unquote(parking_name)
    query = {"Name": {"$regex": re.escape(parking_name), "$options": "i"}}
    doc = collection.find_one(query, {"_id": 0})
    if doc:
        return jsonify(doc)
    else:
        return jsonify({"error": "Parking not found"}), 404

@app.route('/api/rfid', methods=['POST'])
def register_rfid():
    """
    A sample endpoint to register RFID card data.
    """
    data = request.json
    if not data:
        return jsonify({"error": "No data provided"}), 400
    rfid_collection = db["rfid_cards"]
    result = rfid_collection.insert_one(data)
    return jsonify({"message": "RFID card registered", "id": str(result.inserted_id)}), 201

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
