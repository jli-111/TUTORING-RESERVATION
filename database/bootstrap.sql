-- Run as a MySQL administrator on your own instance.
-- Replace CHANGE_ME before running; do not commit real credentials.
CREATE DATABASE IF NOT EXISTS studyroom CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER IF NOT EXISTS 'studyroom'@'localhost' IDENTIFIED BY 'CHANGE_ME';
GRANT ALL PRIVILEGES ON studyroom.* TO 'studyroom'@'localhost';
-- Needed only for the automated test suite (Django creates/drops its own test DB).
GRANT ALL PRIVILEGES ON test_studyroom.* TO 'studyroom'@'localhost';
-- Tables and generated-column indexes are created by Django migrations.
