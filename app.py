import json
import os

# Load hospital data on startup
# Normalize keys to lowercase
with open(os.path.join(os.path.dirname(__file__), 'maharashtra_hospitals.json')) as f:
    raw_data = json.load(f)
    hospitals_by_city = {k.strip().lower(): v for k, v in raw_data.items()}



from flask import Flask, render_template, redirect, url_for, flash, request
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
import dash
from dash import dcc, html
import os
from dash.dependencies import Input, Output, State

# Initialize Flask
app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key-123'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///site.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Initialize database
db = SQLAlchemy(app)

# User model
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(120), nullable=False)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

# Login manager
login_manager = LoginManager(app)
login_manager.login_view = 'login'

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Flask routes
@app.route('/')
def home():
    print("Home route accessed")  # debug
    return render_template('home.html')

@app.route('/predict', methods=['POST'])
def predict():
    symptoms = request.form.getlist('symptoms')

    disease_scores = {
        "Common Cold": 0,
        "Flu": 0,
        "Migraine": 0,
        "COVID-19": 0,
        "Gastroenteritis": 0,
        "Hypertension": 0,
        "Diabetes": 0,
        "Depression": 0,
        "Asthma": 0,
        "Urinary Tract Infection (UTI)": 0,
        "Arthritis": 0,
        "Skin Allergy": 0,
    }

    for symptom in symptoms:
        s = symptom.lower()
        if "fever" in s or "chills" in s:
            disease_scores["Flu"] += 2
            disease_scores["COVID-19"] += 2
            disease_scores["Common Cold"] += 1
        if "head" in s or "migraine" in s:
            disease_scores["Migraine"] += 3
        if "cough" in s or "short of breath" in s:
            disease_scores["COVID-19"] += 2
            disease_scores["Asthma"] += 1
        if "abdomen" in s or "vomit" in s or "nauseated" in s:
            disease_scores["Gastroenteritis"] += 3
            disease_scores["UTI"] += 1
        if "tired" in s or "weak" in s:
            disease_scores["Diabetes"] += 2
            disease_scores["Depression"] += 1
            disease_scores["Hypertension"] += 1
        if "dry" in s or "thirsty" in s:
            disease_scores["Diabetes"] += 3
        if "sleep" in s:
            disease_scores["Depression"] += 2
        if "pain" in s or "leg" in s or "back" in s or "joint" in s:
            disease_scores["Arthritis"] += 2
        if "itch" in s or "scratch" in s or "skin" in s:
            disease_scores["Skin Allergy"] += 3
        if "urinate" in s or "pelvis" in s:
            disease_scores["UTI"] += 2

    # Normalize to probabilities (simple scaling)
    total = sum(disease_scores.values()) + 1e-5  # avoid divide by zero
    probabilities = {disease: round((score / total) * 100, 2) for disease, score in disease_scores.items()}

    return render_template('dashboard.html', disease_probabilities=probabilities, checked_symptoms=symptoms)


@app.route('/dashnew')
def dashb():
    print("Dashboard route accessed")  # debug
    return render_template('dashnew.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        print("[INFO] Already logged in, redirecting to dashboard")
        return redirect(url_for('dashb'))

    
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        print(f"[DEBUG] Attempting login for user: {username}")
        user = User.query.filter_by(username=username).first()
        
        if user and user.check_password(password):
            login_user(user)
            print("[INFO] Login successful, redirecting to dashboard")
            return redirect(url_for('home'))

        else:
            flash('Invalid username or password')
            print("[WARN] Login failed")
    
    return render_template('dashnew.html')

@app.route('/logout')
def logout():
    logout_user()
    return redirect('/')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        print(f"[DEBUG] Registering user: {username}")
        
        if User.query.filter_by(username=username).first():
            flash('Username already exists')
            print("[WARN] Username already exists")
        else:
            user = User(username=username)
            user.set_password(password)
            db.session.add(user)
            db.session.commit()
            flash('Registration successful! Please login.')
            print("[INFO] Registration successful")
            return redirect('/login')

from flask import jsonify, request

@app.route('/api/hospitals')
def get_hospitals():
    city = request.args.get('city', '').strip().lower()
    matches = hospitals_by_city.get(city, [])
    return jsonify(matches)

    return render_template('register.html')

# Initialize Dash
dash_app = dash.Dash(__name__, server=app, url_base_pathname='/dashboard/')

dash_app.layout = html.Div([
    html.H1("Welcome to your Health Dashboard", style={'textAlign': 'center'}),
    dcc.Dropdown(
        id='symptom-selector',
        options=[{'label': s, 'value': s} for s in ['Fever', 'Cough', 'Fatigue']],
        multi=True
    ),
    html.Button('Predict', id='predict-button'),
    html.Div(id='prediction-output')
])

@dash_app.callback(
    Output('prediction-output', 'children'),
    Input('predict-button', 'n_clicks'),
    State('symptom-selector', 'value')
)
def predict(n_clicks, symptoms):
    if n_clicks and symptoms:
        return f"Predicted condition based on {', '.join(symptoms)}"
    return "Select symptoms and click predict"

# Protect Dash route
@app.route('/dashboard/')
@login_required
def dashboard():
    return redirect('/dashboard/')

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)