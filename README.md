# 🐱 Cat Adoption Platform

A full-featured Flask web app connecting cat lovers with adoptable pets. Includes admin tools, real-time chat, and an intuitive adoption process.

---

## ✨ Features

- **User System**
  - Registration, login, and user profiles
- **Pet Listings**
  - Admins can post adoptable cats with images
- **Adoption Process**
  - Users apply to adopt
  - Real-time chat between users and admins (WebSocket)
  - Admin can approve or reject applications
- **Admin Controls**
  - Manage pet listings and adoption requests
  - Mark pets as adopted (automated visibility logic)

---

## 🛠️ Installation

### 1. Clone the Repository
```bash
git clone https://github.com/yourusername/cat-adoption.git
cd cat-adoption

### 2. Create and Activate Virtual Environment
python -m venv venv
source venv/bin/activate  # Mac/Linux
venv\Scripts\activate     # Windows

### 3. Install Dependencies
pip install -r requirements.txt

### 4. Initialize database
flask db init
flask db migrate
flask db upgrade

```
### 6.Run the application
## 🚀 Usage
### 👑 Admin
Access the /admin dashboard
Create pets

View and manage applications

### 🙋 Regular Users
View available cats

Submit adoption applications

Chat with admins

### 🙋‍♀️ About the Author
Built with 💙 by Rinad.
Solo developer. Cat lover. Future full-stack pro! 🧑‍💻✨