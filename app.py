

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

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        print("[INFO] Already logged in, redirecting to dashboard")
        return redirect(url_for('home'))

    
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
    
    return render_template('login.html')

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