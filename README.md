# 👁️ Drishti-AI: A Vision for the Visually Impaired

**Drishti-AI** (formerly AI-Eye) is an intelligent, real-time navigation assistant built to empower visually impaired individuals. By turning a simple camera feed into a descriptive voice, it helps users safely navigate their environment. 

Imagine walking into a room and having a personal assistant instantly whisper in your ear: *"Person is 1.5 meters away straight ahead"* or *"Chair is 2 meters away on your left."* That is exactly what Drishti-AI does.

---

## 🚀 How It Works (The Magic Behind the Scenes)

When a user turns on the camera, the system performs the following steps in a fraction of a second:
1. **Sees the World**: Captures the live video feed using the React Frontend.
2. **Detects Obstacles**: Sends the video frames to a Flask Backend where an advanced AI model (**YOLOv8**) instantly recognizes objects (people, cars, furniture, etc.).
3. **Calculates Distance & Direction**: A custom Machine Learning model calculates exactly how far the object is (in meters) and figures out if it's on the left, right, or straight ahead.
4. **Speaks to the User**: Using an intelligent Text-to-Speech system running in the background, it verbally warns the user about the obstacle without ever freezing or slowing down the video feed.

---

## ✨ Key Features

- **⚡ Real-Time Object Detection**: Uses **YOLOv8** for lightning-fast detection of everyday obstacles.
- **📏 Distance Estimation**: Custom-trained AI predicts the physical distance (in meters) to objects.
- **🧭 Directional Awareness**: Tells the user exactly where the object is (Left, Right, or Center).
- **🗣️ Smart Audio Navigation**: Uses a stable `AnnouncementTracker` so the AI doesn't annoy the user by repeating itself. It only speaks when objects move significantly or new obstacles appear.
- **🤖 LLM Integration (Ollama)**: Capable of generating natural, human-like sentences using large language models.
- **🔐 Secure User Authentication**: Users can create profiles, save emergency contacts, and personalize their experience.

---

## 🛠️ Technology Stack

- **Frontend**: React.js, Vite, Vanilla CSS
- **Backend**: Python, Flask, SQLite (Database)
- **Computer Vision**: OpenCV (`cv2`), YOLOv8 (Ultralytics)
- **Machine Learning**: PyTorch, Scikit-Learn
- **Text-to-Speech**: pyttsx3, Windows SAPI, PowerShell Fallbacks

---

## 💻 Exact Commands to Start the Project

To run this project on your local machine, follow these simple step-by-step commands. You will need to open **two separate terminal windows**.

### Prerequisites
Make sure you have installed:
- **Node.js** (v16+)
- **Python** (v3.9+)
- **Ollama** (Download from [ollama.com](https://ollama.com/) if you want to use the LLM features)

---

### Step 1: Start the Backend (Terminal 1)
Open your first terminal, navigate to the main `Drishti-AI` folder, and run these commands:

```bash
# 1. Go into the backend folder
cd backend

# 2. Install all the required Python libraries (Only needed the first time)
pip install -r requirements.txt

# 3. Start the Flask AI Server
python app.py
```
*(Leave this terminal running. You should see a message saying the Flask server is running on port 5000.)*

---

### Step 2: Start the Frontend (Terminal 2)
Open a **new** second terminal, navigate to the main `Drishti-AI` folder, and run these commands:

```bash
# 1. Go into the frontend folder
cd AI-EYE-Frontend

# 2. Install the Node packages (Only needed the first time)
npm install

# 3. Start the React development server
npm run dev
```

### Step 3: Open the App
- Once both terminals are running, open your web browser.
- Go to the URL provided by the frontend terminal (usually `http://localhost:5173`).
- **Register/Login**, allow camera permissions, and the AI will start guiding you!

---

## 📄 License
This project is open-source and created to make the world a more accessible place.
