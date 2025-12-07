from flask import Flask, render_template, request, redirect, url_for, session 
import requests
import os
from datetime import datetime
import uuid
import json
from flask import session, jsonify


app = Flask(__name__)
app.secret_key = 'supersecretkey'  # Needed for session
app.config['SESSION_TYPE'] = 'filesystem'

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# API Key from .env
SERPAPI_KEY = os.getenv('KEY')

# Predefined topics
TOPICS = [
    "Python Basics",
    "Machine Learning",
    "Data Science",
    "Web Development",
    "Artificial Intelligence",
    "Deep Learning",
    "Flask Tutorial",
    "ReactJS Basics",
    "Natural Language Processing",
    "Data Structures"
]

# Allow only educational/learning words
ALLOWED_KEYWORDS = [
    "learn", "tutorial", "course", "lesson", "study", "education",
    "training", "guide", "basics", "introduction", "class", "explained"
]

EXCLUDE_KEYWORDS = [
    "trailer", "movie", "music", "song", "funny", "dance",
    "prank", "entertainment", "film", "video clip"
]

@app.route("/")
def home():
    return render_template("home.html")

@app.route("/bot")
def bot():
    # Initialize chats in session if not exists
    if "chats" not in session:
        session["chats"] = []
    return redirect(url_for('new_chat'))

@app.route("/bot/new")
def new_chat():
    chat_id = str(uuid.uuid4())
    chat = {
        'id': chat_id,
        'created_at': datetime.utcnow().strftime('%Y-%m-%d %H:%M'),
        'history': []
    }
    chats = session.get('chats', [])
    chats.append(chat)
    session['chats'] = chats
    session.modified = True  # Ensure session is saved
    return redirect(url_for('chat', chat_id=chat_id))

# Add this route to clear chat history
@app.route("/clear-chat-history", methods=["POST"])
def clear_chat_history():
    # Clear only the chat history, keep other session data if needed
    if 'chats' in session:
        del session['chats']
    session.modified = True
    return jsonify({"success": True})

@app.route("/bot/<chat_id>", methods=["GET", "POST"])
def chat(chat_id):
    chats = session.get('chats', [])

    # If no chats exist → create new one
    if not chats:
        return redirect(url_for('new_chat'))

    # Find active chat
    chat = next((c for c in chats if c['id'] == chat_id), None)
    if not chat:
        return redirect(url_for('new_chat'))

    if request.method == "POST":
        topic = request.form.get("topic")
        if topic:
            # Add user message
            chat['history'].append({"type": "user", "text": topic})

            params = {
                "engine": "youtube",
                "search_query": topic,
                "api_key": SERPAPI_KEY
            }
            response = requests.get("https://serpapi.com/search", params=params)

            videos = []
            if response.status_code == 200:
                data = response.json()
                results = data.get("video_results", [])[:15]
                for video in results:
                    title = video.get("title", "")
                    title_lower = title.lower()

                    # Strict filtering
                    if any(bad in title_lower for bad in EXCLUDE_KEYWORDS):
                        continue
                    if not any(ok in title_lower for ok in ALLOWED_KEYWORDS):
                        continue

                    video_link = video.get("link") or video.get("url")
                    video_id = None
                    if video_link:
                        if "v=" in video_link:
                            video_id = video_link.split("v=")[1].split("&")[0]
                        elif "youtu.be/" in video_link:
                            video_id = video_link.split("youtu.be/")[1].split("?")[0]
                        elif "/shorts/" in video_link:
                            video_id = video_link.split("/shorts/")[1].split("?")[0]

                    if video_id:
                        thumbnail = f"https://img.youtube.com/vi/{video_id}/hqdefault.jpg"
                    else:
                        thumbnail = "https://via.placeholder.com/320x180?text=No+Thumbnail"

                    videos.append({
                        "title": title,
                        "link": video_link,
                        "video_id": video_id,
                        "thumbnail": thumbnail
                    })

            if videos:
                chat['history'].append({"type": "bot", "text": f"Here are educational YouTube videos for '{topic}':"})
                chat['history'].append({"type": "videos", "videos": videos, "search_query": topic})
            else:
                chat['history'].append({"type": "bot", "text": f"Sorry, I couldn't find educational videos for '{topic}'. Try another subject!"})

            # Save chats back to session
            for i, c in enumerate(chats):
                if c['id'] == chat_id:
                    chats[i] = chat
            session['chats'] = chats
            session.modified = True  # Ensure session is saved

            return redirect(url_for('chat', chat_id=chat_id, scroll_to_results=True))

    # Check if we need to scroll to results
    scroll_to_results = request.args.get('scroll_to_results', False)
    
    return render_template("bot.html", topics=TOPICS, chat_history=chat['history'], 
                          active_chat_id=chat_id, all_chats=chats, scroll_to_results=scroll_to_results)

@app.route("/delete-chat/<chat_id>", methods=["POST"])
def delete_chat(chat_id):
    chats = session.get('chats', [])
    
    # Find and remove the chat
    chats = [chat for chat in chats if chat['id'] != chat_id]
    session['chats'] = chats
    session.modified = True
    
    return jsonify({"success": True})

if __name__ == "__main__":
    app.run(debug=True)