import json
import os

# Load hospital data on startup
# Normalize keys to lowercase
# Load the NHS 100 diseases data
with open(os.path.join(os.path.dirname(__file__), 'nhs_top_100_diseases.json')) as f:
    nhs_diseases = json.load(f)


with open(os.path.join(os.path.dirname(__file__), 'static/export.json')) as f:
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

from flask import request, jsonify

@app.route('/api/predict', methods=['POST'])
def predict_disease():
    data = request.get_json()
    selected_symptoms = [s.strip().lower() for s in data.get('symptoms', [])]

    results = []
    for disease in nhs_diseases:
        disease_symptoms = [s.lower() for s in disease['symptoms']]
        match_count = len(set(selected_symptoms) & set(disease_symptoms))
        if match_count == 0:
            continue
        probability = round((match_count / len(disease_symptoms)) * 100, 2)
        results.append({
            "disease": disease["disease"],
            "match_count": match_count,
            "total_symptoms": len(disease_symptoms),
            "probability": probability
        })

    # Sort and return top 5 matches
    results.sort(key=lambda x: x['probability'], reverse=True)
    return jsonify(results[:5])



@app.route('/')
def home():
    print("Home route accessed")  # debug
    return render_template('home.html')

# ... (previous imports remain the same)

@app.route('/predict', methods=['POST'])
def predict():
    symptoms = request.form.getlist('symptoms')
    
    # Expanded disease scoring with better symptom mapping
    disease_scores = {
        "Common Cold": 0,
        "Flu": 0,
        "Migraine": 0,
        "COVID-19": 0,
        "Gastroenteritis": 0,
        "Hypertension": 0,
        "Diabetes Type 2": 0,
        "Asthma": 0,
        "Urinary Tract Infection": 0,
        "Irritable Bowel Syndrome": 0,
        "Eczema": 0
    }

    symptom_mapping = {
        # Flu symptoms
        "fever": ["Flu", "COVID-19"],
        "cough": ["Flu", "COVID-19", "Asthma"],
        "sore throat": ["Flu", "Common Cold"],
        "fatigue": ["Flu", "COVID-19", "Diabetes Type 2"],
        "headache": ["Flu", "Migraine", "Hypertension"],
        
        # Common Cold symptoms
        "sneezing": ["Common Cold"],
        "stuffy nose": ["Common Cold"],
        "mild headache": ["Common Cold"],
        
        # COVID-19 symptoms
        "dry cough": ["COVID-19"],
        "loss of taste or smell": ["COVID-19"],
        "breathlessness": ["COVID-19", "Asthma"],
        
        # Asthma symptoms
        "shortness of breath": ["Asthma"],
        "wheezing": ["Asthma"],
        "chest tightness": ["Asthma"],
        
        # Diabetes symptoms
        "increased thirst": ["Diabetes Type 2"],
        "frequent urination": ["Diabetes Type 2", "Urinary Tract Infection"],
        "blurred vision": ["Diabetes Type 2", "Hypertension"],
        "tiredness": ["Diabetes Type 2"],
        
        # Hypertension symptoms
        "dizziness": ["Hypertension"],
        "nosebleeds": ["Hypertension"],
        
        # Migraine symptoms
        "nausea": ["Migraine"],
        "vomiting": ["Migraine"],
        "sensitivity to light": ["Migraine"],
        "aura": ["Migraine"],
        
        # UTI symptoms
        "burning urination": ["Urinary Tract Infection"],
        "pelvic pain": ["Urinary Tract Infection"],
        "cloudy urine": ["Urinary Tract Infection"],
        
        # IBS symptoms
        "abdominal pain": ["Irritable Bowel Syndrome"],
        "bloating": ["Irritable Bowel Syndrome"],
        "diarrhea": ["Irritable Bowel Syndrome"],
        "constipation": ["Irritable Bowel Syndrome"],
        
        # Eczema symptoms
        "itchy skin": ["Eczema"],
        "dry patches": ["Eczema"],
        "redness": ["Eczema"],
        "rash": ["Eczema"]
    }

    # Score diseases based on selected symptoms
    for symptom in symptoms:
        s = symptom.lower()
        if s in symptom_mapping:
            for disease in symptom_mapping[s]:
                disease_scores[disease] += 1

    # Normalize to percentages
    max_score = max(disease_scores.values()) or 1  # prevent division by zero
    probabilities = {disease: round((score / max_score) * 100, 2) 
                    for disease, score in disease_scores.items()}

    return render_template('dashboard.html', 
                         disease_probabilities=probabilities, 
                         checked_symptoms=symptoms)


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
        
        if User.query.filter_by(username=username).first():
            flash('Username already exists')
        else:
            user = User(username=username)
            user.set_password(password)
            db.session.add(user)
            db.session.commit()
            flash('Registration successful! Please login.')
            return redirect(url_for('login'))
    
    return render_template('register.html') 

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