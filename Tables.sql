CREATE TABLE Users (
    user_id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    account_type VARCHAR(20) CHECK (account_type IN ('Admin', 'Student', 'Lecturer')),
    email VARCHAR(150) UNIQUE NOT NULL,
    password VARCHAR(255) NOT NULL
);


CREATE TABLE Login (
    login_id SERIAL PRIMARY KEY,
    user_id INT REFERENCES Users(user_id),
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    email VARCHAR(150),
    password VARCHAR(255)
);


CREATE TABLE Courses (
    course_id SERIAL PRIMARY KEY,
    course_name VARCHAR(150) NOT NULL,
    description TEXT,
    lecturer_id INT REFERENCES Users(user_id) -- must be a lecturer
);



CREATE TABLE Enrollments (
    user_id INT REFERENCES Users(user_id),
    course_id INT REFERENCES Courses(course_id),
    PRIMARY KEY (user_id, course_id)
);



CREATE TABLE CalendarEvents (
    event_id SERIAL PRIMARY KEY,
    course_id INT REFERENCES Courses(course_id),
    event_title VARCHAR(255),
    event_date DATE NOT NULL
);




CREATE TABLE Forums (
    forum_id SERIAL PRIMARY KEY,
    course_id INT REFERENCES Courses(course_id),
    forum_title VARCHAR(255)
);


DROP TABLE IF EXISTS DiscussionThreads CASCADE;


CREATE TABLE DiscussionThreads (
    thread_id SERIAL PRIMARY KEY,
    forum_id INT REFERENCES Forums(forum_id),
    user_id INT REFERENCES Users(user_id),
    title VARCHAR(255),
    content TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);





CREATE TABLE Replies (
    reply_id SERIAL PRIMARY KEY,
    thread_id INT REFERENCES DiscussionThreads(thread_id),
    parent_reply_id INT REFERENCES Replies(reply_id),
    user_id INT REFERENCES Users(user_id),
    content TEXT,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);


CREATE TABLE Assignments (
    assignment_id SERIAL PRIMARY KEY,
    course_id INT REFERENCES Courses(course_id),
    title VARCHAR(255),
    due_date DATE
);




SELECT
    s.user_id,
    AVG(s.grade) AS final_average
FROM
    Submissions s
JOIN
    Assignments a ON s.assignment_id = a.assignment_id
GROUP BY
    s.user_id
ORDER BY
    final_average DESC;


CREATE TABLE Submissions (
    assignment_id INT REFERENCES Assignments(assignment_id),
    user_id INT REFERENCES Users(user_id),
    file_link TEXT,
    submitted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    grade DECIMAL(5,2),
    PRIMARY KEY (assignment_id, user_id)
);



CREATE TABLE Sections (
    section_id SERIAL PRIMARY KEY,
    course_id INT REFERENCES Courses(course_id),
    section_title VARCHAR(255),
    section_type VARCHAR(50) 
);



CREATE TABLE SectionItems (
    item_id SERIAL PRIMARY KEY,
    section_id INT REFERENCES Sections(section_id),
    type VARCHAR(50), 
    name VARCHAR(255),
    link TEXT
);


CREATE VIEW students_5_plus AS
SELECT
    u.user_id AS student_id,
    u.name AS student_name,
    COUNT(e.course_id) AS course_count
FROM
    Users u
JOIN
    Enrollments e ON u.user_id = e.user_id
WHERE
    u.account_type = 'Student'
GROUP BY
    u.user_id, u.name
HAVING
    COUNT(e.course_id) >= 5;







    CREATE VIEW courses_50_plus AS
SELECT
    c.course_id,
    c.course_name, -- or whatever your column is
    COUNT(e.user_id) AS student_count
FROM
    Courses c
JOIN
    Enrollments e ON c.course_id = e.course_id
GROUP BY
    c.course_id, c.course_name
HAVING
    COUNT(e.user_id) > 50;



CREATE VIEW lecturers_3_plus AS
SELECT
    u.user_id AS lecturer_id,
    u.name AS lecturer_name,
    COUNT(c.course_id) AS course_count
FROM
    Users u
JOIN
    Courses c ON u.user_id = c.lecturer_id
WHERE
    u.account_type = 'Lecturer'
GROUP BY
    u.user_id, u.name
HAVING
    COUNT(c.course_id) >= 3;

CREATE OR REPLACE VIEW top_10_enrolled AS
SELECT 
    c.course_id, 
    c.title AS course_name, 
    COUNT(e.user_id) AS student_count
FROM 
    Courses c 
JOIN 
    Enrollments e ON c.course_id = e.course_id 
GROUP BY 
    c.course_id, c.title 
ORDER BY 
    student_count DESC 
LIMIT 10;



-- First, drop the view if it exists
DROP VIEW IF EXISTS top_10_enrolled;

-- Then create it
CREATE VIEW top_10_enrolled AS
SELECT 
    c.course_id,
    c.course_name, -- Replace with your actual column name if different
    COUNT(e.user_id) AS student_count
FROM 
    Courses c 
JOIN 
    Enrollments e ON c.course_id = e.course_id 
GROUP BY 
    c.course_id, c.course_name
ORDER BY 
    student_count DESC 
LIMIT 10;


--check if its 100000 students
SELECT COUNT(*) AS student_count 
FROM Users 
WHERE account_type = 'Student';


-- b. Check if you have at least 200 courses
SELECT COUNT(*) AS course_count 
FROM Courses;


-- c. Check that no student is doing more than 6 courses
SELECT u.user_id, u.name, COUNT(e.course_id) AS course_count
FROM Users u
JOIN Enrollments e ON u.user_id = e.user_id
WHERE u.account_type = 'Student'
GROUP BY u.user_id, u.name
HAVING COUNT(e.course_id) > 6
ORDER BY course_count DESC;


-- d. Check that all students are enrolled in at least 3 courses
SELECT u.user_id, u.name, COUNT(e.course_id) AS course_count
FROM Users u
LEFT JOIN Enrollments e ON u.user_id = e.user_id
WHERE u.account_type = 'Student'
GROUP BY u.user_id, u.name
HAVING COUNT(e.course_id) < 3
ORDER BY course_count ASC;
-- Should return 0 rows if requirement is met

-- e. Check that each course has at least 10 members
SELECT c.course_id, 
       c.course_name AS course_name, 
       COUNT(e.user_id) AS student_count
FROM Courses c
LEFT JOIN Enrollments e ON c.course_id = e.course_id
GROUP BY c.course_id, c.course_name
HAVING COUNT(e.user_id) < 10
ORDER BY student_count ASC;


-- f. Check that no lecturer teaches more than 5 courses
SELECT u.user_id, u.name, COUNT(c.course_id) AS course_count
FROM Users u
JOIN Courses c ON u.user_id = c.lecturer_id
WHERE u.account_type = 'Lecturer'
GROUP BY u.user_id, u.name
HAVING COUNT(c.course_id) > 5
ORDER BY course_count DESC;

-- g. Check that each lecturer teaches at least 1 course
SELECT u.user_id, u.name, COUNT(c.course_id) AS course_count
FROM Users u
LEFT JOIN Courses c ON u.user_id = c.lecturer_id
WHERE u.account_type = 'Lecturer'
GROUP BY u.user_id, u.name
HAVING COUNT(c.course_id) < 1
ORDER BY course_count ASC;



