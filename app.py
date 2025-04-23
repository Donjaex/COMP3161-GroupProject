import os
import psycopg2
from flask import Flask, request, jsonify

app = Flask(__name__)

DATABASE_URL = os.environ.get("DATABASE_URL", "dbname=course_db user=ravaughnmarsh")

def get_cursor():
    conn = psycopg2.connect(DATABASE_URL)
    return conn.cursor(), conn

# --- Students --------------------------------------------------------------

@app.route('/students', methods=['GET'])
def list_students():
    cur, conn = get_cursor()
    cur.execute("SELECT user_id, name, email FROM Users WHERE account_type = 'Student'")
    rows = cur.fetchall()
    conn.close()
    return jsonify([{'student_id': u, 'name': n, 'email': e} for u, n, e in rows])

@app.route('/students/<int:student_id>/courses', methods=['GET'])
def get_student_courses(student_id):
    cur, conn = get_cursor()
    cur.execute("""
        SELECT c.course_id,
               c.title
          FROM Courses c
          JOIN Enrollments e ON c.course_id = e.course_id
         WHERE e.user_id = %s
    """, (student_id,))
    rows = cur.fetchall()
    conn.close()
    return jsonify([{'course_id': cid, 'title': title} for cid, title in rows])

@app.route('/students/<int:student_id>/average', methods=['GET'])
def get_student_average(student_id):
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

# --- Lecturers -------------------------------------------------------------

@app.route('/lecturers/<int:lecturer_id>/courses', methods=['GET'])
def get_lecturer_courses(lecturer_id):
    cur, conn = get_cursor()
    cur.execute("""
        SELECT course_id, title
          FROM Courses
         WHERE lecturer_id = %s
    """, (lecturer_id,))
    rows = cur.fetchall()
    conn.close()
    return jsonify([{'course_id': cid, 'title': title} for cid, title in rows])

# --- Registration & Submissions --------------------------------------------

@app.route('/courses/<int:course_id>/register', methods=['POST'])
def register_course(course_id):
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

@app.route('/courses/<int:course_id>/assignments/<int:assignment_id>/submit', methods=['POST'])
def submit_assignment(course_id, assignment_id):
    data = request.get_json()
    student_id = data.get('student_id')
    content    = data.get('content')
    submitted_at = data.get('submitted_at')
    if not all([student_id, content, submitted_at]):
        return jsonify({'error': 'Missing fields'}), 400

    cur, conn = get_cursor()
    cur.execute("""
        INSERT INTO Submissions (assignment_id, user_id, file_link, submitted_at)
        VALUES (%s, %s, %s, %s)
        RETURNING submission_id
    """, (assignment_id, student_id, content, submitted_at))
    sub_id, = cur.fetchone()
    conn.commit()
    conn.close()
    return jsonify({'submission_id': sub_id})

@app.route('/submissions/<int:submission_id>/grade', methods=['PUT'])
def grade_submission(submission_id):
    data = request.get_json()
    grader_id = data.get('grader_id')
    grade     = data.get('grade')
    if grader_id is None or grade is None:
        return jsonify({'error': 'Missing `grader_id` or `grade`'}), 400

    cur, conn = get_cursor()
    cur.execute("""
        UPDATE Submissions
           SET grade = %s,
               grader_id = %s
         WHERE submission_id = %s
         RETURNING submission_id, grader_id, grade
    """, (grade, grader_id, submission_id))
    row = cur.fetchone()
    conn.commit()
    conn.close()
    if not row:
        return jsonify({'error': 'Submission not found'}), 404

    return jsonify({
        'submission_id': row[0],
        'grader_id'    : row[1],
        'grade'        : float(row[2])
    })

# --- Reporting -------------------------------------------------------------

def make_report(view_name, columns):
    cur, conn = get_cursor()
    cur.execute(f"SELECT * FROM {view_name}")
    rows = cur.fetchall()
    conn.close()
    return jsonify([dict(zip(columns, r)) for r in rows])

@app.route('/reports/courses_50_plus', methods=['GET'])
def report_courses_50_plus():
    return make_report('courses_50_plus', ['course_id','title','student_count'])

@app.route('/reports/students_5_plus', methods=['GET'])
def report_students_5_plus():
    return make_report('students_5_plus', ['student_id','student_name','course_count'])

@app.route('/reports/lecturers_3_plus', methods=['GET'])
def report_lecturers_3_plus():
    return make_report('lecturers_3_plus', ['lecturer_id','lecturer_name','course_count'])

@app.route('/reports/top_10_enrolled', methods=['GET'])
def report_top_10_enrolled():
    return make_report('top_10_enrolled', ['course_id','title','student_count'])

@app.route('/reports/top_10_students', methods=['GET'])
def report_top_10_students():
    return make_report('top_10_students', ['student_id','student_name','average_grade'])

if __name__ == '__main__':
    app.run(debug=True, port=5000)