# 🐱 CutePaws - Cat Adoption Platform

A full-stack Flask web application connecting cat lovers with adoptable pets in Saudi Arabia. Features real-time messaging, adoption workflow management, and automated pet availability scheduling.

---

## ✨ Features

### 👤 User Features
- **Browse Pets:** Filter available cats by city.
- **Adoption Applications:** Submit detailed adoption questionnaires.
- **Real-Time Chat:** Chat instantly with admins regarding applications (no page refresh needed!).
- **User Accounts:** Secure registration and login system.

### 👑 Admin Features
- **Dashboard:** Manage pet listings (upload photos, edit details).
- **Application Review:** View adopter's questionnaire answers directly within the chat interface.
- **Availability Management:** Mark pets as "Adopted" (pets remain visible for 48 hours with an "Adopted" badge before auto-archiving).
- **Messaging:** Communicate with applicants in real-time.

### ⚙️ Technical Highlights
- **Backend:** Flask, Flask-SQLAlchemy, Flask-SocketIO.
- **Frontend:** Bootstrap 5, JavaScript (Socket.IO client), Jinja2 templates.
- **Database:** SQLite (dev) / SQLAlchemy ORM.
- **Background Tasks:** APScheduler for automated cleanup of adopted pets.

---

## 🛠️ Installation & Setup

Follow these steps to run the project locally.

### 1. Clone the Repository
```bash
git clone [https://github.com/yourusername/cat-adoption.git](https://github.com/yourusername/cat-adoption.git)
cd cat-adoption

### 2. Create Virtual Environment
```bash
# Windows
python -m venv venv
venv\Scripts\activate

# Mac/Linux
python3 -m venv venv
source venv/bin/activate

### 3. Install Dependencies
```bash
pip install -r requirements.txt

### 4. Initialize Database
Run the following commands to create the database tables:
```Bash
flask db init
flask db migrate -m "Initial migration"
flask db upgrade

### 5. Run the Application
```bash
python main.py

🚀 How to Use
🔑 Important: Creating an Admin User
By default, new registrations are regular users. To test admin features (like adding pets):

Register a new account on the website (e.g., admin@test.com).

Open the database file instance/database.db using a tool like DB Browser for SQLite.

Find the user table.

Locate your user and change the is_admin column from 0 (or False) to 1 (or True).

Save changes and log in again.

📂 Project Structure
cutepaws/
├── migrations/          # Database migrations
├── wepsite/             # Application package
│   ├── static/          # CSS, JS, Images
│   │   ├── javaScript/  # Socket.IO logic
│   │   └── uploads/     # User uploaded pet photos
│   ├── templates/       # HTML files
│   ├── models.py        # Database models
│   └── views.py         # Routes and logic
├── instance/            # SQLite Database
├── main.py              # Entry point
└── requirements.txt     # Python dependencies
