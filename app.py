
from flask import Flask, request, jsonify
import psycopg2
import os
from datetime import datetime

app = Flask(__name__)

# === DB Connection ===
conn = psycopg2.connect(
    dbname="course_db",
    user="postgres",
    password="yourpassword",
    host="localhost",
    port="5432"
)
cursor = conn.cursor()

UPLOAD_FOLDER = './uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# === Forum Routes ===
@app.route('/forums', methods=['POST'])
def create_forum():
    data = request.json
    course_id = data['course_id']
    title = data['forum_title']
    cursor.execute("INSERT INTO Forums (course_id, forum_title) VALUES (%s, %s) RETURNING forum_id", (course_id, title))
    forum_id = cursor.fetchone()[0]
    conn.commit()
    return jsonify({"forum_id": forum_id}), 201

@app.route('/forums/<int:course_id>', methods=['GET'])
def get_forums(course_id):
    cursor.execute("SELECT forum_id, forum_title FROM Forums WHERE course_id = %s", (course_id,))
    forums = cursor.fetchall()
    return jsonify([{"id": f[0], "title": f[1]} for f in forums])

@app.route('/threads', methods=['POST'])
def create_thread():
    data = request.json
    forum_id = data['forum_id']
    user_id = data['user_id']
    title = data['title']
    content = data['content']
    cursor.execute("""
        INSERT INTO DiscussionThreads (forum_id, user_id, title, content)
        VALUES (%s, %s, %s, %s) RETURNING thread_id
    """, (forum_id, user_id, title, content))
    thread_id = cursor.fetchone()[0]
    conn.commit()
    return jsonify({"thread_id": thread_id}), 201

@app.route('/threads/<int:forum_id>', methods=['GET'])
def get_threads(forum_id):
    cursor.execute("SELECT thread_id, title, content FROM DiscussionThreads WHERE forum_id = %s", (forum_id,))
    threads = cursor.fetchall()
    return jsonify([{"id": t[0], "title": t[1], "content": t[2]} for t in threads])

@app.route('/threads/<int:thread_id>/reply', methods=['POST'])
def reply_thread(thread_id):
    data = request.json
    parent_id = data.get('parent_reply_id')
    user_id = data['user_id']
    content = data['content']
    cursor.execute("""
        INSERT INTO Replies (thread_id, parent_reply_id, user_id, content)
        VALUES (%s, %s, %s, %s)
    """, (thread_id, parent_id, user_id, content))
    conn.commit()
    return jsonify({"message": "Reply posted."}), 201

# Recursive reply fetcher
@app.route('/threads/<int:thread_id>', methods=['GET'])
def get_thread_with_replies(thread_id):
    def fetch_replies(parent_id=None):
        if parent_id:
            cursor.execute("SELECT reply_id, content FROM Replies WHERE parent_reply_id = %s", (parent_id,))
        else:
            cursor.execute("SELECT reply_id, content FROM Replies WHERE parent_reply_id IS NULL AND thread_id = %s", (thread_id,))
        replies = cursor.fetchall()
        return [{"id": r[0], "content": r[1], "replies": fetch_replies(r[0])} for r in replies]

    cursor.execute("SELECT title, content FROM DiscussionThreads WHERE thread_id = %s", (thread_id,))
    thread = cursor.fetchone()
    return jsonify({"thread": {"title": thread[0], "content": thread[1]}, "replies": fetch_replies()})

# === Course Content Routes ===
@app.route('/content/section', methods=['POST'])
def create_section():
    data = request.json
    course_id = data['course_id']
    title = data['section_title']
    section_type = data.get('section_type', 'Lecture')
    cursor.execute("INSERT INTO Sections (course_id, section_title, section_type) VALUES (%s, %s, %s) RETURNING section_id", (course_id, title, section_type))
    section_id = cursor.fetchone()[0]
    conn.commit()
    return jsonify({"section_id": section_id}), 201

@app.route('/content', methods=['POST'])
def upload_content():
    section_id = request.form['section_id']
    name = request.form['name']
    content_type = request.form['type']

    if content_type == 'file':
        file = request.files['file']
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], file.filename)
        file.save(file_path)
        cursor.execute("""
            INSERT INTO SectionItems (section_id, type, name, link)
            VALUES (%s, %s, %s, %s)
        """, (section_id, content_type, name, file_path))
    elif content_type in ['link', 'slide']:
        link = request.form['link']
        cursor.execute("""
            INSERT INTO SectionItems (section_id, type, name, link)
            VALUES (%s, %s, %s, %s)
        """, (section_id, content_type, name, link))
    else:
        return jsonify({"error": "Invalid content type."}), 400

    conn.commit()
    return jsonify({"message": "Content uploaded."}), 201

@app.route('/content/<int:course_id>', methods=['GET'])
def get_course_content(course_id):
    cursor.execute("SELECT section_id, section_title FROM Sections WHERE course_id = %s", (course_id,))
    sections = cursor.fetchall()
    result = []
    for section in sections:
        section_id, title = section
        cursor.execute("""
            SELECT item_id, type, name, link FROM SectionItems
            WHERE section_id = %s
        """, (section_id,))
        content_items = cursor.fetchall()
        items = []
        for item in content_items:
            items.append({
                "id": item[0],
                "type": item[1],
                "name": item[2],
                "link": item[3]
            })
        result.append({"section": title, "items": items})
    return jsonify(result)

if __name__ == '__main__':
    app.run(debug=True)
