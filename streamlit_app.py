import os
import streamlit as st
import cv2
import numpy as np
from PIL import Image
from keras.models import load_model
import datetime
import sqlite3
import gdown

folder_id = "1gxwtPi8rupeMSOU6UGg9GnV_c76Xq8kv"
SAVE_PATH = "fake_image_classifier.h5"
# ✅ Download the folder if it doesn't exist
if not os.path.exists(SAVE_PATH):
    gdown.download_folder(id = folder_id, output=SAVE_PATH, quiet=False)

# --- SQLite Database Setup ---
DATABASE_PATH = "predictions.db"

def get_db_connection():
    conn = sqlite3.connect(DATABASE_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row  # Optional: fetch rows as dictionaries if needed
    return conn

def create_table():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS predictions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            image_filename TEXT,
            label TEXT NOT NULL,
            real_confidence REAL NOT NULL,
            deepfake_confidence REAL NOT NULL,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()

create_table()

# --- Model Loading Section ---
# This code assumes that the file 'fake_image_classifier.h5' is present in the repository root.
# IMPORTANT: Ensure that this file is not tracked by Git LFS (or that Git LFS is correctly configured in your deployment environment)
MODEL_LOCAL_PATH = SAVE_PATH

if not os.path.exists(MODEL_LOCAL_PATH):
    st.error("Model file not found. Please ensure 'fake_image_classifier.h5' is in the repository.")
    st.stop()

@st.cache_resource
def load_detection_model():
    st.info("Loading model...")
    model = load_model(MODEL_LOCAL_PATH)
    st.success("Model loaded!")
    return model

model = load_detection_model()

# --- Image Preprocessing Function ---
def preprocess_image(pil_image, target_size=224):
    # Convert the PIL image to a NumPy array
    image = np.array(pil_image)
    # Ensure image has 3 channels; if not, convert to RGB
    if image.ndim == 2:
        image = cv2.cvtColor(image, cv2.COLOR_GRAY2RGB)
    elif image.shape[2] == 4:  # If image has an alpha channel
        image = cv2.cvtColor(image, cv2.COLOR_RGBA2RGB)
    # Convert from RGB (PIL) to BGR (OpenCV)
    image = cv2.cvtColor(image, cv2.COLOR_RGB2BGR)
    # Resize the image
    image = cv2.resize(image, (target_size, target_size))
    # Normalize pixel values
    image = image / 255.0
    # Expand dimensions to create a batch of 1
    image = np.expand_dims(image, axis=0)
    return image

# --- Streamlit App Layout ---
st.title("Deepfake Detector")
st.write("Upload an image to check if it is a deepfake. The result and image info will be stored in our database.")

# File uploader widget
uploaded_file = st.file_uploader("Choose an image (JPG, JPEG, PNG)", type=["jpg", "jpeg", "png"])

if uploaded_file is not None:
    # Display the uploaded image using the new 'use_container_width' parameter
    image = Image.open(uploaded_file)
    st.image(image, caption="Uploaded Image", use_container_width=True)
    
    if st.button("Predict"):
        try:
            # Preprocess the image
            img_input = preprocess_image(image)
            # Run model prediction
            probability = model.predict(img_input)[0][0]
            # Determine label based on threshold (adjust threshold if necessary)
            label = "Real" if probability > 0.5 else "Deepfake"
            real_confidence = probability * 100
            deepfake_confidence = (1 - probability) * 100

            # Display prediction results
            st.write(f"**Prediction:** {label}")
            st.write(f"**Confidence:** {real_confidence:.2f}% Real, {deepfake_confidence:.2f}% Deepfake")

            # Save the uploaded file locally (in an 'uploads' folder)
            uploads_dir = "uploads"
            if not os.path.exists(uploads_dir):
                os.makedirs(uploads_dir)
            filename = os.path.join(uploads_dir, uploaded_file.name)
            with open(filename, "wb") as f:
                f.write(uploaded_file.getbuffer())

            # Save the prediction to the SQLite database
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO predictions (image_filename, label, real_confidence, deepfake_confidence, timestamp)
                VALUES (?, ?, ?, ?, ?)
            """, (filename, label, real_confidence, deepfake_confidence, datetime.datetime.utcnow()))
            conn.commit()
            conn.close()

            st.success("Prediction saved to the database!")
        except Exception as e:
            st.error(f"An error occurred: {e}")
