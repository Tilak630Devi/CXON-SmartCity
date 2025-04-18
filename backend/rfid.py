from flask import Flask, request, jsonify
from pymongo import MongoClient

app = Flask(__name__)

# Setup MongoDB connection (adjust the URI as necessary)
client = MongoClient('mongodb+srv://chudgayeguru7:MMMT%404_CXON@cluster0.a9o67.mongodb.net/')
db = client['parking_db']                       # Change to your database name
collection = db['parking_locations']            # Change to your collection name

@app.route('/data', methods=['POST'])
def receive_data():
    # Get the raw data sent by the ESP32
    raw_data = request.data
    try:
        data_str = raw_data.decode('utf-8').strip()
    except Exception as e:
        return jsonify({"error": "Failed to decode data", "message": str(e)}), 400
    
    print("Received data:", data_str)
    
    # Expected format: {slot_no,occupied,rfid_no?} e.g. {25,No} or {25,Yes,1A2B3C}
    # Remove surrounding curly braces
    if data_str.startswith('{') and data_str.endswith('}'):
        data_str = data_str[1:-1]
    else:
        return jsonify({"error": "Data format incorrect"}), 400

    # Split the data by comma
    parts = data_str.split(',')
    if len(parts) < 2:
        return jsonify({"error": "Insufficient data parts"}), 400

    # Extract and validate the slot number
    try:
        slot_no = int(parts[0].strip())
    except ValueError:
        return jsonify({"error": "Slot number must be an integer"}), 400

    # Extract occupancy status and (if applicable) the RFID number
    occupied_value = parts[1].strip()
    if occupied_value.lower() == "yes":
        if len(parts) < 3:
            return jsonify({"error": "RFID number missing for occupied slot"}), 400
        rfid_no = parts[2].strip()
    else:
        # For "No", we clear out the RFID value
        rfid_no = ""

    # Use the positional operator "$" to update the matching array element
    result = collection.update_one(
        {"Name": "Andheri Parking Lot", "rfid_scanners.slot_no": slot_no},
        {"$set": {
            "rfid_scanners.$.occupied": occupied_value,
            "rfid_scanners.$.rfid_no": rfid_no
        }}
    )

    if result.matched_count == 0:
        return jsonify({"error": "No matching slot found for update"}), 404

    message = f"Successfully updated slot {slot_no}" if result.modified_count == 1 else f"No changes made for slot {slot_no}"
    return jsonify({"status": "success", "message": message}), 200

if __name__ == '__main__':
    # Run the server on all network interfaces, port 5000.
    app.run(host='0.0.0.0', port=4000, debug=True)
