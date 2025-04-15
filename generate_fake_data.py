from faker import Faker
import random

fake = Faker()

# Requirements
num_lecturers = 10
num_courses = 200
num_students = 100000

lecturers = []
courses = []
students = []

course_names = [
    "Introduction to Programming", "Data Structures", "Database Systems", "Algorithms",
    "Computer Networks", "Software Engineering", "Operating Systems", "Discrete Mathematics",
    "Artificial Intelligence", "Machine Learning", "Web Development", "Mobile Application Development",
    "Cybersecurity", "Cloud Computing", "Computer Graphics", "Computer Vision", "Data Science",
    "Human-Computer Interaction", "Computer Architecture", "Game Development", "Big Data",
    "Network Security", "Digital Forensics", "Ethical Hacking", "Database Administration",
    "Systems Programming", "Cloud Infrastructure", "Natural Language Processing", "AI Ethics",
    "Blockchain Technology", "Robotics", "Programming Languages", "Data Analytics",
    "Data Mining", "Information Retrieval", "Computational Biology", "Quantum Computing",
    "Autonomous Systems", "Cryptography", "Parallel Computing", "Cloud Databases", "Intelligent Systems",
    "Advanced Operating Systems", "Bioinformatics", "Deep Learning", "Search Engine Optimization",
    "Web Security", "IoT Systems", "Virtual Reality", "Business Intelligence", "Geographic Information Systems"
]

# Generate users (lecturers and students)
users = []
for i in range(num_lecturers):
    users.append({
        'user_id': i + 1,
        'name': fake.name().replace("'", "''"),
        'account_type': 'Lecturer',
        'email': fake.unique.email(),
        'password': fake.password()
    })
for i in range(num_students):
    users.append({
        'user_id': num_lecturers + i + 1,
        'name': fake.name().replace("'", "''"),
        'account_type': 'Student',
        'email': fake.unique.email(),
        'password': fake.password()
    })

# Generate courses
for i in range(num_courses):
    courses.append({
        'course_id': i + 1,
        'course_name': random.choice(course_names).replace("'", "''"),
        'description': fake.paragraph().replace("'", "''"),
        'lecturer_id': random.randint(1, num_lecturers)
    })

# Enrollments
enrollments = []
course_student_count = {c['course_id']: 0 for c in courses}
for student in users[num_lecturers:]:  # Only students
    selected_courses = random.sample(courses, random.randint(3, 6))
    for course in selected_courses:
        enrollments.append({
            'user_id': student['user_id'],
            'course_id': course['course_id']
        })
        course_student_count[course['course_id']] += 1

# Ensure each course has at least 10 students
for course in courses:
    while course_student_count[course['course_id']] < 10:
        student = random.choice(users[num_lecturers:])
        enrollments.append({
            'user_id': student['user_id'],
            'course_id': course['course_id']
        })
        course_student_count[course['course_id']] += 1

# Assignments and Submissions
assignments = []
submissions = []
assignment_id = 1
for course in courses:
    for _ in range(random.randint(2, 4)):
        due = fake.date_between(start_date='+1d', end_date='+90d')
        assignments.append({
            'assignment_id': assignment_id,
            'course_id': course['course_id'],
            'title': fake.sentence().replace("'", "''"),
            'due_date': due
        })
        enrolled_students = [e['user_id'] for e in enrollments if e['course_id'] == course['course_id']]
        for student_id in random.sample(enrolled_students, min(20, len(enrolled_students))):
            grade = random.choice([None, random.choice([5.0, 10.0, 15.0])])
            submissions.append({
                'assignment_id': assignment_id,
                'user_id': student_id,
                'file_link': fake.url().replace("'", "''"),
                'submitted_at': fake.date_this_year(),
                'grade': grade
            })
        assignment_id += 1

# Calendar Events
calendar_events = []
for course in courses:
    for _ in range(random.randint(1, 3)):
        calendar_events.append({
            'event_id': fake.unique.random_int(),
            'course_id': course['course_id'],
            'event_title': fake.catch_phrase().replace("'", "''"),
            'event_date': fake.date_between(start_date='today', end_date='+90d')
        })

# Forums, Threads, Replies
forums = []
threads = []
replies = []
forum_id = 1
thread_id = 1
reply_id = 1
for course in courses:
    forums.append({'forum_id': forum_id, 'course_id': course['course_id'], 'forum_title': f"{course['course_name']} Forum".replace("'", "''")})
    for _ in range(random.randint(1, 3)):
        threads.append({
            'thread_id': thread_id,
            'forum_id': forum_id,
            'user_id': random.choice(users[num_lecturers:])['user_id'],
            'title': fake.sentence().replace("'", "''"),
            'content': fake.paragraph().replace("'", "''")
        })
        for _ in range(random.randint(1, 4)):
            replies.append({
                'reply_id': reply_id,
                'thread_id': thread_id,
                'user_id': random.choice(users[num_lecturers:])['user_id'],
                'content': fake.sentence().replace("'", "''")
            })
            reply_id += 1
        thread_id += 1
    forum_id += 1

# Write to file
with open('insert_data.sql', 'w', encoding='utf-8') as f:
    for user in users:
        f.write(f"INSERT INTO Users (user_id, name, account_type, email, password) VALUES ({user['user_id']}, '{user['name']}', '{user['account_type']}', '{user['email']}', '{user['password']}');\n")

    for course in courses:
        f.write(f"INSERT INTO Courses (course_id, course_name, description, lecturer_id) VALUES ({course['course_id']}, '{course['course_name']}', '{course['description']}', {course['lecturer_id']});\n")

    for enrollment in enrollments:
        f.write(f"INSERT INTO Enrollments (user_id, course_id) VALUES ({enrollment['user_id']}, {enrollment['course_id']});\n")

    for assignment in assignments:
        f.write(f"INSERT INTO Assignments (assignment_id, course_id, title, due_date) VALUES ({assignment['assignment_id']}, {assignment['course_id']}, '{assignment['title']}', '{assignment['due_date']}');\n")

    for submission in submissions:
        grade_value = 'NULL' if submission['grade'] is None else submission['grade']
        f.write(f"INSERT INTO Submissions (assignment_id, user_id, file_link, submitted_at, grade) VALUES ({submission['assignment_id']}, {submission['user_id']}, '{submission['file_link']}', '{submission['submitted_at']}', {grade_value});\n")

    for event in calendar_events:
        f.write(f"INSERT INTO CalendarEvents (event_id, course_id, event_title, event_date) VALUES ({event['event_id']}, {event['course_id']}, '{event['event_title']}', '{event['event_date']}');\n")

    for forum in forums:
        f.write(f"INSERT INTO Forums (forum_id, course_id, forum_title) VALUES ({forum['forum_id']}, {forum['course_id']}, '{forum['forum_title']}');\n")

    for thread in threads:
        f.write(f"INSERT INTO DiscussionThreads (thread_id, forum_id, user_id, title, content) VALUES ({thread['thread_id']}, {thread['forum_id']}, {thread['user_id']}, '{thread['title']}', '{thread['content']}');\n")

    for reply in replies:
        f.write(f"INSERT INTO Replies (reply_id, thread_id, user_id, content) VALUES ({reply['reply_id']}, {reply['thread_id']}, {reply['user_id']}, '{reply['content']}');\n")
