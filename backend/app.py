import os
import time
import signal
import sys
import csv
from datetime import datetime
import requests
from twilio.rest import Client
import pytz
import urllib.parse
from flask import Flask, request, jsonify
from flask_cors import CORS

# Initialize Flask app
app = Flask(__name__)
CORS(app)  # Allow cross-origin requests
UPLOAD_FOLDER = 'uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Ensure the upload folder exists
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

# Path to store the latest uploaded CSV file
UPLOADED_CSV_PATH = os.path.join(UPLOAD_FOLDER, 'lead_data.csv')

# Load credentials from environment variables
ELEVENLABS_API_KEY = os.getenv("sk_de1ade198998dc97d0b5c96d95fc2d158010c38607a8479d")
TWILIO_ACCOUNT_SID = os.getenv("ACed85b2a2d2293fc43f14651be7ad2f58")
TWILIO_AUTH_TOKEN = os.getenv("61f2de50b64cf4c0c03587bdc1d2080f")
TWILIO_PHONE_NUMBER = os.getenv("+19152847071")
AGENT_PHONE_NUMBER_ID = os.getenv("phnum_01jxh9xvwwep5arskcwfm6aa02")
AGENT_ID = os.getenv("agent_01jxffk5wve1c99nb58dfatxv3")

# Validate credentials
if not all([ELEVENLABS_API_KEY, TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, TWILIO_PHONE_NUMBER, AGENT_PHONE_NUMBER_ID, AGENT_ID]):
    raise ValueError("Missing required environment variables. Please set ELEVENLABS_API_KEY, TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, TWILIO_PHONE_NUMBER, AGENT_PHONE_NUMBER_ID, and AGENT_ID.")

# Initialize clients
twilio_client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
ist_tz = pytz.timezone('Asia/Kolkata')

# Global flag for graceful shutdown
running = True

def signal_handler(sig, frame):
    """Handle graceful shutdown on interrupt"""
    global running
    print("ℹ️ Shutting down gracefully...")
    running = False
    sys.exit(0)

def fetch_agent_config():
    """Fetch the agent's configuration to debug dynamic variables"""
    try:
        url = f"https://api.elevenlabs.io/v1/convai/agents/{AGENT_ID}"
        headers = {
            "xi-api-key": ELEVENLABS_API_KEY,
            "Content-Type": "application/json"
        }
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()
        config = response.json()
        print(f"📋 Agent Configuration: {config}")
        return config
    except Exception as e:
        print(f"❌ Error fetching agent config: {e}")
        return None

def generate_dynamic_twiml_url(conversation_id):
    """Generate a dynamic TwiML URL with the conversation_id"""
    if not conversation_id or conversation_id == "N/A":
        raise ValueError("Invalid conversation_id for TwiML URL generation")
    
    twiml = f'<?xml version="1.0" encoding="UTF-8"?><Response><Connect><Stream url="wss://api.elevenlabs.io/v1/convai/conversation"><Parameter name="conversation_id" value="{conversation_id}" /></Stream></Connect></Response>'
    encoded_twiml = urllib.parse.quote(twiml)
    twiml_url = f"https://twimlets.com/echo?Twiml={encoded_twiml}"
    return twiml_url

def check_call_status(call_sid, max_attempts=6, delay=5):
    """Check the status of a Twilio call with multiple attempts"""
    for attempt in range(max_attempts):
        try:
            call = twilio_client.calls(call_sid).fetch()
            print(f"📞 Call Status for SID {call.sid} (Attempt {attempt + 1}): {call.status}")
            print(f"📞 Call Duration: {call.duration if call.duration else 'N/A'} seconds")
            print(f"📞 Call Start Time: {call.start_time if call.start_time else 'N/A'}")
            print(f"📞 Call End Time: {call.end_time if call.end_time else 'N/A'}")
            
            if call.status in ["failed", "busy", "no-answer", "completed", "canceled"]:
                if call.status == "failed":
                    print(f"⚠️ Call Failed - Error Code: {call.error_code}, Error Message: {call.error_message}")
                return call.status
            elif call.status == "in-progress":
                print("📞 Call is in progress, continuing to monitor...")
            time.sleep(delay)  # Wait before the next attempt
        except Exception as e:
            print(f"❌ Error checking call status for SID {call_sid}: {e}")
            return None
    print(f"⚠️ Call status still not final after {max_attempts} attempts")
    return None

def initiate_outbound_call(phone_number, customer_name):
    """Initiate an outbound call with Twilio and pass CustomerName to ElevenLabs, with no retries"""
    print(f"📞 Attempting to call {customer_name} ({phone_number})...")
    try:
        # Validate phone number length
        digits = ''.join(filter(str.isdigit, phone_number))
        if len(digits) != 12:  # +91 (2 digits) + 10 digits
            raise ValueError(f"Invalid phone number format: {phone_number}. Expected 10 digits after +91.")

        # Step 1: Initiate the call with ElevenLabs Conversational AI
        elevenlabs_url = "https://api.elevenlabs.io/v1/convai/twilio/outbound-call"
        headers = {
            "xi-api-key": ELEVENLABS_API_KEY,
            "Content-Type": "application/json"
        }
        payload = {
            "to_number": phone_number,
            "agent_id": AGENT_ID,
            "agent_phone_number_id": AGENT_PHONE_NUMBER_ID,
            "conversation_initiation_client_data": {
                "dynamic_variables": {
                    "CustomerName": customer_name
                }
            }
        }

        print(f"📡 Initiating ElevenLabs call for {customer_name} ({phone_number})...")
        print(f"Request URL: {elevenlabs_url}")
        print(f"Request Payload: {payload}")
        response = requests.post(elevenlabs_url, json=payload, headers=headers, timeout=15)
        response.raise_for_status()
        conv_data = response.json()
        print(f"Response from ElevenLabs: {conv_data}")
        conversation_id = conv_data.get("conversation_id", "N/A")
        print(f"✅ ElevenLabs call initiated: {conversation_id}")

        # Step 2: Generate dynamic TwiML URL
        twiml_url = generate_dynamic_twiml_url(conversation_id)
        print(f"📋 Generated TwiML URL: {twiml_url}")

        # Step 3: Use Twilio to dial the number with dynamic TwiML
        call = twilio_client.calls.create(
            to=phone_number,
            from_=TWILIO_PHONE_NUMBER,
            url=twiml_url,
            timeout=55
        )
        print(f"✅ Twilio call initiated: {call.sid}")

        # Step 4: Check call status with multiple attempts
        final_status = check_call_status(call.sid, max_attempts=6, delay=5)

        return conversation_id, call.sid, final_status

    except requests.exceptions.HTTPError as e:
        print(f"❌ HTTP Error initiating call for {customer_name} ({phone_number}): {e}")
        print(f"Response Text: {e.response.text if e.response else 'N/A'}")
        return None, None, "failed"
    except Exception as e:
        print(f"❌ Error initiating call for {customer_name} ({phone_number}): {e}")
        return None, None, "failed"

def process_lead_data():
    """Read customer data from the uploaded CSV file and initiate outbound calls"""
    print("🚀 Starting batch outbound calls...")

    # Set up signal handler for graceful shutdown
    signal.signal(signal.SIGINT, signal_handler)

    # Fetch agent configuration for debugging
    fetch_agent_config()

    # Check if a CSV file has been uploaded
    if not os.path.exists(UPLOADED_CSV_PATH):
        print("❌ No CSV file uploaded. Please upload a file first.")
        return "No CSV file uploaded. Please upload a file first."

    # Read customer data from the CSV file
    data = []
    try:
        with open(UPLOADED_CSV_PATH, 'r', encoding='utf-8') as csv_file:
            csv_reader = csv.reader(csv_file)
            data = list(csv_reader)[1:]  # Skip header row
    except Exception as e:
        print(f"❌ Error reading CSV file: {e}")
        return f"Error reading CSV file: {str(e)}"

    # Process each row in the CSV
    for idx, row in enumerate(data, 1):
        if not running:
            print("⚠️ Batch process interrupted, stopping...")
            break

        customer_name = row[0] if row else "Unknown"
        phone_number = row[1] if len(row) > 1 else None

        # Skip rows with missing data
        if not customer_name or not phone_number:
            print(f"⚠️ Skipping row {idx + 1}: Missing customer name or phone number")
            continue

        print(f"\n🔍 Processing {idx}/{len(data)}: {customer_name} ({phone_number})")

        # Ensure phone number is in E.164 format (e.g., +91 for India)
        if not phone_number.startswith("+"):
            phone_number = "+91" + phone_number

        # Initiate the outbound call with no retries
        conversation_id, call_sid, final_status = initiate_outbound_call(phone_number, customer_name)

        # Log the result
        if conversation_id and call_sid and final_status in ["completed", "in-progress"]:
            print(f"✅ Call successfully initiated for {customer_name}: Conv ID {conversation_id}, Call SID {call_sid}, Status: {final_status}")
        else:
            print(f"❌ Call failed for {customer_name}: Status: {final_status}")

        # Add a delay to avoid rate limits
        time.sleep(2)

    print("🏁 Batch calling completed")
    return "Batch calling completed successfully."

# Flask routes
@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return jsonify({"status": "error", "message": "No file part in the request"}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({"status": "error", "message": "No file selected"}), 400
    
    if file and file.filename.endswith('.csv'):
        file.save(UPLOADED_CSV_PATH)
        return jsonify({"status": "success", "message": "File uploaded successfully"}), 200
    else:
        return jsonify({"status": "error", "message": "Please upload a CSV file"}), 400

@app.route('/run-script', methods=['POST'])
def run_script():
    result = process_lead_data()
    return jsonify({"status": "success", "message": result}), 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 5000)))