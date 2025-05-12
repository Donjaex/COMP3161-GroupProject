
from flask import Flask, request, jsonify
import psycopg2
import os


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
    try:
        data = request.json
        if not data or 'course_id' not in data or 'forum_title' not in data:
            return jsonify({"error": "Missing 'course_id' or 'forum_title' in the request."}), 400

        course_id = data['course_id']
        title = data['forum_title']

        # Check if course_id exists in the courses table
        cursor.execute("SELECT course_id FROM courses WHERE course_id = %s", (course_id,))
        if not cursor.fetchone():
            return jsonify({"error": "course_id does not exist in the courses table."}), 400

        cursor.execute("INSERT INTO Forums (course_id, forum_title) VALUES (%s, %s) RETURNING forum_id", (course_id, title))
        forum_id = cursor.fetchone()[0]
        conn.commit()  # Commit after successful query
        return jsonify({"forum_id": forum_id}), 201
    except Exception as e:
        conn.rollback()  # Rollback in case of error
        print("ERROR:", e)
        app.logger.error(f"Error occurred: {e}")
        return jsonify({"error": str(e)}), 500


@app.route('/forums/<int:course_id>', methods=['GET'])
def get_forums(course_id):
    cursor.execute("SELECT forum_id, forum_title FROM Forums WHERE course_id = %s", (course_id,))
    forums = cursor.fetchall()
    return jsonify([{"id": f[0], "title": f[1]} for f in forums])


@app.route('/threads', methods=['POST'])
def create_thread():
    try:
        data = request.json
        forum_id = data['forum_id']
        user_id = data['user_id']
        title = data['title']
        content = data['content']

        # Check if forum_id exists
        cursor.execute("SELECT forum_id FROM forums WHERE forum_id = %s", (forum_id,))
        if not cursor.fetchone():
            return jsonify({"error": "forum_id does not exist in the forums table."}), 400

        # Check if user_id exists
        cursor.execute("SELECT user_id FROM users WHERE user_id = %s", (user_id,))
        if not cursor.fetchone():
            return jsonify({"error": "user_id does not exist in the users table."}), 400

        # Attempt to insert thread
        cursor.execute("""
            INSERT INTO DiscussionThreads (forum_id, user_id, title, content)
            VALUES (%s, %s, %s, %s) RETURNING thread_id
        """, (forum_id, user_id, title, content))

        thread_id = cursor.fetchone()[0]
        conn.commit()  # Commit the transaction

        return jsonify({"thread_id": thread_id}), 201
    except Exception as e:
        conn.rollback()  # Rollback the transaction if any error occurs
        app.logger.error(f"Error occurred while creating thread: {e}")
        return jsonify({"error": "Internal Server Error"}), 500


@app.route('/threads/<int:forum_id>', methods=['GET'])
def get_threads(forum_id):
    cursor.execute("SELECT thread_id, title, content FROM DiscussionThreads WHERE forum_id = %s", (forum_id,))
    threads = cursor.fetchall()
    return jsonify([{"id": t[0], "title": t[1], "content": t[2]} for t in threads])

@app.route("/threads/<int:thread_id>/reply", methods=["POST"])
def reply_thread(thread_id):
    user_id = request.json.get('user_id')
    content = request.json.get('content')

    # Check if the thread exists
    cursor.execute("SELECT * FROM discussionthreads WHERE thread_id = %s", (thread_id,))
    thread = cursor.fetchone()

    if not thread:
        return jsonify({"error": "Thread not found"}), 404

    # Check if the user exists
    cursor.execute("SELECT * FROM users WHERE user_id = %s", (user_id,))
    user = cursor.fetchone()

    if not user:
        return jsonify({"error": "User not found"}), 404

    # Insert the reply into the replies table
    try:
        cursor.execute("""
            INSERT INTO replies (thread_id, user_id, content)
            VALUES (%s, %s, %s)
        """, (thread_id, user_id, content))

        # Use the existing `conn` object to commit the transaction
        conn.commit()
        return jsonify({"message": "Reply posted."}), 201
    except Exception as e:
        # Use `conn.rollback()` to roll back the transaction in case of error
        conn.rollback()
        return jsonify({"error": str(e)}), 500


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
    try:
        data = request.json
        course_id = data['course_id']
        title = data['section_title']
        section_type = data.get('section_type', 'Lecture')

        app.logger.info(f"Received request to create section: course_id={course_id}, title={title}")

        # Check if course_id exists
        cursor.execute("SELECT course_id FROM courses WHERE course_id = %s", (course_id,))
        if not cursor.fetchone():
            return jsonify({"error": "course_id does not exist in the courses table."}), 400

        app.logger.info("course_id exists, inserting into Sections table.")

        cursor.execute("""
            INSERT INTO Sections (course_id, section_title, section_type)
            VALUES (%s, %s, %s) RETURNING section_id
        """, (course_id, title, section_type))

        section_id = cursor.fetchone()[0]
        conn.commit()  # Commit the transaction

        app.logger.info(f"Section created with section_id={section_id}")

        return jsonify({"section_id": section_id}), 201
    except Exception as e:
        conn.rollback()  # Rollback the transaction in case of error
        app.logger.error(f"Error occurred while creating section: {e}")
        return jsonify({"error": "Internal Server Error"}), 500


@app.route('/content', methods=['POST'])
def upload_content():
    try:
        section_id = request.form['section_id']
        name = request.form['name']
        content_type = request.form['type']

        if content_type == 'file':
            if 'file' not in request.files:
                return jsonify({"error": "No file part"}), 400
            file = request.files['file']
            if file.filename == '':
                return jsonify({"error": "No selected file"}), 400
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

        conn.commit()  # Commit the transaction
        return jsonify({"message": "Content uploaded."}), 201

    except Exception as e:
        conn.rollback()  # Rollback in case of error
        app.logger.error(f"Error occurred while uploading content: {e}")
        return jsonify({"error": "Internal Server Error"}), 500


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
    app.run(debug=True, port=5001)
