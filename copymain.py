
from flask import Flask, render_template, request, redirect, url_for, session, flash, send_file
import pickle, pandas as pd, numpy as np
import uuid, hashlib, sqlite3
from models import db, SymptomHistory
from werkzeug.security import generate_password_hash, check_password_hash
from fpdf import FPDF
import os
from datetime import datetime
import pytz

app = Flask(__name__)
app.secret_key = 'your_secret_key'

app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///history.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db.init_app(app)

# Load model and label encoder
with open("disease_model_with_le.pkl", "rb") as f:
    data = pickle.load(f)
    model = data["model"]
    le = data["label_encoder"]

# Load training data columns to get symptom names
df = pd.read_csv("dataset/Training.csv")
symptoms_list = df.columns[:-1].tolist()
symptoms_dict = {symptom.lower(): idx for idx, symptom in enumerate(symptoms_list)}

# Load description and medication data
desc_df = pd.read_csv("dataset/description.csv")
med_age_df = pd.read_csv("dataset/Disease_Medication_Age_MatchedDosage.csv")

# Clean column names
med_age_df.columns = [col.strip().replace(" ", "") for col in med_age_df.columns]

desc_dict = dict(zip(desc_df['Disease'].str.lower(), desc_df['Description']))

# Load precautions data
precautions_df = pd.read_csv("dataset/precautions_df.csv")
precautions_dict = precautions_df.set_index('Disease').T.to_dict('list')
precautions_dict = {
    disease.lower(): [str(p).strip() for p in precautions if pd.notna(p)]
    for disease, precautions in precautions_dict.items()
}

# PDF Generation Setup
DB_PATH = "instance/history.db"
PDF_PATH = "history_output.pdf"

class PDF(FPDF):
    def header(self):
        self.set_font("Arial", 'B', 14)
        self.cell(0, 10, "Patient History Report", border=False, ln=True, align='C')
        self.ln(5)

    def table_header(self, headers):
        self.set_font("Arial", 'B', 12)
        for header in headers:
            self.cell(38, 10, header, border=1)
        self.ln()

    def table_row(self, row):
        self.set_font("Arial", '', 10)
        for col in row:
            self.cell(38, 10, str(col), border=1)
        self.ln()

def generate_pdf():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("SELECT id, user_id, symptoms, predicted_disease, timestamp FROM symptom_history")
    rows = cursor.fetchall()

    headers = ["ID", "User ID", "Symptoms", "Predicted Disease", "Timestamp"]
    col_widths = [15, 25, 60, 50, 40]

    pdf = PDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()

    # Draw header
    pdf.set_font("Arial", 'B', 12)
    for i, header in enumerate(headers):
        pdf.cell(col_widths[i], 10, header, border=1)
    pdf.ln()

    # Set font for data
    pdf.set_font("Arial", '', 10)

    for row in rows:
        x_start = pdf.get_x()
        y_start = pdf.get_y()

        # Calculate the height of each cell using split_only
        line_heights = []
        split_texts = []

        for i, text in enumerate(row):
            text = str(text)
            text_width = col_widths[i]
            text_lines = pdf.multi_cell(text_width, 5, text, border=0, split_only=True)
            line_heights.append(5 * len(text_lines))
            split_texts.append(text_lines)

        row_height = max(line_heights)

        # Page break if needed
        if y_start + row_height > pdf.h - pdf.b_margin:
            pdf.add_page()
            pdf.set_font("Arial", 'B', 12)
            for i, header in enumerate(headers):
                pdf.cell(col_widths[i], 10, header, border=1)
            pdf.ln()
            pdf.set_font("Arial", '', 10)
            x_start = pdf.get_x()
            y_start = pdf.get_y()

        # Write each cell with border and proper row height
        for i, lines in enumerate(split_texts):
            x = pdf.get_x()
            y = pdf.get_y()
            text = '\n'.join(lines)
            pdf.multi_cell(col_widths[i], row_height / max(1, len(lines)), text, border=1, align='L')
            pdf.set_xy(x + col_widths[i], y)

        pdf.ln(row_height)

    pdf.output(PDF_PATH)
    conn.close()

# Routes for the main app

@app.route("/")
def home():
    return render_template('home.html')

@app.route("/predict", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        input_symptoms = request.form.get("symptoms", "").lower()
        typed_symptoms = [sym.strip() for sym in input_symptoms.split(",") if sym.strip()]

        age = request.form.get("age")
        duration = request.form.get("duration_days")
        pain_intensity = request.form.get("pain_intensity", "").lower()  # Get pain intensity

        try:
            age = int(age)
        except (ValueError, TypeError):
            return "Invalid age entered", 400

        try:
            duration = int(duration)
        except (ValueError, TypeError):
            duration = 0

        input_vector = np.zeros(len(symptoms_list))
        matched_any = False

        for symptom in typed_symptoms:
            if symptom in symptoms_dict:
                input_vector[symptoms_dict[symptom]] = 1
                matched_any = True

        if not matched_any:
            error_msg = "None of the entered symptoms matched the database. Please check spelling or try different symptoms."
            return render_template("index.html", error=error_msg)

        pred_index = model.predict([input_vector])[0]
        predicted_disease = le.inverse_transform([pred_index])[0]
        key = predicted_disease.lower()
        description = desc_dict.get(key, "Description not available.")

        disease_precautions = precautions_dict.get(key, ["No precautions available."])
        if len(disease_precautions) > 1:
            disease_precautions = disease_precautions[1:]
        else:
            disease_precautions = []

        medications = []
        precaution_message = None

        # Check for high pain intensity
        if pain_intensity == "high":
            precaution_message = "Pain intensity is high. Please consult a doctor immediately."
            medications = []
            disease_precautions = []
        elif duration > 5:
            precaution_message = "Duration of the symptoms is more than 5 days. Please consult a doctor immediately."
            medications = []
            disease_precautions = []
        else:
            if duration > 2:
                precaution_message = None
            else:
                def age_in_group(age, group):
                    try:
                        parts = group.replace("–", "-").split("-")
                        if len(parts) == 2:
                            min_age, max_age = map(int, parts)
                            return min_age <= age <= max_age
                    except:
                        pass
                    return False

                try:
                    filtered = med_age_df[
                        (med_age_df['Disease'].str.lower() == key) &
                        (med_age_df['AgeGroup'].apply(lambda group: age_in_group(age, str(group))))
                    ]

                    if not filtered.empty:
                        medications = [
                            f"{row['Medications']} ({row['Dosage']}, Age Group {row['AgeGroup']})"
                            for _, row in filtered.iterrows()
                        ]
                    else:
                        medications = ["No medications found for this age group."]
                except Exception as e:
                    medications = [f"Error retrieving medication data: {e}"]

                precaution_message = None
                disease_precautions = []

        return render_template("result.html",
                               prediction=predicted_disease,
                               description=description,
                               medications=medications,
                               symptoms=input_symptoms,
                               precaution=precaution_message,
                               disease_precautions=disease_precautions,
                               error=None)

    return render_template('index.html')


@app.route('/save_history', methods=['POST'])
def save_history():
    symptoms = request.form.get("symptoms")
    predicted_disease = request.form.get("predicted_disease")
    user_id = session.get("user_id")

    if not user_id:
        return redirect(url_for('login'))

    hashed_user_id = hashlib.sha256(str(user_id).encode()).hexdigest()

    new_entry = SymptomHistory(
        user_id=hashed_user_id,
        symptoms=symptoms,
        predicted_disease=predicted_disease
    )
    db.session.add(new_entry)
    db.session.commit()

    return redirect(url_for('history'))

# @app.route('/login', methods=['GET', 'POST'])
# def login():
#     if request.method == 'POST':
#         email = request.form['email']
#         password = request.form['password']

#         conn = sqlite3.connect("instance/users.db")
#         cursor = conn.cursor()
#         cursor.execute("SELECT id, name, dob, gender, email, password FROM users WHERE email = ?", (email,))
#         user = cursor.fetchone()
#         conn.close()

#         if user and check_password_hash(user[5], password):
#             session['user'] = user[4]
#             session['user_id'] = user[0]
#             session['user_data'] = {
#                 "id": user[0],
#                 "name": user[1],
#                 "dob": user[2],
#                 "gender": user[3],
#                 "email": user[4],
#             }
#             session['is_admin'] = (email == 'admin@example.com')
#             return redirect(url_for('admin' if session['is_admin'] else 'dashboard'))
#         else:
#             return "Invalid email or password", 401

#     return render_template('login.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        conn = sqlite3.connect("instance/users.db")
        cursor = conn.cursor()
        cursor.execute("SELECT id, name, dob, gender, email, password FROM users WHERE email = ?", (email,))
        user = cursor.fetchone()
        conn.close()

        if user and check_password_hash(user[5], password):
            session['user'] = user[4]
            session['user_id'] = user[0]
            session['user_data'] = {
                "id": user[0],
                "name": user[1],
                "dob": user[2],
                "gender": user[3],
                "email": user[4],
            }
            session['is_admin'] = (email == 'admin@example.com')

            ist = pytz.timezone('Asia/Kolkata')
            ist_now = datetime.now(ist).strftime('%Y-%m-%d %H:%M:%S')


            # ✅ Log the login timestamp to userlog.db
            log_conn = sqlite3.connect("instance/userlog.db")
            log_cursor = log_conn.cursor()
            log_cursor.execute('''
                INSERT INTO userlog (user_id, timestamp)
                VALUES (?, ?)
            ''', (user[0],ist_now))
            log_conn.commit()
            log_conn.close()

            return redirect(url_for('admin' if session['is_admin'] else 'dashboard'))
        else:
            return "Invalid email or password", 401

    return render_template('login.html')

@app.route('/dashboard')
def dashboard():
    if 'user' in session:
        return render_template('dashboard.html', user=session['user'])
    return redirect(url_for('login'))

@app.route('/profile')
def profile():
    if 'user_data' in session:
        return render_template('profile.html', user=session['user_data'])
    return redirect(url_for('login'))

@app.route('/admin')
def admin():
    if not session.get('is_admin'):
        return "Access denied", 403

    histories = SymptomHistory.query.order_by(SymptomHistory.timestamp.desc()).all()
    return render_template('admin.html', entries=histories)

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        name = request.form['name']
        dob = request.form['dob']
        gender = request.form['gender']
        email = request.form['email']
        password = request.form['password']

        try:
            dob_date = datetime.strptime(dob, '%Y-%m-%d').date()
        except ValueError:
            flash("Invalid date format for DOB. Please use YYYY-MM-DD.", "danger")
            return redirect(url_for('signup'))

        today = datetime.today().date()

        # DOB must be less than today
        if dob_date >= today:
            flash("Enter a valid Date of Birth (cannot be today ).", "danger")
            return redirect(url_for('signup'))

        # Check if user is at least 18
        age = today.year - dob_date.year - ((today.month, today.day) < (dob_date.month, dob_date.day))
        if age < 18:
            flash("You must be at least 18 years old to sign up.", "danger")
            return redirect(url_for('signup'))

        # Validate password length
        if len(password) < 8:
            flash("Password must be at least 8 characters long.", "danger")
            return redirect(url_for('signup'))

        hashed_password = generate_password_hash(password)
        user_id = str(uuid.uuid4())

        conn = sqlite3.connect("instance/users.db")
        cursor = conn.cursor()

        cursor.execute("SELECT * FROM users WHERE email = ?", (email,))
        if cursor.fetchone():
            conn.close()
            flash("User already exists!", "danger")
            return redirect(url_for('signup'))

        cursor.execute('''
            INSERT INTO users (id, name, dob, gender, email, password)
            VALUES (?, ?, ?, ?, ?, ?)''',
                       (user_id, name, dob, gender, email, hashed_password))

        conn.commit()
        conn.close()

        flash("Signup successful!", "success")
        return redirect(url_for('login'))

    return render_template('signup.html')

@app.route('/history')
def history():
    user_id = session.get('user_id')
    if not user_id:
        return redirect(url_for('login'))

    hashed_user_id = hashlib.sha256(str(user_id).encode()).hexdigest()
    history_entries = SymptomHistory.query.filter_by(user_id=hashed_user_id).order_by(SymptomHistory.timestamp.desc()).all()

    return render_template('history.html', entries=history_entries)

# Add PDF download route
@app.route('/download', methods=['POST'])
def download():
    generate_pdf()
    return send_file(PDF_PATH, as_attachment=True)

# if __name__ == '__main__':
#     print("Starting Flask server...")
#     app.run(debug=True, port=5000)


if __name__ == '__main__':
    # print("Starting Flask server...")
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port, debug=True)
