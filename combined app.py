import os
import psycopg2
from flask import Flask, request, jsonify

app = Flask(__name__)


from flask_cors import CORS

app = Flask(__name__)
CORS(app)  # Enable CORS for all routes

# === Database Configuration ===
DATABASE_URL = os.environ.get("DATABASE_URL", "dbname=course_db user=postgres password=yourpassword host=localhost port=5432")

# === File Upload Configuration ===
UPLOAD_FOLDER = './uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

def get_cursor():
    """Create a new database connection and return cursor and connection."""
    conn = psycopg2.connect(DATABASE_URL)
    return conn.cursor(), conn

# === Helper Functions ===
def handle_error(e, conn=None):
    """Centralized error handling function."""
    if conn:
        conn.rollback()
    app.logger.error(f"Error occurred: {e}")
    return jsonify({"error": str(e)}), 500

# -------------------- AUTH --------------------

@app.route('/auth/register', methods=['POST'])
def register():
    try:
        data = request.get_json()
        required_fields = ['user_id', 'name', 'account_type', 'email', 'password']
        if not all(field in data for field in required_fields):
            return jsonify({'error': 'Missing fields in request'}), 400

        cur, conn = get_cursor()
        cur.execute("""
            INSERT INTO Users (user_id, name, account_type, email, password)
            VALUES (%s, %s, %s, %s, %s)
        """, (data['user_id'], data['name'], data['account_type'], data['email'], data['password']))
        conn.commit()
        conn.close()
        return jsonify({'message': 'User registered successfully'})
    except Exception as e:
        return handle_error(e)

@app.route('/auth/login', methods=['POST'])
def login():
    try:
        data = request.get_json()
        if 'email' not in data or 'password' not in data:
            return jsonify({'error': 'Email and password required'}), 400

        cur, conn = get_cursor()
        cur.execute("SELECT * FROM Users WHERE email=%s AND password=%s", (data['email'], data['password']))
        columns = [desc[0] for desc in cur.description]
        user = dict(zip(columns, cur.fetchone())) if cur.rowcount > 0 else None
        conn.close()
        if user:
            return jsonify(user)
        return jsonify({'error': 'Invalid credentials'}), 401
    except Exception as e:
        return handle_error(e)

# === Students Routes ===
@app.route('/students', methods=['GET'])
def list_students():
    try:
        cur, conn = get_cursor()
        cur.execute("SELECT user_id, name, email FROM Users WHERE account_type = 'Student'")
        rows = cur.fetchall()
        conn.close()
        return jsonify([{'student_id': u, 'name': n, 'email': e} for u, n, e in rows])
    except Exception as e:
        return handle_error(e)

@app.route('/students/<int:student_id>/courses', methods=['GET'])
def get_student_courses(student_id):
    try:
        cur, conn = get_cursor()
        
        # Get column names to identify the title column
        cur.execute("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_schema = 'public' 
            AND table_name = 'courses'
        """)
        columns = [col[0] for col in cur.fetchall()]
        
        # Look for possible title columns
        title_column = None
        possible_names = ['name', 'course_name', 'course_title', 'title', 'description']
        for col in possible_names:
            if col in columns:
                title_column = col
                break
        
        if not title_column:
            return jsonify({"error": "Could not find title column in courses table"}), 500
        
        # Use the identified column name in the query
        query = f"""
            SELECT c.course_id, c.{title_column}
            FROM Courses c
            JOIN Enrollments e ON c.course_id = e.course_id
            WHERE e.user_id = %s
        """
        
        cur.execute(query, (student_id,))
        rows = cur.fetchall()
        conn.close()
        return jsonify([{'course_id': row[0], 'title': row[1]} for row in rows])
    except Exception as e:
        return handle_error(e)

@app.route('/students/<int:student_id>/average', methods=['GET'])
def get_student_average(student_id):
    try:
        cur, conn = get_cursor()
        cur.execute("""
            SELECT AVG(s.grade)::numeric(5,2)
            FROM Submissions s
            WHERE s.user_id = %s
            AND s.grade IS NOT NULL
        """, (student_id,))
        avg, = cur.fetchone() or (None,)
        conn.close()
        return jsonify({'student_id': student_id, 'average': float(avg) if avg is not None else None})
    except Exception as e:
        return handle_error(e)

# -------------------- COURSES --------------------

@app.route('/courses/create', methods=['POST'])
def create_course():
    try:
        data = request.get_json()
        if data.get('account_type') != 'admin':
            return jsonify({'error': 'Only admins can create courses'}), 403

        # Get the table structure to identify the correct column names
        cur, conn = get_cursor()
        cur.execute("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_schema = 'public' 
            AND table_name = 'courses'
        """)
        columns = [col[0] for col in cur.fetchall()]
        
        # Map the expected fields to actual database columns
        field_mappings = {
            'course_id': 'course_id',
            'title': next((col for col in ['title', 'course_name', 'name'] if col in columns), None),
            'description': 'description',
            'lecturer_id': 'lecturer_id'
        }
        
        
        if None in field_mappings.values():
            missing_fields = [k for k, v in field_mappings.items() if v is None]
            return jsonify({'error': f'Database schema missing required fields: {missing_fields}'}), 500
            
        
        required_fields = ['course_id', 'title', 'description', 'lecturer_id']
        if not all(field in data for field in required_fields):
            return jsonify({'error': 'Missing course information'}), 400
            
        
        query = f"""
            INSERT INTO Courses (course_id, {field_mappings['title']}, description, lecturer_id)
            VALUES (%s, %s, %s, %s)
        """
        
        
        cur.execute(query, (data['course_id'], data['title'], data['description'], data['lecturer_id']))
        conn.commit()
        conn.close()
        return jsonify({'message': 'Course created'})
    except Exception as e:
        return handle_error(e)

@app.route('/courses/all', methods=['GET'])
def get_all_courses():
    try:
        cur, conn = get_cursor()
        cur.execute("SELECT * FROM Courses")
        columns = [desc[0] for desc in cur.description]
        courses = [dict(zip(columns, row)) for row in cur.fetchall()]
        conn.close()
        return jsonify(courses)
    except Exception as e:
        return handle_error(e)

# === Lecturers Routes ===
@app.route('/lecturers/<int:lecturer_id>/courses', methods=['GET'])
def get_lecturer_courses(lecturer_id):
    try:
        cur, conn = get_cursor()
        
        # First, get the column names to identify the title column
        cur.execute("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_schema = 'public' 
            AND table_name = 'courses'
        """)
        columns = [col[0] for col in cur.fetchall()]
        
        
        title_column = None
        possible_names = ['name', 'course_name', 'course_title', 'title', 'description']
        for col in possible_names:
            if col in columns:
                title_column = col
                break
        
        if not title_column:
            return jsonify({"error": "Could not find title column in courses table"}), 500
        
        
        query = f"""
            SELECT course_id, {title_column}
            FROM courses
            WHERE lecturer_id = %s
        """
        
        cur.execute(query, (lecturer_id,))
        rows = cur.fetchall()
        conn.close()
        
        return jsonify([{'course_id': row[0], 'title': row[1]} for row in rows])
    except Exception as e:
        return handle_error(e)

# === Registration & Submissions Routes ===
@app.route('/courses/<int:course_id>/register', methods=['POST'])
def register_course(course_id):
    try:
        data = request.get_json()
        student_id = data.get('student_id')
        if not student_id:
            return jsonify({'error': 'Missing `student_id`'}), 400

        cur, conn = get_cursor()
        cur.execute("""
            INSERT INTO Enrollments (user_id, course_id)
            VALUES (%s, %s)
            ON CONFLICT DO NOTHING
        """, (student_id, course_id))
        conn.commit()
        conn.close()
        return jsonify({'status': 'registered', 'student_id': student_id, 'course_id': course_id})
    except Exception as e:
        return handle_error(e)

@app.route('/courses/<int:course_id>/assignments/<int:assignment_id>/submit', methods=['POST'])
def submit_assignment(course_id, assignment_id):
    try:
        data = request.get_json()
        student_id = data.get('student_id')
        content = data.get('content')
        submitted_at = data.get('submitted_at')
        if not all([student_id, content, submitted_at]):
            return jsonify({'error': 'Missing fields'}), 400

        cur, conn = get_cursor()
        cur.execute("""
            INSERT INTO Submissions (assignment_id, user_id, file_link, submitted_at)
            VALUES (%s, %s, %s, %s)
        """, (assignment_id, student_id, content, submitted_at))
        conn.commit()
        conn.close()
        return jsonify({
            'status': 'success',
            'assignment_id': assignment_id,
            'user_id': student_id
        })
    except Exception as e:
        return handle_error(e)

@app.route('/submissions/<int:assignment_id>/<int:user_id>/grade', methods=['PUT'])
def grade_submission(assignment_id, user_id):
    try:
        data = request.get_json()
        grade = data.get('grade')
        if grade is None:
            return jsonify({'error': 'Missing `grade`'}), 400

        cur, conn = get_cursor()
        cur.execute("""
            UPDATE Submissions
            SET grade = %s
            WHERE assignment_id = %s AND user_id = %s
            RETURNING assignment_id, user_id, grade
        """, (grade, assignment_id, user_id))
        row = cur.fetchone()
        conn.commit()
        conn.close()
        if not row:
            return jsonify({'error': 'Submission not found'}), 404

        return jsonify({
            'assignment_id': row[0],
            'user_id': row[1],
            'grade': float(row[2])
        })
    except Exception as e:
        return handle_error(e)

# === Reporting Routes ===
def make_report(view_name, columns):
    try:
        cur, conn = get_cursor()
        cur.execute(f"SELECT * FROM {view_name}")
        rows = cur.fetchall()
        conn.close()
        return jsonify([dict(zip(columns, r)) for r in rows])
    except Exception as e:
        return handle_error(e)

@app.route('/reports/courses_50_plus', methods=['GET'])
def report_courses_50_plus():
    
    try:
        cur, conn = get_cursor()
        cur.execute("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_schema = 'public' 
            AND table_name = 'courses'
        """)
        columns = [col[0] for col in cur.fetchall()]
        
        
        title_column = 'title'  # Default
        possible_names = ['name', 'course_name', 'course_title', 'title', 'description']
        for col in possible_names:
            if col in columns:
                title_column = col
                break
                
        conn.close()
        return make_report('courses_50_plus', ['course_id', title_column, 'student_count'])
    except Exception as e:
        return handle_error(e)

@app.route('/reports/students_5_plus', methods=['GET'])
def report_students_5_plus():
    return make_report('students_5_plus', ['student_id', 'student_name', 'course_count'])

@app.route('/reports/lecturers_3_plus', methods=['GET'])
def report_lecturers_3_plus():
    return make_report('lecturers_3_plus', ['lecturer_id', 'lecturer_name', 'course_count'])

@app.route('/reports/top_10_enrolled', methods=['GET'])
def report_top_10_enrolled():
    # Get column names to identify the title column
    try:
        cur, conn = get_cursor()
        cur.execute("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_schema = 'public' 
            AND table_name = 'courses'
        """)
        columns = [col[0] for col in cur.fetchall()]
        
        # Look for possible title columns
        title_column = 'title'  # Default
        possible_names = ['name', 'course_name', 'course_title', 'title', 'description']
        for col in possible_names:
            if col in columns:
                title_column = col
                break
                
        conn.close()
        return make_report('top_10_enrolled', ['course_id', title_column, 'student_count'])
    except Exception as e:
        return handle_error(e)

@app.route('/reports/top_10_students', methods=['GET'])
def report_top_10_students():
    return make_report('top_10_students', ['student_id', 'student_name', 'average_grade'])

@app.route('/courses/most-enrolled', methods=['GET'])
def most_enrolled_courses():
    try:
       
        cur, conn = get_cursor()
        
        
        cur.execute("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_schema = 'public' 
            AND table_name = 'courses'
        """)
        columns = [col[0] for col in cur.fetchall()]
        
        # Look for possible title columns
        title_column = None
        possible_names = ['name', 'course_name', 'course_title', 'title', 'description']
        for col in possible_names:
            if col in columns:
                title_column = col
                break
        
        if not title_column:
            return jsonify({"error": "Could not find title column in courses table"}), 500
        
        # Execute the SQL to get the most enrolled courses with dynamic column name
        query = f"""
            SELECT c.course_id, c.{title_column}, COUNT(e.user_id) AS student_count
            FROM Courses c
            JOIN Enrollments e ON c.course_id = e.course_id
            GROUP BY c.course_id, c.{title_column}
            ORDER BY student_count DESC
            LIMIT 10
        """
        
        cur.execute(query)
        courses = cur.fetchall()
        
        # Format the results
        formatted_courses = []
        for course in courses:
            formatted_courses.append({
                'course_id': course[0],
                'title': course[1],
                'student_count': course[2]
            })
            
        conn.close()
        
        return jsonify(formatted_courses)
    except Exception as e:
        return handle_error(e)

@app.route('/students/top-10-averages', methods=['GET'])
def get_top_10_students_by_average():
    try:
        cur, conn = get_cursor()

        if cur is None or conn is None:
            return jsonify({"error": "Database connection failed."}), 500

        # Modified query to only include students with non-null grades
        # and to format the average properly
        cur.execute("""
            SELECT u.user_id, u.name, ROUND(AVG(s.grade)::numeric, 2) AS average_grade
            FROM Users u
            JOIN Submissions s ON u.user_id = s.user_id
            WHERE u.account_type = 'Student' AND s.grade IS NOT NULL
            GROUP BY u.user_id, u.name
            HAVING AVG(s.grade) IS NOT NULL
            ORDER BY average_grade DESC
            LIMIT 10;
        """)

        # Fetch the results
        rows = cur.fetchall()
        
        # Format the results
        students = []
        for row in rows:
            students.append({
                "student_id": row[0],
                "name": row[1],
                "average_grade": float(row[2]) if row[2] is not None else None
            })
        
        conn.close()

        
        if not students:
            return jsonify({"message": "No students with grades found."}), 200

        return jsonify(students), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500
        return jsonify(students), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# === Forum Routes ===
@app.route('/forums', methods=['POST'])
def create_forum():
    try:
        data = request.json
        if not data or 'course_id' not in data or 'forum_title' not in data:
            return jsonify({"error": "Missing 'course_id' or 'forum_title' in the request."}), 400

        course_id = data['course_id']
        title = data['forum_title']

        cur, conn = get_cursor()
        
        # First check if the course exists (using a more flexible approach)
        cur.execute("""
            SELECT EXISTS (
                SELECT 1 FROM information_schema.tables 
                WHERE table_schema = 'public' AND table_name = 'courses'
            )
        """)
        
        if cur.fetchone()[0]:
            table_name = 'courses'
        else:
            table_name = 'Courses'
            
        # Check if course exists
        cur.execute(f'SELECT course_id FROM "{table_name}" WHERE course_id = %s', (course_id,))
        if not cur.fetchone():
            conn.close()
            return jsonify({"error": f"Course with ID {course_id} not found."}), 404

        # Get the next available forum_id
        cur.execute("SELECT MAX(forum_id) + 1 FROM Forums")
        next_id = cur.fetchone()[0] or 1
        
        # Insert with explicit ID to avoid sequence issues
        cur.execute("""
            INSERT INTO Forums (forum_id, course_id, forum_title)
            VALUES (%s, %s, %s)
            RETURNING forum_id
        """, (next_id, course_id, title))
        
        forum_id = cur.fetchone()[0]
        conn.commit()
        conn.close()
        
        return jsonify({
            "message": "Forum created successfully",
            "forum_id": forum_id
        }), 201
        
    except Exception as e:
        return handle_error(e)
    
@app.route('/forum/<int:forum_id>', methods=['GET'])
def get_forum_by_id(forum_id):
    try:
        cur, conn = get_cursor()
        
        # Get the basic forum information
        cur.execute("""
            SELECT * FROM Forums WHERE forum_id = %s
        """, (forum_id,))
        
        if cur.rowcount == 0:
            conn.close()
            return jsonify({"error": f"Forum with ID {forum_id} not found"}), 404
            
        columns = [desc[0] for desc in cur.description]
        forum_row = cur.fetchone()
        
        # Convert to dictionary
        forum = dict(zip(columns, forum_row))
        
        conn.close()
        return jsonify(forum)
        
    except Exception as e:
        app.logger.error(f"Error getting forum: {str(e)}")
        return handle_error(e)    
    

    

@app.route('/threads', methods=['POST'])
def create_thread():
    try:
        data = request.json
        forum_id = data['forum_id']
        user_id = data['user_id']
        title = data['title']
        content = data['content']

        
        cur, conn = get_cursor()

        
        cur.execute("SELECT forum_id FROM forums WHERE forum_id = %s", (forum_id,))
        if not cur.fetchone():
            conn.close()
            return jsonify({"error": "forum_id does not exist in the forums table."}), 400

        
        cur.execute("SELECT user_id FROM users WHERE user_id = %s", (user_id,))
        if not cur.fetchone():
            conn.close()
            return jsonify({"error": "user_id does not exist in the users table."}), 400

        
        cur.execute("""
            INSERT INTO DiscussionThreads (forum_id, user_id, title, content)
            VALUES (%s, %s, %s, %s) RETURNING thread_id, forum_id, user_id, title, content, created_at
        """, (forum_id, user_id, title, content))

        # Fetch the created thread details
        thread = cur.fetchone()
        thread_id, forum_id, user_id, title, content, created_at = thread

        
        conn.commit()
        conn.close()

        
        return jsonify({
            "thread_id": thread_id,
            "forum_id": forum_id,
            "user_id": user_id,
            "title": title,
            "content": content,
            "created_at": created_at.isoformat()  
        }), 201

    except Exception as e:
        return handle_error(e)
    


    
    
@app.route('/courses/<int:course_id>/members', methods=['GET'])
def get_course_members(course_id):
    try:
        cur, conn = get_cursor()
        
        # First, check if the course exists
        cur.execute("SELECT course_id FROM Courses WHERE course_id = %s", (course_id,))
        if not cur.fetchone():
            conn.close()
            return jsonify({"error": f"Course with ID {course_id} not found"}), 404
        
        # Get the lecturer for this course
        cur.execute("""
            SELECT u.user_id, u.name, u.email, 'Lecturer' as role
            FROM Courses c
            JOIN Users u ON c.lecturer_id = u.user_id
            WHERE c.course_id = %s
        """, (course_id,))
        lecturer = cur.fetchone()
        
        
        cur.execute("""
            SELECT u.user_id, u.name, u.email, 'Student' as role
            FROM Users u
            JOIN Enrollments e ON u.user_id = e.user_id
            WHERE e.course_id = %s
            AND u.account_type = 'Student'
        """, (course_id,))
        students = cur.fetchall()
        
        # Combine the results
        members = []
        if lecturer:
            members.append({
                "user_id": lecturer[0],
                "name": lecturer[1],
                "email": lecturer[2],
                "role": lecturer[3]
            })
        
        for student in students:
            members.append({
                "user_id": student[0],
                "name": student[1],
                "email": student[2],
                "role": student[3]
            })
        
        conn.close()
        return jsonify({
            "course_id": course_id,
            "member_count": len(members),
            "members": members
        })
    except Exception as e:
        return handle_error(e)    

@app.route('/threads/<int:forum_id>', methods=['GET'])
def get_threads(forum_id):
    try:
        cur, conn = get_cursor()
        cur.execute("SELECT thread_id, title, content FROM DiscussionThreads WHERE forum_id = %s", (forum_id,))
        threads = cur.fetchall()
        conn.close()
        return jsonify([{"id": t[0], "title": t[1], "content": t[2]} for t in threads])
    except Exception as e:
        return handle_error(e)

@app.route('/threads/<int:thread_id>', methods=['GET'])
def get_thread_with_replies(thread_id):
    try:
        cur, conn = get_cursor()
        
        def fetch_replies(parent_id=None):
            if parent_id:
                cur.execute("SELECT reply_id, content FROM Replies WHERE parent_reply_id = %s", (parent_id,))
            else:
                cur.execute("SELECT reply_id, content FROM Replies WHERE parent_reply_id IS NULL AND thread_id = %s", (thread_id,))
            replies = cur.fetchall()
            return [{"id": r[0], "content": r[1], "replies": fetch_replies(r[0])} for r in replies]

        cur.execute("SELECT title, content FROM DiscussionThreads WHERE thread_id = %s", (thread_id,))
        thread = cur.fetchone()
        
        if not thread:
            conn.close()
            return jsonify({"error": "Thread not found"}), 404
            
        result = jsonify({"thread": {"title": thread[0], "content": thread[1]}, "replies": fetch_replies()})
        conn.close()
        return result
    except Exception as e:
        return handle_error(e)

@app.route('/replies', methods=['POST'])
def create_reply():
    try:
        data = request.json
        thread_id = data['thread_id']
        user_id = data['user_id']
        content = data['content']
        parent_reply_id = data.get('parent_reply_id')  # Optional (if this is a reply to an existing reply)
        created_at = data.get('created_at')  # Timestamp for the reply (optional)

        # Connect to the database
        cur, conn = get_cursor()

        # Check if the thread exists
        cur.execute("SELECT thread_id FROM discussionthreads WHERE thread_id = %s", (thread_id,))
        if not cur.fetchone():
            conn.close()
            return jsonify({"error": "thread_id does not exist in the DiscussionThreads table."}), 400

        # Check if user exists
        cur.execute("SELECT user_id FROM users WHERE user_id = %s", (user_id,))
        if not cur.fetchone():
            conn.close()
            return jsonify({"error": "user_id does not exist in the users table."}), 400

        
        cur.execute("""
            INSERT INTO Replies (thread_id, user_id, content, parent_reply_id, timestamp)
            VALUES (%s, %s, %s, %s, %s) RETURNING reply_id, thread_id, user_id, content, parent_reply_id, timestamp
        """, (thread_id, user_id, content, parent_reply_id, created_at))

     # Fetch the reply details
        reply = cur.fetchone()
        reply_id, thread_id, user_id, content, parent_reply_id, timestamp = reply

        
        conn.commit()
        conn.close()

        # Return the created reply details
        return jsonify({
            "reply_id": reply_id,
            "thread_id": thread_id,
            "user_id": user_id,
            "content": content,
            "parent_reply_id": parent_reply_id,
            "timestamp": timestamp.isoformat()  # Format timestamp to ISO 8601
        }), 201

    except Exception as e:
        return handle_error(e)

# === Course Content Routes ===
@app.route('/content/section', methods=['POST'])
def create_section():
    try:
        data = request.json
        course_id = data['course_id']
        title = data['section_title']
        section_type = data.get('section_type', 'Lecture')

        app.logger.info(f"Received request to create section: course_id={course_id}, title={title}")

        cur, conn = get_cursor()
        # Check if course_id exists
        cur.execute("SELECT course_id FROM courses WHERE course_id = %s", (course_id,))
        if not cur.fetchone():
            conn.close()
            return jsonify({"error": "course_id does not exist in the courses table."}), 400

        app.logger.info("course_id exists, inserting into Sections table.")

        cur.execute("""
            INSERT INTO Sections (course_id, section_title, section_type)
            VALUES (%s, %s, %s) RETURNING section_id
        """, (course_id, title, section_type))

        section_id = cur.fetchone()[0]
        conn.commit()
        conn.close()

        app.logger.info(f"Section created with section_id={section_id}")

        return jsonify({"section_id": section_id}), 201
    except Exception as e:
        return handle_error(e)

@app.route('/content', methods=['POST'])
def upload_content():
    try:
        section_id = request.form['section_id']
        name = request.form['name']
        content_type = request.form['type']

        cur, conn = get_cursor()
        
        if content_type == 'file':
            if 'file' not in request.files:
                conn.close()
                return jsonify({"error": "No file part"}), 400
                
            file = request.files['file']
            if file.filename == '':
                conn.close()
                return jsonify({"error": "No selected file"}), 400
                
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], file.filename)
            file.save(file_path)

            cur.execute("""
                INSERT INTO SectionItems (section_id, type, name, link)
                VALUES (%s, %s, %s, %s)
            """, (section_id, content_type, name, file_path))

        elif content_type in ['link', 'slide']:
            link = request.form['link']
            cur.execute("""
                INSERT INTO SectionItems (section_id, type, name, link)
                VALUES (%s, %s, %s, %s)
            """, (section_id, content_type, name, link))

        else:
            conn.close()
            return jsonify({"error": "Invalid content type."}), 400

        conn.commit()
        conn.close()
        return jsonify({"message": "Content uploaded."}), 201

    except Exception as e:
        return handle_error(e, conn if 'conn' in locals() else None)

@app.route('/content/<int:course_id>', methods=['GET'])
def get_course_content(course_id):
    try:
        cur, conn = get_cursor()
        cur.execute("SELECT section_id, section_title FROM Sections WHERE course_id = %s", (course_id,))
        sections = cur.fetchall()
        result = []
        for section in sections:
            section_id, title = section
            cur.execute("""
                SELECT item_id, type, name, link FROM SectionItems
                WHERE section_id = %s
            """, (section_id,))
            content_items = cur.fetchall()
            items = []
            for item in content_items:
                items.append({
                    "id": item[0],
                    "type": item[1],
                    "name": item[2],
                    "link": item[3]
                })
            result.append({"section": title, "items": items})
        conn.close()
        return jsonify(result)
    except Exception as e:
        return handle_error(e)

# -------------------- CALENDAR EVENTS --------------------

@app.route('/calendar-events', methods=['POST'])
def create_calendar_event():
    try:
        data = request.get_json()

        # Validate required fields
        required_fields = ['course_id', 'event_title', 'event_date']
        if not all(field in data for field in required_fields):
            return jsonify({'error': 'Missing required fields'}), 400
        
        cur, conn = get_cursor()
        cur.execute("""
            INSERT INTO CalendarEvents (course_id, event_title, event_date)
            VALUES (%s, %s, %s) RETURNING event_id
        """, (data['course_id'], data['event_title'], data['event_date']))
        
        event_id = cur.fetchone()[0]
        conn.commit()
        conn.close()
        
        return jsonify({'message': 'Calendar event created successfully', 'event_id': event_id}), 201
    except Exception as e:
        return handle_error(e)
    
@app.route('/debug/student-enrollment/<int:student_id>/<int:course_id>', methods=['GET'])
def check_student_enrollment(student_id, course_id):
    try:
        cur, conn = get_cursor()
        cur.execute("""
            SELECT * FROM Enrollments 
            WHERE user_id = %s AND course_id = %s
        """, (student_id, course_id))
        
        enrollment = cur.fetchone()
        is_enrolled = enrollment is not None
        
        conn.close()
        return jsonify({
            "student_id": student_id,
            "course_id": course_id,
            "is_enrolled": is_enrolled
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    
@app.route('/test/student-events/<int:user_id>/<date>', methods=['GET'])
def test_student_events(user_id, date):
    try:
        cur, conn = get_cursor()
        
        # First, get courses the student is enrolled in
        cur.execute("SELECT course_id FROM Enrollments WHERE user_id = %s", (user_id,))
        courses = [row[0] for row in cur.fetchall()]
        
        # If no courses, return empty
        if not courses:
            return jsonify({
                "message": "Student not enrolled in any courses",
                "student_id": user_id,
                "courses": []
            })
        
        
        placeholders = ','.join(['%s'] * len(courses))
        cur.execute(f"""
            SELECT * FROM CalendarEvents 
            WHERE course_id IN ({placeholders})
        """, courses)
        
        all_events = []
        columns = [desc[0] for desc in cur.description]
        for row in cur.fetchall():
            event = dict(zip(columns, row))
            
            if 'event_date' in event and event['event_date']:
                event['event_date'] = str(event['event_date'])
            all_events.append(event)
        
        
        filtered_events = []
        for event in all_events:
            # Print event date for debugging
            print(f"Event date: {event.get('event_date')}, Target date: {date}")
            # Simple string comparison for debugging
            if date in str(event.get('event_date', '')):
                filtered_events.append(event)
        
        conn.close()
        return jsonify({
            "student_id": user_id,
            "date": date,
            "courses": courses,
            "all_events": all_events,
            "filtered_events": filtered_events
        })
        
    except Exception as e:
        print(f"Error: {str(e)}")
        return jsonify({"error": str(e)}), 500
    

@app.route('/calendar/course/<int:course_id>', methods=['GET'])
def get_course_events(course_id):
    try:
        cur, conn = get_cursor()
        cur.execute("SELECT * FROM CalendarEvents WHERE course_id = %s", (course_id,))
        columns = [desc[0] for desc in cur.description]
        events = [dict(zip(columns, row)) for row in cur.fetchall()]
        conn.close()
        return jsonify(events)
    except Exception as e:
        return handle_error(e)

@app.route('/calendar/student/<int:user_id>/date/<date>', methods=['GET'])
def get_student_events(user_id, date):
    try:
        cur, conn = get_cursor()
        cur.execute("""
            SELECT ce.* FROM CalendarEvents ce
            JOIN Enrollments e ON ce.course_id = e.course_id
            WHERE e.user_id = %s AND ce.event_date = %s
        """, (user_id, date))
        columns = [desc[0] for desc in cur.description]
        events = [dict(zip(columns, row)) for row in cur.fetchall()]
        conn.close()
        return jsonify(events)
    except Exception as e:
        return handle_error(e)

if __name__ == '__main__':
    app.run(debug=True, port=5001)
