from flask import Flask, request, render_template, redirect, url_for, session, jsonify, flash
import os
import cv2
import numpy as np
import requests  # For downloading the model file
from keras.models import load_model
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from config import Config

app = Flask(__name__)
app.config.from_object(Config)
db = SQLAlchemy(app)

# -------------------------------
# Database Model for Users
# -------------------------------
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
        
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

# Uncomment and run once to create tables, then comment out:
# with app.app_context():
#     db.create_all()

# -------------------------------
# Model Download & Loading Section
# -------------------------------
# Replace MODEL_URL with the actual public URL where your model is hosted.
MODEL_URL = 'https://example.com/path/to/fake_image_classifier.h5'
MODEL_LOCAL_PATH = 'fake_image_classifier.h5'

def download_model():
    if not os.path.exists(MODEL_LOCAL_PATH):
        print("Downloading model from external source...")
        response = requests.get(MODEL_URL, stream=True)
        if response.status_code == 200:
            with open(MODEL_LOCAL_PATH, 'wb') as f:
                for chunk in response.iter_content(chunk_size=1024):
                    if chunk:
                        f.write(chunk)
            print("Model download complete.")
        else:
            raise Exception("Failed to download model. Status code: {}".format(response.status_code))
    else:
        print("Model already exists locally.")

download_model()
model = load_model(MODEL_LOCAL_PATH)

def preprocess_image(image_path, target_size=224):
    img = cv2.imread(image_path)
    if img is None:
        return None
    img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    img = cv2.resize(img, (target_size, target_size))
    img = img / 255.0
    img = np.expand_dims(img, axis=0)
    return img

# -------------------------------
# Routes
# -------------------------------

# Home page: full-page layout with header, about, and contact sections.
@app.route('/')
def home():
    return render_template('index.html')

# Contact route: process contact form submissions.
@app.route('/contact', methods=['POST'])
def contact():
    email = request.form.get('email', '').strip()
    message = request.form.get('message', '').strip()
    if email and message:
        # Here you could add logic to email the details or store them.
        flash("Thank you for contacting us. We'll get back to you soon!", "success")
    else:
        flash("Please fill out both fields.", "error")
    return redirect(url_for('home'))

# User Registration (Sign Up)
@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        username = request.form.get('username', '').strip().lower()
        password = request.form.get('password', '')
        confirm_password = request.form.get('confirm_password', '')
        
        if not name or not username or not password or not confirm_password:
            flash("Please fill out all fields.", "error")
            return redirect(url_for('signup'))
        if password != confirm_password:
            flash("Passwords do not match.", "error")
            return redirect(url_for('signup'))
        if User.query.filter_by(username=username).first():
            flash("Username already exists.", "error")
            return redirect(url_for('signup'))
        
        new_user = User(name=name, username=username)
        new_user.set_password(password)
        db.session.add(new_user)
        db.session.commit()
        flash("Registration successful. Please log in.", "success")
        return redirect(url_for('login'))
    
    return render_template('signup.html')

# Login Route
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username', '').strip().lower()
        password = request.form.get('password', '')
        user = User.query.filter_by(username=username).first()
        if user and user.check_password(password):
            session['logged_in'] = True
            session['username'] = user.username
            session['name'] = user.name
            return redirect(url_for('dashboard'))
        else:
            flash("Invalid username or password.", "error")
            return redirect(url_for('login'))
    return render_template('login.html')

# Logout Route
@app.route('/logout')
def logout():
    session.clear()
    flash("You have been logged out.", "info")
    return redirect(url_for('home'))

# Dashboard Route (protected)
@app.route('/dashboard')
def dashboard():
    if not session.get('logged_in'):
        flash("Please log in to access the dashboard.", "error")
        return redirect(url_for('login'))
    return render_template('dashboard.html')

# Prediction API Endpoint (protected)
@app.route('/predict', methods=['POST'])
def predict():
    if not session.get('logged_in'):
        return jsonify({'error': 'Unauthorized'}), 401
    if 'image' not in request.files:
        return jsonify({'error': 'No image provided'}), 400
    file = request.files['image']
    os.makedirs('uploads', exist_ok=True)
    filepath = os.path.join('uploads', file.filename)
    file.save(filepath)
    image_input = preprocess_image(filepath)
    if image_input is None:
        return jsonify({'error': 'Error processing image'}), 400

    probability = model.predict(image_input)[0][0]
    label = 'real' if probability > 0.5 else 'fake'
    real_percentage = probability * 100
    fake_percentage = (1 - probability) * 100

    result = {
        'fake_percentage': fake_percentage,
        'real_percentage': real_percentage,
        'label': label
    }
    return jsonify(result)

if __name__ == '__main__':
    app.run(debug=True)
