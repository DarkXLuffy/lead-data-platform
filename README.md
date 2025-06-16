Lead Data Management Platform
This project provides a web platform to upload a CSV file containing lead data and run a Python script to process the data by making outbound calls using Twilio and ElevenLabs.
Project Structure

static/: Contains the frontend files (HTML, CSS, JavaScript) for GitHub Pages.
backend/: Contains the Flask backend app (app.py) and dependencies (requirements.txt).
uploads/: Temporary folder for storing uploaded CSV files (used by the backend).

Setup Instructions
1. Host the Frontend on GitHub Pages

Create a new GitHub repository (e.g., lead-data-platform).
Push the entire project to the repository:git init
git add .
git commit -m "Initial commit"
git remote add origin https://github.com/<your-username>/lead-data-platform.git
git push -u origin main


Enable GitHub Pages:
Go to your repository on GitHub.
Navigate to Settings > Pages.
Set the source to the main branch and the /static folder.
Save, and GitHub will provide a URL (e.g., https://<your-username>.github.io/lead-data-platform/).



2. Deploy the Backend
The Flask backend cannot run on GitHub Pages because it requires a server to execute Python code. Deploy it on a platform like Render:
Deploy on Render

Create a new Web Service on Render (https://render.com).
Connect your GitHub repository and select the backend/ folder.
Configure the following:
Runtime: Python 3
Build Command: pip install -r requirements.txt
Start Command: python app.py


Add environment variables in Render's dashboard:
ELEVENLABS_API_KEY: Your ElevenLabs API key
TWILIO_ACCOUNT_SID: Your Twilio Account SID
TWILIO_AUTH_TOKEN: Your Twilio Auth Token
TWILIO_PHONE_NUMBER: Your Twilio phone number
AGENT_PHONE_NUMBER_ID: Your ElevenLabs agent phone number ID
AGENT_ID: Your ElevenLabs agent ID
PORT: 5000 (or leave default)


Deploy the app. Render will provide a URL (e.g., https://your-backend.onrender.com).

Update the Frontend
Update static/script.js with the Render backend URL (e.g., https://your-backend.onrender.com).
3. Test the Platform

Visit the GitHub Pages URL (e.g., https://<your-username>.github.io/lead-data-platform/).
Upload a CSV file with the format:CustomerName,PhoneNumber
John Doe,9876543210
Jane Smith,9876543211


Click "Run Script" to process the file and make outbound calls.
Check the backend logs on Render for detailed output.

Security Notes

Never commit sensitive credentials to GitHub. Use environment variables.
Add a .gitignore file to exclude the uploads/ folder and any .env files.

License
This project is for educational purposes. Ensure you comply with Twilio and ElevenLabs usage policies.
