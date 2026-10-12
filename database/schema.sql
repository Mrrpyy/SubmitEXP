
USE submitexp;

-- USERS TABLE

CREATE TABLE IF NOT EXISTS users (
    user_id INT AUTO_INCREMENT PRIMARY KEY,

    username VARCHAR(50) NOT NULL UNIQUE,

    email VARCHAR(255) NOT NULL UNIQUE,

    password_hash VARCHAR(255) NOT NULL,

    role ENUM('student', 'admin')
        NOT NULL DEFAULT 'student',

    created_at TIMESTAMP
        DEFAULT CURRENT_TIMESTAMP,

    updated_at TIMESTAMP
        DEFAULT CURRENT_TIMESTAMP
        ON UPDATE CURRENT_TIMESTAMP
);

-- SUBMISSIONS TABLE

CREATE TABLE IF NOT EXISTS submissions (
    submission_id INT AUTO_INCREMENT PRIMARY KEY,

    user_id INT NOT NULL,

    assignment_title VARCHAR(255) NOT NULL,

    course_name VARCHAR(150),

    submission_type ENUM(
        'assignment',
        'test',
        'exam'
    ) NOT NULL DEFAULT 'assignment',

    due_at DATETIME,

    submitted_at DATETIME,

    created_at TIMESTAMP
        DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT fk_submissions_user
        FOREIGN KEY (user_id)
        REFERENCES users(user_id)
        ON DELETE CASCADE
);

-- POINT TRANSACTIONS TABLE

CREATE TABLE IF NOT EXISTS point_transactions (
    transaction_id INT AUTO_INCREMENT PRIMARY KEY,

    submission_id INT NOT NULL UNIQUE,

    points_awarded INT NOT NULL,

    reason VARCHAR(255),

    awarded_at TIMESTAMP
        DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT chk_points_nonnegative
        CHECK (points_awarded >= 0),

    CONSTRAINT fk_points_submission
        FOREIGN KEY (submission_id)
        REFERENCES submissions(submission_id)
        ON DELETE CASCADE
);

-- USER PROGRESS TABLE

CREATE TABLE IF NOT EXISTS user_progress (
    user_id INT PRIMARY KEY,

    total_points INT NOT NULL DEFAULT 0,

    current_level INT NOT NULL DEFAULT 1,

    updated_at TIMESTAMP
        DEFAULT CURRENT_TIMESTAMP
        ON UPDATE CURRENT_TIMESTAMP,

    CONSTRAINT chk_total_points
        CHECK (total_points >= 0),

    CONSTRAINT chk_current_level
        CHECK (current_level >= 1),

    CONSTRAINT fk_progress_user
        FOREIGN KEY (user_id)
        REFERENCES users(user_id)
        ON DELETE CASCADE
);

-- VERIFY TABLES

SHOW TABLES;

DESCRIBE users;

DESCRIBE submissions;

DESCRIBE point_transactions;

DESCRIBE user_progress;
