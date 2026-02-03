🐱 CutePaws — Cat Adoption Platform

CutePaws is a full-stack Flask web application that connects cat lovers with adoptable pets in Saudi Arabia.
It supports a complete adoption workflow, real-time messaging, admin moderation, and automated background tasks.

✨ Features
👤 User Features

Browse Pets — Filter adoptable cats by city.

Adoption Applications — Submit detailed questionnaires for adoption requests.

Real-Time Chat — Instantly message admins without page refresh (Socket.IO).

User Accounts — Secure user registration and authentication.

👑 Admin Features

Admin Dashboard — Create, edit, and manage pet listings (including image uploads).

Application Review — View adopter questionnaires directly inside the chat interface.

Adoption Status Management

Mark pets as Adopted

Pets remain visible for 48 hours with an “Adopted” badge

Automatically archived after 48 hours

Admin Messaging — Communicate with applicants in real time.

⚙️ Technical Overview

Backend: Flask, Flask-SQLAlchemy, Flask-SocketIO

Frontend: Bootstrap 5, JavaScript, Jinja2

Database: SQLite (development) with SQLAlchemy ORM

Background Tasks: APScheduler (automated cleanup of adopted pets)

Architecture: Application factory pattern

🛠️ Installation & Setup

Follow these steps to run the project locally.

1️⃣ Clone the Repository
git clone https://github.com/yourusername/cat-adoption.git
cd cat-adoption

2️⃣ Create & Activate a Virtual Environment
# Windows
python -m venv venv
venv\Scripts\activate

# macOS / Linux
python3 -m venv venv
source venv/bin/activate

3️⃣ Install Dependencies
pip install -r requirements.txt

🐚 Flask App Configuration (Important)

This project uses an application factory pattern, and the Flask app lives inside a package rather than a flat app.py file.

Because of this, Flask cannot automatically detect the app unless it is explicitly specified.

One-Time Setup (Recommended)

On macOS / Linux, run:

export FLASK_APP=cutepaws.wepsite


After setting this once, you can safely run:

flask shell
flask db upgrade
flask run


💡 This step is required for database commands and the Flask shell to work correctly.

🗄️ Database Initialization
Using Flask-Migrate (Recommended)
flask db init
flask db migrate -m "Initial migration"
flask db upgrade

If Tables Are Missing (Quick Fix)

If you encounter an error like:

sqlite3.OperationalError: no such table: pet


Run:

flask shell


Then inside the shell:

from wepsite import db
db.create_all()


This ensures all database tables exist before background tasks run.

▶️ Running the Application
python main.py


The app will be available at:

http://127.0.0.1:5000

🚀 How to Use
🔑 Creating an Admin User

By default, all newly registered users are regular users.

To enable admin features:

Register a new account (e.g. admin@test.com)

Open the database file:

instance/database.db


using DB Browser for SQLite

Open the user table

Change:

is_admin = 0 → 1


Save changes and log in again

You now have full admin access 🎉

🔄 Background Scheduler Behavior

The application includes an APScheduler job that runs:

Immediately on startup

Then every 6 hours

Its job:

Find pets marked as Adopted

Automatically archive them after 48 hours

⚠️ Important:
If database tables do not exist when the app starts, the scheduler will raise errors.
This is why database initialization is required before running the server.

📂 Project Structure
cutepaws/
├── migrations/          # Database migrations
├── wepsite/             # Main application package (intentional name)
│   ├── static/
│   │   ├── javaScript/  # Socket.IO client logic
│   │   └── uploads/     # Uploaded pet images
│   ├── templates/       # Jinja2 HTML templates
│   ├── models.py        # Database models
│   └── views.py         # Routes and business logic
├── instance/            # SQLite database
├── main.py              # Application entry point
└── requirements.txt     # Python dependencies

⚠️ Note About the wepsite Folder Name

The folder name wepsite is intentionally kept as-is.

While this is a typo of website, renaming it at this stage would require:

Updating all imports

Updating Flask configuration

Updating migrations

Updating scheduler references

To avoid breaking the project, the name has been preserved and documented instead.

❤️ Final Notes

CutePaws was built as a learning-focused full-stack project, combining:

backend logic

real-time communication

background automation

and clean project structure

Contributions, suggestions, and improvements are always welcome ✨