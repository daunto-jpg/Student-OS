# Student OS

An AI-powered academic management application built for university students.

## Overview

Student OS brings a student's academic life into one desktop application.

It manages:

- Courses
- Timetable
- Assignments
- Attendance
- Notes
- Student profile/settings
- AI-powered academic assistance

Core academic functions are designed to work offline, while AI features require an internet connection.

## Technology Stack

- Python
- SQLite
- CustomTkinter
- Google Gemini API
- Git & GitHub
- pytest

## Project Architecture

The project is divided into three partitions:

### Partition A — Core Backend

Responsible for:

- Database
- Course management
- Timetable
- Assignments
- Attendance
- Notes

### Partition B — GUI & UX

Responsible for:

- Application shell
- Navigation
- Dashboard
- Courses screen
- Timetable screen
- Assignments screen
- Attendance screen
- Notes screen
- Settings

### Partition C — AI & Quality Assurance

Responsible for:

- Gemini API integration
- AI prompt templates
- Academic context builder
- AI routing
- Automated testing
- Documentation

## Repository Structure

```text
student-os/
│
├── student_os/       # Core application/backend
├── gui/              # Graphical interface
├── ai/               # AI integration
├── tests/             # Automated tests
├── docs/              # Documentation
│
├── main.py            # Application entry point
├── requirements.txt   # Python dependencies
├── .gitignore
└── README.md
