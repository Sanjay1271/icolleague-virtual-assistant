import os
import sqlite3
import openai
from flask import Flask, render_template, request, jsonify, redirect, session
from werkzeug.security import generate_password_hash, check_password_hash

# ---------------- OPENAI ----------------
openai.api_key = os.getenv("OPENAI_API_KEY")

# ---------------- FLASK ----------------
app = Flask(__name__)
app.secret_key = "icolleague_secret_key"

# ---------------- DATABASE ----------------
def db():
    return sqlite3.connect("database.db")


def init_db():
    conn = db()
    cur = conn.cursor()

    # USERS
    cur.execute("""
    CREATE TABLE IF NOT EXISTS users(
        username TEXT PRIMARY KEY,
        password TEXT NOT NULL
    )
    """)

    # KNOWLEDGE BASE WITH DEPARTMENT
    cur.execute("""
    CREATE TABLE IF NOT EXISTS knowledge(
        question TEXT PRIMARY KEY,
        answer TEXT NOT NULL,
        department TEXT
    )
    """)

    # DEFAULT ADMIN
    cur.execute(
        "INSERT OR IGNORE INTO users VALUES(?,?)",
        ("admin", generate_password_hash("admin123"))
    )

    # DEFAULT COMPANY DATA
    default_data = [
        ("leave", "Employees get 12 casual leaves per year.", "HR"),
        ("working hours", "Working hours are 9 AM to 5 PM.", "HR"),
        ("hr", "Contact HR: hr@company.com", "HR"),
        ("it", "Contact IT: it@company.com", "IT")
    ]

    for q, a, d in default_data:
        cur.execute("INSERT OR IGNORE INTO knowledge VALUES(?,?,?)", (q, a, d))

    conn.commit()
    conn.close()


init_db()

# ---------------- INTENT DETECTION ----------------
def detect_department(message):
    message = message.lower()

    hr_keywords = ["leave", "salary", "policy", "holiday", "hr"]
    it_keywords = ["system", "password", "email", "network", "vpn", "it"]

    for w in hr_keywords:
        if w in message:
            return "HR"

    return next(("IT" for w in it_keywords if w in message), "General")


# ---------------- CHATBOT ----------------
def get_response(message):

    message = message.lower().strip()

    if "chat_history" not in session:
        session["chat_history"] = []

    conn = db()
    cur = conn.cursor()

    # 1️⃣ SEARCH LOCAL DATABASE FIRST
    cur.execute("SELECT answer FROM knowledge WHERE question LIKE ?", (f"%{message}%",))
    if result := cur.fetchone():
        reply = result[0]

        session["chat_history"].append({"role": "user", "content": message})
        session["chat_history"].append({"role": "assistant", "content": reply})

        conn.close()
        return reply

    # 2️⃣ AI RESPONSE
    try:
        return _extracted_from_get_response_26(message, cur, conn)
    except Exception as e:
        conn.close()
        print("AI ERROR:", e)
        return "AI service unavailable. Please contact HR."

    conn.close()


# TODO Rename this here and in `get_response`
def _extracted_from_get_response_26(message, cur, conn):
    department = detect_department(message)

    messages = [
        {
            "role": "system",
            "content": f"You are iColleague, a professional {department} support assistant. Reply briefly and clearly."
        }
    ]

    messages += session["chat_history"]
    messages.append({"role": "user", "content": message})

    response = openai.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=messages
    )



    # GET AI RESPONSE
    ai_reply = response.choices[0].message.content.strip() # type: ignore

    # SAVE TO MEMORY
    session["chat_history"].append({"role": "user", "content": message})
    session["chat_history"].append({"role": "assistant", "content": ai_reply})

    # SELF LEARNING SAVE
    if ai_reply:
        cur.execute(
            "INSERT OR IGNORE INTO knowledge VALUES(?,?,?)",
            (message, ai_reply, department)
        )
        conn.commit()

    conn.close()
    return ai_reply
    

# ---------------- ROUTES ----------------
@app.route("/")
def home():
    if "user" in session:
        return render_template("index.html")
    return redirect("/login")


@app.route("/chat", methods=["POST"])
def chat():
    if "user" not in session:
        return jsonify({"reply": "Unauthorized"}), 401

    message = request.json["message"]
    reply = get_response(message)
    return jsonify({"reply": reply})


@app.route("/clear")
def clear():
    session.pop("chat_history", None)
    return redirect("/")


# ---------------- LOGIN ----------------
@app.route("/login", methods=["GET", "POST"])
def login():

    if request.method == "GET":
        return render_template("login.html")

    username = request.form["username"]
    password = request.form["password"]

    conn = db()
    cur = conn.cursor()
    cur.execute("SELECT password FROM users WHERE username=?", (username,))
    user = cur.fetchone()
    conn.close()

    if not user or not check_password_hash(user[0], password):
        return "Invalid Login"

    session["user"] = username
    return redirect("/")


@app.route("/logout")
def logout():
    session.clear()
    return redirect("/login")


# ---------------- ADMIN PANEL ----------------
@app.route("/admin", methods=["GET", "POST"])
def admin():

    if "user" not in session or session["user"] != "admin":
        return redirect("/login")

    conn = db()
    cur = conn.cursor()

    if request.method == "POST":
        q = request.form["question"].lower().strip()
        a = request.form["answer"]
        dept = request.form["department"]

        cur.execute("INSERT OR REPLACE INTO knowledge VALUES(?,?,?)", (q, a, dept))
        conn.commit()

    cur.execute("SELECT * FROM knowledge ORDER BY department, question")
    data = cur.fetchall()
    conn.close()

    return render_template("admin.html", data=data)


# ---------------- RUN ----------------
if __name__ == "__main__":
    app.run(debug=True)

# ---------------- END ----------------