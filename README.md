# TownSense 🚀🏙️

TownSense is a modern AI-powered solution designed to detect and automatically report urban issues like potholes, unauthorized graffiti, overflowing trash bins, and illegally parked cars. By analyzing images captured from street cameras, drones, or smartphones, TownSense helps cities maintain cleanliness, safety, and efficiency.

## 🌟 Features Overview

* **Image Analysis:** Automatically detect urban issues using AI.
* **Direct Reporting:** Easily submit issues with automatic address recognition through reverse geocoding.
* **Email Integration:** Reports are directly sent via email, ensuring swift response from city authorities.
* **Community Feedback:** Users can provide feedback, helping our AI learn and improve continuously.
* **Contact Webhook:** Quickly turns feedback into actionable tickets via an integrated webhook system.

## 🛠️ Tech Stack

* **Languages:** Python, JavaScript, HTML, CSS
* **Frontend:** Streamlit
* **Backend:** Flask
* **Database:** MongoDB Atlas (CosmosDB)
* **AI Models:** YOLO (You Only Look Once) for fast, real-time image detection; GitHub AI API for advanced analysis.

## 📦 Key Python Packages

* Flask
* Streamlit
* Ultralytics YOLO
* Requests
* Pillow (PIL)
* PyMongo
* bcrypt

## 🤖 AI and Self-Learning

TownSense employs YOLO models for rapid detection of common urban issues. Advanced interpretation of detected problems is further enhanced by GitHub's AI API. Moreover, the AI learns continuously through community feedback, adapting its detection accuracy and recommendations to user insights.

## ✉️ Direct Communication

Reported issues generate automatic email notifications containing details and images, enabling rapid action from authorities. The built-in contact form directly creates support tickets through a webhook integration, streamlining communication.

## 🚀 Installation and Quickstart

### 📥 Clone the Repository

```bash
git clone <repository_url>
cd TownSense
```

### 🐍 Install Dependencies

```bash
pip install -r requirements.txt
```

### ▶️ Launching the Application

Run the application using the provided script:

```bash
python main.py
```

This script ensures the backend is live before automatically launching the frontend Streamlit app.

### 🌐 Accessing the Application

Open your browser and navigate to:

```
http://localhost:8501
```

## 🎨 Frontend Customization

Use the provided `styles.py` to easily customize UI elements like buttons and containers, maintaining a consistent and appealing visual style across the application.
