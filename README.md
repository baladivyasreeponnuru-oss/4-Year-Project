# Examinare

**AI-Powered Exam Paper Generation & Results Management System**

Turns a syllabus and an existing question bank into a balanced, print-ready exam paper, then carries the exam through online MCQ tests and result tracking. Roles: Admin, Faculty, Student. NLP tags each question by Bloom's level and difficulty and catches reworded duplicates.

## Features

- **Admin:** create subjects and faculty accounts, assign faculty, view pass/fail overview by subject and faculty, export to Excel
- **Faculty:** upload syllabus and question bank (`.docx`), auto-tag questions (Bloom's, difficulty, duplicates), generate PDF paper (Part A compulsory, Part B with OR choices), generate MCQs with Gemini, manage students, enter external marks, download results
- **Student:** log in with roll number, take auto-graded MCQ test, view internal and external results

## Tech Stack

Flask, Flask-SQLAlchemy, MySQL, `sentence-transformers` (`all-MiniLM-L6-v2`, duplicate threshold 0.85), Google Gemini, `python-docx`, `reportlab`, HTML/CSS/JS, SheetJS

## How It Works

- **Paper generation:** one non-duplicate question is picked per unit; Part B adds an OR-alternative from a unit topic keyword
- **Pass mark:** 35% for both internal and external

## Setup

**Requirements:** Python 3.10+, MySQL 8.x, Gemini API key (for MCQs only)

```bash
git clone https://github.com/<your-username>/examinare.git
cd examinare
python -m venv venv
venv\Scripts\activate        # Windows (macOS/Linux: source venv/bin/activate)
pip install -r requirements.txt
```

1. Create the MySQL database `question_paper_generator` and its tables (see `schema.sql`).
2. Create a `.env` file (never commit it):
```
   DB_PASSWORD=your_mysql_password
   GEMINI_API_KEY=your_gemini_api_key
```
3. Run `python app.py` and open http://127.0.0.1:5000
4. Create the first admin (no sign-up page):
```python
   import requests
   requests.post("http://127.0.0.1:5000/add_user", json={
       "name": "Admin", "email": "admin@example.com",
       "password": "choose-a-strong-password", "role": "admin"})
```

## Input Formats (`.docx` only)

**Syllabus** (upload first):
```
UNIT 1: Introduction to NLP
Basics of NLP, applications, text preprocessing
```

**Question bank** (unit names must match the syllabus):
```
UNIT 1: Introduction to NLP

2 Marks Questions
1. Define natural language processing

12 Marks Questions
1. Explain the applications of NLP
```

## Limitations

- Bloom's and difficulty tagging are rule-based
- PDF layout supports the 5 x 2 + 5 x 12 (OR) pattern only
- No token-based auth (uses `localStorage`); add sessions or JWT before real deployment
- Uses Flask's dev server; use Gunicorn or Waitress with HTTPS in production

## Authors 

P.Baladivyasree and team · Guide: M.Vijay Bhaskar 
