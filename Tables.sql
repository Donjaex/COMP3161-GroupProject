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
