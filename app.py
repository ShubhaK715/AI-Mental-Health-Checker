
import sqlite3
import os
import threading
import webbrowser
import re

from flask import Flask, render_template, request, jsonify, session, redirect
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = "mental_health_checker_secret"

DB = "mental_health.db"


# =====================================
# DATABASE
# =====================================

def connect():
    con = sqlite3.connect(DB)
    con.row_factory = sqlite3.Row
    return con


def create_database():
    con = connect()

    con.execute("""
        CREATE TABLE IF NOT EXISTS users(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE,
            password TEXT
        )
    """)

    con.execute("""
        CREATE TABLE IF NOT EXISTS chats(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            owner TEXT,
            title TEXT
        )
    """)

    con.execute("""
        CREATE TABLE IF NOT EXISTS messages(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            chat_id INTEGER,
            role TEXT,
            content TEXT
        )
    """)

    con.commit()
    con.close()


create_database()


# =====================================
# USER SESSION
# =====================================

def get_owner():
    if "user_id" in session:
        return "user_" + str(session["user_id"])

    if "guest_id" not in session:
        session["guest_id"] = os.urandom(16).hex()

    return "guest_" + session["guest_id"]


# =====================================
# RULE-BASED CHATBOT ALGORITHM
# =====================================

rules = [
    {
        "keywords": ["hello", "hi", "hey", "good morning", "good evening"],
        "response": "Hello! 🌸 Welcome to Aura. How are you feeling today? I'm here to listen and support you."
    },
    {
        "keywords": ["sad", "unhappy", "crying", "lonely", "upset"],
        "response": "I'm sorry you're feeling this way. 💜 Your feelings matter. Try talking to someone you trust or doing something comforting. Would you like to tell me what happened?"
    },
    {
        "keywords": ["stress", "stressed", "pressure", "overwhelmed"],
        "response": "It sounds like you are experiencing stress. Try these simple steps:\n\n1. Take a short break.\n2. Breathe slowly.\n3. Divide your tasks into smaller parts.\n4. Talk to someone you trust.\n\nWhat is causing you the most stress?"
    },
    {
        "keywords": ["anxiety", "anxious", "nervous", "worried", "worry"],
        "response": "Feeling anxious can be difficult. 💜 Try this grounding exercise:\n\n1. Notice 5 things you can see.\n2. Notice 4 things you can feel.\n3. Notice 3 things you can hear.\n\nTake your time. You don't have to solve everything immediately."
    },
    {
        "keywords": ["angry", "anger", "irritated", "frustrated"],
        "response": "It's okay to feel angry sometimes. Try stepping away from the situation, taking slow breaths and giving yourself time before responding."
    },
    {
        "keywords": ["happy", "great", "excited", "wonderful", "good"],
        "response": "That's wonderful! 😊 Enjoy this positive moment. You could share your happiness with someone or write down what made your day special."
    },
    {
        "keywords": ["tired", "exhausted", "fatigue", "sleepy"],
        "response": "It sounds like you may need some rest. Try taking a break, drinking water and maintaining a comfortable sleep routine."
    },
    {
        "keywords": ["sleep", "insomnia", "sleepless", "sleeping"],
        "response": "Good sleep supports mental wellness. Try keeping a regular bedtime, reducing screen time before bed and creating a calm sleeping environment."
    },
    {
        "keywords": ["exam", "exams", "study", "studies", "college"],
        "response": "Studies and exams can feel overwhelming. Try making a realistic timetable, studying in short sessions and taking regular breaks. Remember, your worth is not defined by your marks."
    },
    {
        "keywords": ["friend", "friendship", "relationship", "breakup"],
        "response": "Relationships can bring many emotions. Give yourself time, communicate honestly when possible and speak with someone you trust."
    },
    {
        "keywords": ["motivation", "motivated", "lazy", "procrastination"],
        "response": "Start with one small task. You don't need to complete everything today. Small consistent steps can help you build momentum. 🌱"
    },
    {
        "keywords": ["confidence", "confident", "self-esteem", "insecure"],
        "response": "Building confidence takes time. Try recognizing your strengths, celebrating small achievements and avoiding comparisons with others."
    },
    {
        "keywords": ["breathing", "relax", "relaxation", "calm"],
        "response": "Let's try a gentle breathing exercise. Breathe in slowly, then breathe out gently. Repeat at a comfortable pace for a minute. Stop if you feel uncomfortable."
    },
    {
        "keywords": ["water", "hydration", "exercise", "walking"],
        "response": "Taking care of your body can support your wellbeing. Try drinking enough water, getting some gentle movement and taking regular breaks."
    },
    {
        "keywords": ["thank you", "thanks"],
        "response": "You're very welcome! 💜 Remember to be kind to yourself. I'm here whenever you'd like to talk."
    },
    {
        "keywords": ["who are you", "your name", "what are you"],
        "response": "I'm Aura 🌸, a rule-based mental wellness chatbot. I can respond to common feelings, offer wellness suggestions and answer selected general questions."
    },
    {
        "keywords": ["help", "what can you do", "features"],
        "response": "I can help with:\n\n1. Stress management\n2. Sadness and loneliness\n3. Anxiety support\n4. Sleep suggestions\n5. Study pressure\n6. Motivation\n7. Mood checking\n8. General wellness tips\n\nChoose a topic or tell me how you're feeling."
    },
    {
        "keywords": ["mental health", "mental wellness"],
        "response": "Mental wellness includes caring for your emotions, thoughts and daily habits. Sleep, social support, healthy routines and asking for help when needed can all play a role."
    },
    {
        "keywords": ["python", "computer", "programming", "technology"],
        "response": "Programming is the process of writing instructions for computers. Python is a popular beginner-friendly programming language used in web development, automation and data science."
    }
]


# Emergency-related phrases receive priority over ordinary rules.
crisis_phrases = [
    "kill myself", "suicide", "end my life",
    "hurt myself", "harm myself", "self harm",
    "want to die"
]


def get_bot_response(message):
    text = message.lower().strip()

    # Priority safety rule
    if any(phrase in text for phrase in crisis_phrases):
        return (
            "I'm really sorry you're going through this. "
            "You deserve support, and you don't have to face this alone. "
            "If you may act on these thoughts or are in immediate danger, "
            "please contact local emergency services or go to the nearest emergency department. "
            "If possible, tell someone you trust and ask them to stay with you. "
            "You can also seek support from a qualified mental health professional."
        )

    # Keyword matching
    for rule in rules:
        if any(keyword in text for keyword in rule["keywords"]):
            return rule["response"]

    # Default response
    return (
        "Thank you for sharing that with me. 💜 "
        "I may not have a predefined response for that topic yet. "
        "Could you tell me a little more about how you're feeling? "
        "You can also ask me about stress, sadness, anxiety, sleep or studies."
    )


# =====================================
# LOGIN AND REGISTRATION
# =====================================

@app.route("/auth", methods=["POST"])
def auth():
    data = request.json
    username = data.get("username", "").strip()
    password = data.get("password", "")
    action = data.get("action")

    if not username or not password:
        return jsonify(error="Please enter username and password."), 400

    if len(username) > 40 or len(password) < 6:
        return jsonify(error="Username must be under 40 characters and password must have at least 6 characters."), 400

    con = connect()

    if action == "register":
        try:
            con.execute(
                "INSERT INTO users(username,password) VALUES(?,?)",
                (username, generate_password_hash(password))
            )
            con.commit()

            user = con.execute(
                "SELECT id FROM users WHERE username=?",
                (username,)
            ).fetchone()

        except sqlite3.IntegrityError:
            con.close()
            return jsonify(error="Username already exists."), 400

    else:
        user = con.execute(
            "SELECT * FROM users WHERE username=?",
            (username,)
        ).fetchone()

        if not user or not check_password_hash(user["password"], password):
            con.close()
            return jsonify(error="Incorrect username or password."), 401

    session.clear()
    session["user_id"] = user["id"]

    con.close()
    return jsonify(success=True)


@app.route("/guest")
def guest():
    session.clear()
    session["guest_id"] = os.urandom(16).hex()
    return redirect("/")


@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")


# =====================================
# CHAT HISTORY
# =====================================

@app.route("/api/chats")
def get_chats():
    con = connect()

    chats = con.execute(
        "SELECT * FROM chats WHERE owner=? ORDER BY id DESC",
        (get_owner(),)
    ).fetchall()

    con.close()
    return jsonify([dict(chat) for chat in chats])


@app.route("/api/new", methods=["POST"])
def new_chat():
    con = connect()

    cur = con.execute(
        "INSERT INTO chats(owner,title) VALUES(?,?)",
        (get_owner(), "New Conversation")
    )

    con.commit()
    chat_id = cur.lastrowid
    con.close()

    return jsonify(id=chat_id)


@app.route("/api/messages/<int:chat_id>")
def get_messages(chat_id):
    con = connect()

    chat = con.execute(
        "SELECT id FROM chats WHERE id=? AND owner=?",
        (chat_id, get_owner())
    ).fetchone()

    if not chat:
        con.close()
        return jsonify(error="Chat not found."), 404

    messages = con.execute(
        "SELECT role,content FROM messages WHERE chat_id=? ORDER BY id",
        (chat_id,)
    ).fetchall()

    con.close()
    return jsonify([dict(message) for message in messages])


@app.route("/api/delete/<int:chat_id>", methods=["DELETE"])
def delete_chat(chat_id):
    con = connect()

    chat = con.execute(
        "SELECT id FROM chats WHERE id=? AND owner=?",
        (chat_id, get_owner())
    ).fetchone()

    if not chat:
        con.close()
        return jsonify(error="Chat not found."), 404

    con.execute("DELETE FROM messages WHERE chat_id=?", (chat_id,))
    con.execute("DELETE FROM chats WHERE id=?", (chat_id,))

    con.commit()
    con.close()

    return jsonify(success=True)


# =====================================
# CHATBOT
# =====================================

@app.route("/api/chat", methods=["POST"])
def chat():
    data = request.json
    message = data.get("message", "").strip()
    chat_id = data.get("chat_id")

    if not message or len(message) > 3000:
        return jsonify(error="Enter a message under 3000 characters."), 400

    con = connect()

    chat = con.execute(
        "SELECT * FROM chats WHERE id=? AND owner=?",
        (chat_id, get_owner())
    ).fetchone()

    if not chat:
        con.close()
        return jsonify(error="Please start a new chat."), 404

    reply = get_bot_response(message)

    con.execute(
        "INSERT INTO messages(chat_id,role,content) VALUES(?,?,?)",
        (chat_id, "user", message)
    )

    con.execute(
        "INSERT INTO messages(chat_id,role,content) VALUES(?,?,?)",
        (chat_id, "assistant", reply)
    )

    if chat["title"] == "New Conversation":
        con.execute(
            "UPDATE chats SET title=? WHERE id=?",
            (message[:35], chat_id)
        )

    con.commit()
    con.close()

    return jsonify(reply=reply)


# =====================================
# MOOD CHECKER
# =====================================

@app.route("/api/mood", methods=["POST"])
def mood_checker():
    mood = request.json.get("mood", "").lower()

    suggestions = {
        "happy": "Wonderful! Keep enjoying positive moments and share your happiness with others.",
        "sad": "Be gentle with yourself. Talk to someone you trust or try a comforting activity.",
        "stressed": "Take a short break, breathe slowly and divide your tasks into smaller steps.",
        "anxious": "Try a grounding exercise. Notice five things you can see and four things you can feel.",
        "angry": "Pause for a moment, take slow breaths and give yourself some space.",
        "tired": "Consider resting, drinking water and maintaining a comfortable sleep routine.",
        "neutral": "Try a small enjoyable activity and check in with yourself later."
    }

    return jsonify(
        mood=mood,
        suggestion=suggestions.get(
            mood, "Take a moment to notice how you feel and choose one small helpful activity."
        )
    )
@app.route("/api/session")
def check_session():
    logged_in = (
        "user_id" in session or
        "guest_id" in session
    )

    return jsonify(logged_in=logged_in)


# =====================================
# HOME PAGE
# =====================================

@app.route("/")
def home():
    return render_template("index.html")


# =====================================
# RUN PROJECT
# =====================================

if __name__ == "__main__":

    threading.Timer(
        1.5,
        lambda: webbrowser.open("http://127.0.0.1:5000")
    ).start()

    app.run(host="127.0.0.1", port=5000, debug=False)
