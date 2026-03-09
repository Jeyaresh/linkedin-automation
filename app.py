from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
import csv
from datetime import datetime
import os
import subprocess
import sys
import uuid
import threading

app = Flask(__name__)
CORS(app)

PATH = 'all excels/'
BOT_PROCESS = None

# Bot dialog state: {dialog_id: {type, title, message, buttons, response?}}
BOT_DIALOGS = {}
BOT_DIALOGS_LOCK = threading.Lock()


def get_project_root():
    """Get the project root directory (where runAiBot.py lives)."""
    return os.path.dirname(os.path.abspath(__file__))
##> ------ Karthik Sarode : karthik.sarode23@gmail.com - UI for excel files ------
@app.route('/')
def home():
    """Displays the home page of the application."""
    return render_template('index.html')

@app.route('/applied-jobs', methods=['GET'])
def get_applied_jobs():
    '''
    Retrieves a list of applied jobs from the applications history CSV file.
    
    Returns a JSON response containing a list of jobs, each with details such as 
    Job ID, Title, Company, HR Name, HR Link, Job Link, External Job link, and Date Applied.
    
    If the CSV file is not found, returns a 404 error with a relevant message.
    If any other exception occurs, returns a 500 error with the exception message.
    '''

    try:
        jobs = []
        with open(PATH + 'all_applied_applications_history.csv', 'r', encoding='utf-8') as file:
            reader = csv.DictReader(file)
            for row in reader:
                jobs.append({
                    'Job_ID': row['Job ID'],
                    'Title': row['Title'],
                    'Company': row['Company'],
                    'HR_Name': row['HR Name'],
                    'HR_Link': row['HR Link'],
                    'Job_Link': row['Job Link'],
                    'External_Job_link': row['External Job link'],
                    'Date_Applied': row['Date Applied']
                })
        return jsonify(jobs)
    except FileNotFoundError:
        return jsonify({"error": "No applications history found"}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/applied-jobs/<job_id>', methods=['PUT'])
def update_applied_date(job_id):
    """
    Updates the 'Date Applied' field of a job in the applications history CSV file.

    Args:
        job_id (str): The Job ID of the job to be updated.

    Returns:
        A JSON response with a message indicating success or failure of the update
        operation. If the job is not found, returns a 404 error with a relevant
        message. If any other exception occurs, returns a 500 error with the
        exception message.
    """
    try:
        data = []
        csvPath = PATH + 'all_applied_applications_history.csv'
        
        if not os.path.exists(csvPath):
            return jsonify({"error": f"CSV file not found at {csvPath}"}), 404
            
        # Read current CSV content
        with open(csvPath, 'r', encoding='utf-8') as file:
            reader = csv.DictReader(file)
            fieldNames = reader.fieldnames
            found = False
            for row in reader:
                if row['Job ID'] == job_id:
                    row['Date Applied'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    found = True
                data.append(row)
        
        if not found:
            return jsonify({"error": f"Job ID {job_id} not found"}), 404

        with open(csvPath, 'w', encoding='utf-8', newline='') as file:
            writer = csv.DictWriter(file, fieldnames=fieldNames)
            writer.writeheader()
            writer.writerows(data)
        
        return jsonify({"message": "Date Applied updated successfully"}), 200
    except Exception as e:
        print(f"Error updating applied date: {str(e)}")  # Debug log
        return jsonify({"error": str(e)}), 500


@app.route('/start-bot', methods=['POST'])
def start_bot():
    """Starts the LinkedIn auto-apply bot in the background. Accepts username and password in JSON body."""
    global BOT_PROCESS
    if BOT_PROCESS is not None and BOT_PROCESS.poll() is None:
        return jsonify({"message": "Bot is already running", "status": "running"}), 200
    try:
        data = request.get_json() or {}
        username = (data.get("username") or "").strip()
        password = data.get("password") or ""

        if not username or not password:
            return jsonify({"error": "LinkedIn username and password are required", "status": "error"}), 400

        project_root = get_project_root()
        python_cmd = sys.executable
        env = os.environ.copy()
        env["LINKEDIN_USERNAME"] = username
        env["LINKEDIN_PASSWORD"] = password

        BOT_PROCESS = subprocess.Popen(
            [python_cmd, 'runAiBot.py'],
            cwd=project_root,
            env=env,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True
        )
        return jsonify({"message": "Auto-apply bot started", "status": "running"}), 200
    except Exception as e:
        return jsonify({"error": str(e), "status": "error"}), 500


@app.route('/stop-bot', methods=['POST'])
def stop_bot():
    """Stops the LinkedIn auto-apply bot if it is running."""
    global BOT_PROCESS
    if BOT_PROCESS is None or BOT_PROCESS.poll() is not None:
        return jsonify({"message": "Bot is not running", "status": "idle"}), 200
    try:
        BOT_PROCESS.terminate()
        try:
            BOT_PROCESS.wait(timeout=5)
        except subprocess.TimeoutExpired:
            BOT_PROCESS.kill()
        BOT_PROCESS = None
        return jsonify({"message": "Auto-apply bot stopped", "status": "idle"}), 200
    except Exception as e:
        return jsonify({"error": str(e), "status": "error"}), 500


@app.route('/status', methods=['GET'])
def bot_status():
    """Returns whether the auto-apply bot is currently running."""
    global BOT_PROCESS
    if BOT_PROCESS is not None and BOT_PROCESS.poll() is None:
        return jsonify({"status": "running"})
    return jsonify({"status": "idle"})


@app.route('/bot/request-dialog', methods=['POST'])
def bot_request_dialog():
    """Bot requests a dialog - stores it and returns dialog_id."""
    data = request.get_json() or {}
    dialog_id = str(uuid.uuid4())
    with BOT_DIALOGS_LOCK:
        BOT_DIALOGS[dialog_id] = {
            "type": data.get("type", "alert"),
            "title": data.get("title", ""),
            "message": data.get("message", ""),
            "buttons": data.get("buttons", ["OK"]),
            "response": None
        }
    return jsonify({"dialog_id": dialog_id})


@app.route('/bot/check-response')
def bot_check_response():
    """Bot polls for user response. Returns {ready: bool, response?: str}."""
    dialog_id = request.args.get("id")
    if not dialog_id:
        return jsonify({"ready": False}), 400
    with BOT_DIALOGS_LOCK:
        d = BOT_DIALOGS.get(dialog_id)
        if not d:
            return jsonify({"ready": False})
        if d["response"] is not None:
            resp = d["response"]
            del BOT_DIALOGS[dialog_id]
            return jsonify({"ready": True, "response": resp})
    return jsonify({"ready": False})


@app.route('/bot/pending-dialog')
def bot_pending_dialog():
    """Returns current pending dialog for web UI, or empty object."""
    with BOT_DIALOGS_LOCK:
        for did, d in BOT_DIALOGS.items():
            if d["response"] is None:
                return jsonify({
                    "dialog_id": did,
                    "type": d["type"],
                    "title": d["title"],
                    "message": d["message"],
                    "buttons": d["buttons"]
                })
    return jsonify({})


@app.route('/bot/respond', methods=['POST'])
def bot_respond():
    """Web UI sends user's choice."""
    data = request.get_json() or {}
    dialog_id = data.get("dialog_id")
    response = data.get("response")
    if not dialog_id or response is None:
        return jsonify({"error": "Missing dialog_id or response"}), 400
    with BOT_DIALOGS_LOCK:
        if dialog_id in BOT_DIALOGS:
            BOT_DIALOGS[dialog_id]["response"] = response
    return jsonify({"ok": True})


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    debug = 'PORT' not in os.environ
    app.run(host='0.0.0.0', port=port, debug=debug)

##<