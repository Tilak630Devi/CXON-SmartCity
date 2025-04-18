from flask import Flask, jsonify
from flask_cors import CORS
import threading
import time
from pymongo import MongoClient

app = Flask(__name__)
CORS(app)  # Enable CORS for all routes

# Connect to your MongoDB server
client = MongoClient('mongodb+srv://chudgayeguru7:MMMT%404_CXON@cluster0.a9o67.mongodb.net/')
db = client['parking_db']
collection = db['sensor_data']

def get_last_values():
    # Query for the document with _id "fixed_sensor_data" (adjust if needed)
    document = collection.find_one({"_id": "fixed_sensor_data"})
    if not document:
        return {}
    
    last_values = {}
    # Iterate over each key except _id and extract the last value if it is a non-empty list
    for key, value in document.items():
        if key == '_id':
            continue
        if isinstance(value, list) and value:
            last_values[key] = value[-1]
        else:
            last_values[key] = None
    return last_values

@app.route('/data')
def data():
    return jsonify(get_last_values())

if __name__ == '__main__':

    # Run the Flask app.
    app.run(host='0.0.0.0', port=1000)
