
USE submitexp;

-- START TEST TRANSACTION

START TRANSACTION;

-- TEST 1: CREATE TEST USER

SET @test_username = CONCAT(
    'test_',
    LEFT(REPLACE(UUID(), '-', ''), 12)
);

INSERT INTO users (
    username,
    email,
    password_hash,
    role
)
VALUES (
    @test_username,
    CONCAT(@test_username, '@example.invalid'),
    'TEST_ONLY_NOT_A_REAL_HASH',
    'student'
);

SET @test_user_id = LAST_INSERT_ID();

SELECT *
FROM users
WHERE user_id = @test_user_id;

-- TEST 2: CREATE TEST SUBMISSION

INSERT INTO submissions (
    user_id,
    assignment_title,
    course_name,
    submission_type,
    due_at,
    submitted_at
)
VALUES (
    @test_user_id,
    'Statistics Homework 1',
    'STA 3032',
    'assignment',
    DATE_ADD(UTC_TIMESTAMP(), INTERVAL 1 DAY),
    UTC_TIMESTAMP()
);

SET @test_submission_id = LAST_INSERT_ID();

SELECT *
FROM submissions
WHERE submission_id = @test_submission_id;

-- TEST 3: AWARD TEST POINTS

INSERT INTO point_transactions (
    submission_id,
    points_awarded,
    reason
)
VALUES (
    @test_submission_id,
    100,
    'Test: submitted one day early'
);

SELECT *
FROM point_transactions
WHERE submission_id = @test_submission_id;

-- TEST 4: CREATE USER PROGRESS

INSERT INTO user_progress (
    user_id,
    total_points,
    current_level
)
VALUES (
    @test_user_id,
    100,
    1
);

SELECT *
FROM user_progress
WHERE user_id = @test_user_id;

-- TEST 5: VERIFY TABLE RELATIONSHIPS

SELECT
    u.user_id,
    u.username,
    u.email,
    u.role,

    s.submission_id,
    s.assignment_title,
    s.course_name,
    s.submission_type,
    s.due_at,
    s.submitted_at,

    pt.transaction_id,
    pt.points_awarded,
    pt.reason,

    up.total_points,
    up.current_level

FROM users u

JOIN submissions s
    ON u.user_id = s.user_id

JOIN point_transactions pt
    ON s.submission_id = pt.submission_id

JOIN user_progress up
    ON u.user_id = up.user_id

WHERE u.user_id = @test_user_id;

-- TEST 6: VERIFY POINT TOTAL

SELECT
    up.user_id,
    up.total_points,
    SUM(pt.points_awarded) AS calculated_points,

    CASE
        WHEN up.total_points = SUM(pt.points_awarded)
        THEN 'PASS'
        ELSE 'FAIL'
    END AS points_test

FROM user_progress up

JOIN submissions s
    ON up.user_id = s.user_id

JOIN point_transactions pt
    ON s.submission_id = pt.submission_id

WHERE up.user_id = @test_user_id

GROUP BY
    up.user_id,
    up.total_points;

-- TEST 7: VERIFY ALL TEST RECORDS

SELECT
    (SELECT COUNT(*) FROM users
     WHERE user_id = @test_user_id)
        AS users_found,

    (SELECT COUNT(*) FROM submissions
     WHERE submission_id = @test_submission_id)
        AS submissions_found,

    (SELECT COUNT(*) FROM point_transactions
     WHERE submission_id = @test_submission_id)
        AS transactions_found,

    (SELECT COUNT(*) FROM user_progress
     WHERE user_id = @test_user_id)
        AS progress_found;

-- TEST 8: REMOVE TEMPORARY DATA

ROLLBACK;

-- TEST 9: VERIFY CLEANUP

SELECT
    (SELECT COUNT(*) FROM users
     WHERE user_id = @test_user_id)
        AS users_remaining,

    (SELECT COUNT(*) FROM submissions
     WHERE submission_id = @test_submission_id)
        AS submissions_remaining,

    (SELECT COUNT(*) FROM point_transactions
     WHERE submission_id = @test_submission_id)
        AS transactions_remaining,

    (SELECT COUNT(*) FROM user_progress
     WHERE user_id = @test_user_id)
        AS progress_remaining;

-- TEST 10: VERIFY DATABASE TABLES

SHOW TABLES;

DESCRIBE users;
DESCRIBE submissions;
DESCRIBE point_transactions;
DESCRIBE user_progress;
