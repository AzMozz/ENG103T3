from flask import Flask, render_template, request, redirect, url_for, session, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import timedelta
import json
import os
import dropbox

app = Flask(__name__)
app.secret_key = 'your_secret_key'  # Replace with a strong, unique key in a real project
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(minutes=30)  # Session timeout
USER_FILE = 'users.json'
DROPBOX_APP_KEY = "csjuutbmdc20u95"
DROPBOX_APP_SECRET = "1t15sf6afrgb6rt"
DROPBOX_ACCESS_TOKEN = "sl.B-1vol6pfXlwZt_xqmJprbYN77c8iVSNTMgyUKE5RwzLu7tz_RmBBipaqeHnupRoCXSTA9zjagSvmFlOMtWQeTwQ8wMWQz5g7VCnzk9khd82FQm3z2XX-Jx6hMmClfUdEbgClaf7qbKc"
DROPBOX_REFRESH_TOKEN = "lVfESq_Qgh0AAAAAAAAAAWr7uWN09iHPKUdIC72kHB8OVV_1YiRCx9CiIehisUOZ"

dbx = dropbox.Dropbox(
    oauth2_access_token=DROPBOX_ACCESS_TOKEN,
    oauth2_refresh_token=DROPBOX_REFRESH_TOKEN,
    app_key=DROPBOX_APP_KEY,
    app_secret=DROPBOX_APP_SECRET
)

# Helper function to load users
def load_users():
    if os.path.exists(USER_FILE):
        with open(USER_FILE, 'r') as file:
            return json.load(file)
    return {}

# Helper function to save users
def save_users(users):
    with open(USER_FILE, 'w') as file:
        json.dump(users, file)

# List all health data files from Dropbox
def list_health_data_files():
    try:
        files = []
        for entry in dbx.files_list_folder('/HealthData').entries:
            if isinstance(entry, dropbox.files.FileMetadata):
                files.append(entry.path_lower)
        return files
    except Exception as e:
        print(f"Error listing files: {e}")
        return []

# Retrieve file content from Dropbox
def get_file_content_from_dropbox(file_path):
    try:
        metadata, response = dbx.files_download(file_path)
        content = response.content.decode('utf-8')
        file_data = []
        for line in content.strip().split('\n'):
            timestamp, bpm_str, spo2_str = line.split(', ')
            bpm_value = float(bpm_str.split(': ')[1])
            spo2_value = float(spo2_str.split(': ')[1])
            file_data.append({
                "timestamp": timestamp,
                "bpm": round(bpm_value),
                "spo2": round(spo2_value)
            })
        return file_data
    except Exception as e:
        print(f"Error downloading file {file_path}: {e}")
        return []

# Registration route
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        users = load_users()

        if username in users:
            return 'Username already exists. Please choose a different one.'

        hashed_password = generate_password_hash(password)
        users[username] = hashed_password
        save_users(users)

        return redirect(url_for('login'))

    return render_template('register.html')

# Login route
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        users = load_users()

        if username in users and check_password_hash(users[username], password):
            session['username'] = username
            return redirect(url_for('view_health_data'))
        else:
            return 'Invalid credentials, please try again.'

    return render_template('login.html')

# Logout route
@app.route('/logout')
def logout():
    session.pop('username', None)
    return redirect(url_for('login'))

# Route to aggregate and return health data as JSON
@app.route('/get_all_health_data', methods=['GET'])
def get_all_health_data():
    files = list_health_data_files()
    all_data = []
    for file in files:
        file_data = get_file_content_from_dropbox(file)
        all_data.extend(file_data)
    return jsonify({"data": all_data})

# Dashboard view route
@app.route('/view_health_data', methods=['GET'])
def view_health_data():
    if 'username' not in session:
        return redirect(url_for('login'))
    username = session['username']
    return render_template('view_health_data.html', username=username)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)