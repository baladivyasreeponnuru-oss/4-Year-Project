from parser import parse_question_bank, parse_header, parse_reference_paper, parse_syllabus
from ai_engine import classify_bloom, predict_difficulty, check_duplicate, generate_paper, generate_template_questions, generate_mixed_paper, generate_mcqs_from_syllabus, generate_mcqs_with_ai
from pdf_generator import generate_question_paper_pdf
import os
from dotenv import load_dotenv
load_dotenv()  # reads OPENAI_API_KEY from a local .env file, keeps it out of source code
from flask import Flask, jsonify, request, send_from_directory
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__, static_folder='static', static_url_path='')
CORS(app)

app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+mysqlconnector://root:project%4012345@localhost/question_paper_generator'
db = SQLAlchemy(app)

class User(db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False)
    role = db.Column(db.Enum('admin', 'faculty'), nullable=False)
class Subject(db.Model):
    __tablename__ = 'subjects'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    code = db.Column(db.String(20))
    semester = db.Column(db.String(20))

class SyllabusUnit(db.Model):
    __tablename__ = 'syllabus_units'
    id = db.Column(db.Integer, primary_key=True)
    subject_id = db.Column(db.Integer, db.ForeignKey('subjects.id'))
    unit_name = db.Column(db.String(150))
    topics = db.Column(db.Text)

class Question(db.Model):
    __tablename__ = 'questions'
    id = db.Column(db.Integer, primary_key=True)
    subject_id = db.Column(db.Integer, db.ForeignKey('subjects.id'))
    unit_id = db.Column(db.Integer, db.ForeignKey('syllabus_units.id'))
    question_text = db.Column(db.Text, nullable=False)
    marks = db.Column(db.Integer)
    bloom_level = db.Column(db.String(20))
    difficulty = db.Column(db.String(10))
    is_duplicate = db.Column(db.Boolean, default=False)

class FacultyAssignment(db.Model):
    __tablename__ = 'faculty_assignments'
    id = db.Column(db.Integer, primary_key=True)
    faculty_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    subject_id = db.Column(db.Integer, db.ForeignKey('subjects.id'))


@app.route('/')
def home():
    return app.send_static_file('login.html')
@app.route('/add_user', methods=['POST'])
def add_user():
    data = request.json
    hashed_password = generate_password_hash(data['password'])
    new_user = User(
        name=data['name'],
        email=data['email'],
        password=hashed_password,
        role=data['role']
    )
    db.session.add(new_user)
    db.session.commit()
    return jsonify({"message": "User added successfully!"})

@app.route('/login', methods=['POST'])
def login():
    data = request.json
    user = User.query.filter_by(email=data['email']).first()
    if user and check_password_hash(user.password, data['password']):
        return jsonify({"message": "Login successful!", "id": user.id, "role": user.role, "name": user.name})
    else:
        return jsonify({"message": "Invalid email or password"}), 401

@app.route('/users', methods=['GET'])
def get_users():
    users = User.query.all()
    result = [{"id": u.id, "name": u.name, "email": u.email, "role": u.role} for u in users]
    return jsonify(result)

@app.route('/update_user/<int:user_id>', methods=['POST'])
def update_user(user_id):
    data = request.json
    user = User.query.get(user_id)
    if not user:
        return jsonify({"message": "User not found"}), 404
    user.name = data.get('name', user.name)
    user.email = data.get('email', user.email)
    db.session.commit()
    return jsonify({"message": "User updated successfully!"})
@app.route('/add_subject', methods=['POST'])
def add_subject():
    data = request.json
    new_subject = Subject(
        name=data['name'],
        code=data.get('code'),
        semester=data.get('semester')
    )
    db.session.add(new_subject)
    db.session.commit()
    return jsonify({"message": "Subject added successfully!"})

@app.route('/subjects', methods=['GET'])
def get_subjects():
    subjects = Subject.query.all()
    result = [{"id": s.id, "name": s.name, "code": s.code, "semester": s.semester} for s in subjects]
    return jsonify(result)

@app.route('/faculty_subjects/<int:faculty_id>', methods=['GET'])
def faculty_subjects(faculty_id):
    assignments = FacultyAssignment.query.filter_by(faculty_id=faculty_id).all()
    subject_ids = [a.subject_id for a in assignments]
    subjects = Subject.query.filter(Subject.id.in_(subject_ids)).all() if subject_ids else []
    result = [{"id": s.id, "name": s.name, "code": s.code, "semester": s.semester} for s in subjects]
    return jsonify(result)

@app.route('/update_subject/<int:subject_id>', methods=['POST'])
def update_subject(subject_id):
    data = request.json
    subject = Subject.query.get(subject_id)
    if not subject:
        return jsonify({"message": "Subject not found"}), 404
    subject.name = data.get('name', subject.name)
    subject.code = data.get('code', subject.code)
    subject.semester = data.get('semester', subject.semester)
    db.session.commit()
    return jsonify({"message": "Subject updated successfully!"})

@app.route('/add_unit', methods=['POST'])
def add_unit():
    data = request.json
    new_unit = SyllabusUnit(
        subject_id=data['subject_id'],
        unit_name=data['unit_name']
    )
    db.session.add(new_unit)
    db.session.commit()
    return jsonify({"message": "Unit added successfully!"})

@app.route('/add_units_bulk', methods=['POST'])
def add_units_bulk():
    data = request.json
    subject_id = data['subject_id']
    unit_names = data['unit_names']  # list of strings

    added = 0
    for name in unit_names:
        name = name.strip()
        if name:
            db.session.add(SyllabusUnit(subject_id=subject_id, unit_name=name))
            added += 1
    db.session.commit()

    return jsonify({"message": f"{added} units added successfully!"})

@app.route('/assign_faculty', methods=['POST'])
def assign_faculty():
    data = request.json
    faculty_id = data['faculty_id']
    subject_id = data['subject_id']

    existing = FacultyAssignment.query.filter_by(faculty_id=faculty_id, subject_id=subject_id).first()
    if existing:
        return jsonify({"message": "Already assigned!"})

    new_assignment = FacultyAssignment(faculty_id=faculty_id, subject_id=subject_id)
    db.session.add(new_assignment)
    db.session.commit()
    return jsonify({"message": "Faculty assigned to subject successfully!"})

class GeneratedPaper(db.Model):
    __tablename__ = 'generated_papers'
    id = db.Column(db.Integer, primary_key=True)
    subject_id = db.Column(db.Integer, db.ForeignKey('subjects.id'))
    faculty_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    question_ids = db.Column(db.Text)
    pdf_filename = db.Column(db.String(255))
    created_at = db.Column(db.DateTime, server_default=db.func.now())

class Student(db.Model):
    __tablename__ = 'students'
    id = db.Column(db.Integer, primary_key=True)
    roll_number = db.Column(db.String(30), unique=True)
    name = db.Column(db.String(100))
    password = db.Column(db.String(255))
    subject_id = db.Column(db.Integer, db.ForeignKey('subjects.id'))  # legacy, unused going forward

class StudentSubject(db.Model):
    __tablename__ = 'student_subjects'
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('students.id'))
    subject_id = db.Column(db.Integer, db.ForeignKey('subjects.id'))

class MCQBatch(db.Model):
    __tablename__ = 'mcq_batches'
    id = db.Column(db.Integer, primary_key=True)
    subject_id = db.Column(db.Integer, db.ForeignKey('subjects.id'))
    total_questions = db.Column(db.Integer, default=0)
    posted = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, server_default=db.func.now())

class MCQQuestion(db.Model):
    __tablename__ = 'mcq_questions'
    id = db.Column(db.Integer, primary_key=True)
    subject_id = db.Column(db.Integer, db.ForeignKey('subjects.id'))
    batch_id = db.Column(db.Integer, db.ForeignKey('mcq_batches.id'))
    posted = db.Column(db.Boolean, default=False)
    question_text = db.Column(db.Text)
    option_a = db.Column(db.String(255))
    option_b = db.Column(db.String(255))
    option_c = db.Column(db.String(255))
    option_d = db.Column(db.String(255))
    correct_option = db.Column(db.String(1))
    created_at = db.Column(db.DateTime, server_default=db.func.now())

class MCQAttempt(db.Model):
    __tablename__ = 'mcq_attempts'
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('students.id'))
    subject_id = db.Column(db.Integer, db.ForeignKey('subjects.id'))
    total_questions = db.Column(db.Integer)
    correct_answers = db.Column(db.Integer)
    marks_obtained = db.Column(db.Integer)
    max_marks = db.Column(db.Integer)
    passed = db.Column(db.Boolean)
    attempted_at = db.Column(db.DateTime, server_default=db.func.now())

class ExternalMarks(db.Model):
    __tablename__ = 'external_marks'
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('students.id'))
    subject_id = db.Column(db.Integer, db.ForeignKey('subjects.id'))
    marks_obtained = db.Column(db.Integer)
    max_marks = db.Column(db.Integer)
    passed = db.Column(db.Boolean)
    entered_at = db.Column(db.DateTime, server_default=db.func.now())

@app.route('/subjects_overview', methods=['GET'])
def subjects_overview():
    subjects = Subject.query.all()
    result = []
    for s in subjects:
        assignments = FacultyAssignment.query.filter_by(subject_id=s.id).all()
        faculty_list = []
        for a in assignments:
            f = User.query.get(a.faculty_id)
            if f:
                faculty_list.append({"id": f.id, "name": f.name, "email": f.email})

        question_count = Question.query.filter_by(subject_id=s.id).count()
        unit_count = SyllabusUnit.query.filter_by(subject_id=s.id).count()

        result.append({
            "subject_id": s.id,
            "subject_name": s.name,
            "code": s.code,
            "semester": s.semester,
            "faculty": faculty_list,
            "question_count": question_count,
            "unit_count": unit_count
        })
    return jsonify(result)


@app.route('/unassign_faculty', methods=['POST'])
def unassign_faculty():
    data = request.json
    faculty_id = data['faculty_id']
    subject_id = data['subject_id']
    FacultyAssignment.query.filter_by(faculty_id=faculty_id, subject_id=subject_id).delete()
    db.session.commit()
    return jsonify({"message": "Faculty removed from subject."})

@app.route('/remove_subject/<int:subject_id>', methods=['POST'])
def remove_subject(subject_id):
    try:
        # Children first, in dependency order, then the subject itself.
        MCQQuestion.query.filter_by(subject_id=subject_id).delete()   # references mcq_batches.id
        MCQBatch.query.filter_by(subject_id=subject_id).delete()
        MCQAttempt.query.filter_by(subject_id=subject_id).delete()
        ExternalMarks.query.filter_by(subject_id=subject_id).delete()
        StudentSubject.query.filter_by(subject_id=subject_id).delete()
        # Legacy column on students — unlink rather than delete the student
        # (they may still be enrolled in other subjects).
        Student.query.filter_by(subject_id=subject_id).update({"subject_id": None})
        GeneratedPaper.query.filter_by(subject_id=subject_id).delete()
        Question.query.filter_by(subject_id=subject_id).delete()
        SyllabusUnit.query.filter_by(subject_id=subject_id).delete()
        FacultyAssignment.query.filter_by(subject_id=subject_id).delete()
        Subject.query.filter_by(id=subject_id).delete()
        db.session.commit()
        return jsonify({"message": "Subject removed."})
    except Exception as e:
        db.session.rollback()
        return jsonify({"message": f"Could not remove subject: {str(e)}"}), 500


@app.route('/remove_faculty/<int:user_id>', methods=['POST'])
def remove_faculty(user_id):
    FacultyAssignment.query.filter_by(faculty_id=user_id).delete()
    User.query.filter_by(id=user_id, role='faculty').delete()
    db.session.commit()
    return jsonify({"message": "Faculty account removed."})

@app.route('/upload_syllabus', methods=['POST'])
def upload_syllabus():
    file = request.files['file']
    subject_id = request.form.get('subject_id')

    file_path = os.path.join(UPLOAD_FOLDER, file.filename)
    file.save(file_path)
    parsed_units = parse_syllabus(file_path)
    existing_names = [u.unit_name for u in SyllabusUnit.query.filter_by(subject_id=subject_id).all()]

    added = 0
    for u in parsed_units:
        if u['unit_name'] not in existing_names:
            db.session.add(SyllabusUnit(subject_id=subject_id, unit_name=u['unit_name'], topics=u['topics']))
            existing_names.append(u['unit_name'])
            added += 1
    db.session.commit()

    return jsonify({"message": f"{added} units extracted and added from syllabus!"})

 
@app.route('/units/<int:subject_id>', methods=['GET'])
def get_units(subject_id):
    units = SyllabusUnit.query.filter_by(subject_id=subject_id).all()
    result = [{"id": u.id, "unit_name": u.unit_name} for u in units]
    return jsonify(result)
UPLOAD_FOLDER = 'uploads'
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)
@app.route('/upload_questions', methods=['POST'])
def upload_questions():
    file = request.files['file']
    subject_id = request.form.get('subject_id')
    
    file_path = os.path.join(UPLOAD_FOLDER, file.filename)
    file.save(file_path)
    
    parsed_questions = parse_question_bank(file_path)
    
    existing_questions = [q.question_text for q in Question.query.filter_by(subject_id=subject_id).all()]
    
    saved_count = 0
    for q in parsed_questions:
        unit = SyllabusUnit.query.filter_by(subject_id=subject_id, unit_name=q['unit']).first()
        unit_id = unit.id if unit else None
        
        bloom_level = classify_bloom(q['question'])
        difficulty = predict_difficulty(q['question'], q['marks'])
        is_dup, matched = check_duplicate(q['question'], existing_questions)
        
        new_question = Question(
            subject_id=subject_id,
            unit_id=unit_id,
            question_text=q['question'],
            marks=q['marks'],
            bloom_level=bloom_level,
            difficulty=difficulty,
            is_duplicate=is_dup
        )
        db.session.add(new_question)
        existing_questions.append(q['question'])
        saved_count += 1
    
    db.session.commit()
    
    return jsonify({
        "message": "File uploaded, parsed, tagged, and saved successfully!",
        "total_questions_saved": saved_count
    })

@app.route('/upload_reference_paper', methods=['POST'])
def upload_reference_paper():
    file = request.files['file']
    file_path = os.path.join(UPLOAD_FOLDER, file.filename)
    file.save(file_path)

    header = parse_header(file_path)
    questions = parse_reference_paper(file_path)

    total_marks = sum(q['marks'] for q in questions if not q['is_alternative'])

    return jsonify({
        "message": "Reference paper parsed successfully!",
        "header": header,
        "total_questions_found": len(questions),
        "total_marks_detected": total_marks,
        "questions": questions
    })
@app.route('/generate_paper', methods=['POST'])
def generate_paper_route():
    data = request.json
    subject_id = data['subject_id']
    pattern = data['pattern']
    header = data.get('header', {})

    selected, part_a, part_b = generate_mixed_paper(subject_id, pattern, db, Question, SyllabusUnit)

    if not selected:
        return jsonify({
            "message": "No questions matched this pattern. Check that your question bank has questions "
                        "tagged with these exact marks values, and that a syllabus is uploaded for this subject."
        }), 400

    total_marks = sum(q.marks for q in selected)

    pdf_filename = f"question_paper_subject{subject_id}.pdf"
    pdf_path = os.path.join(UPLOAD_FOLDER, pdf_filename)
    generate_question_paper_pdf(header, part_a, part_b, pdf_path)
    new_record = GeneratedPaper(
    subject_id=subject_id,
    question_ids=",".join(str(q.id) for q in selected),
    pdf_filename=pdf_filename
    )
    db.session.add(new_record)
    db.session.commit()

    return jsonify({
        "message": "Paper generated successfully!",
        "total_questions": len(selected),
        "total_marks": total_marks,
        "pdf_path": pdf_path
    })



@app.route('/paper_history/<int:subject_id>', methods=['GET'])
def paper_history(subject_id):
    papers = GeneratedPaper.query.filter_by(subject_id=subject_id).order_by(GeneratedPaper.created_at.desc()).all()
    result = [{
        "id": p.id,
        "pdf_filename": p.pdf_filename,
        "created_at": p.created_at.strftime("%d %b %Y, %I:%M %p") if p.created_at else "",
        "question_count": len(p.question_ids.split(",")) if p.question_ids else 0
    } for p in papers]
    return jsonify(result)
@app.route('/remove_question/<int:question_id>', methods=['POST'])
def remove_question(question_id):
    q = Question.query.get(question_id)
    if not q:
        return jsonify({"message": "Question not found."}), 404
    db.session.delete(q)
    db.session.commit()
    return jsonify({"message": "Question removed."})

@app.route('/questions/<int:subject_id>', methods=['GET'])
def get_questions(subject_id):
    questions = Question.query.filter_by(subject_id=subject_id).all()
    result = [{
        "id": q.id,
        "question": q.question_text,
        "marks": q.marks,
        "unit_id": q.unit_id,
        "bloom_level": q.bloom_level,
        "difficulty": q.difficulty,
        "is_duplicate": q.is_duplicate
    } for q in questions]
    return jsonify(result)


@app.route('/stats/<int:subject_id>', methods=['GET'])
def get_stats(subject_id):
    total = Question.query.filter_by(subject_id=subject_id).count()
    tagged = Question.query.filter_by(subject_id=subject_id).filter(Question.bloom_level.isnot(None)).count()
    duplicates = Question.query.filter_by(subject_id=subject_id, is_duplicate=True).count()
    units = SyllabusUnit.query.filter_by(subject_id=subject_id).count()
    return jsonify({
        "total_questions": total,
        "tagged_questions": tagged,
        "duplicate_questions": duplicates,
        "total_units": units
    })
@app.route('/download/<filename>', methods=['GET'])
def download_pdf(filename):
    return send_from_directory(UPLOAD_FOLDER, filename, as_attachment=True)

@app.route('/view_pdf/<filename>', methods=['GET'])
def view_pdf(filename):
    return send_from_directory(UPLOAD_FOLDER, filename, as_attachment=False)

@app.route('/subject_info/<int:subject_id>', methods=['GET'])
def subject_info(subject_id):
    s = Subject.query.get(subject_id)
    if not s:
        return jsonify({}), 404
    assignments = FacultyAssignment.query.filter_by(subject_id=subject_id).all()
    faculty_names = [User.query.get(a.faculty_id).name for a in assignments if User.query.get(a.faculty_id)]
    return jsonify({
        "name": s.name, "code": s.code, "semester": s.semester,
        "faculty": ", ".join(faculty_names) if faculty_names else "TBA"
    })

@app.route('/add_student', methods=['POST'])
def add_student():
    data = request.json
    roll_number = data['roll_number']
    subject_id = data['subject_id']

    student = Student.query.filter_by(roll_number=roll_number).first()
    if student:
        # Existing student (from another subject) — just enroll them here too.
        already = StudentSubject.query.filter_by(student_id=student.id, subject_id=subject_id).first()
        if already:
            return jsonify({"message": f"{student.name} is already enrolled in this subject."})
        db.session.add(StudentSubject(student_id=student.id, subject_id=subject_id))
        db.session.commit()
        return jsonify({"message": f"Existing student {student.name} enrolled in this subject."})

    hashed = generate_password_hash(data['password'])
    student = Student(roll_number=roll_number, name=data['name'], password=hashed)
    db.session.add(student)
    db.session.flush()  # get student.id before commit
    db.session.add(StudentSubject(student_id=student.id, subject_id=subject_id))
    db.session.commit()
    return jsonify({"message": "Student added and enrolled successfully!"})

@app.route('/remove_student/<int:student_id>', methods=['POST'])
def remove_student(student_id):
    try:
        StudentSubject.query.filter_by(student_id=student_id).delete()
        MCQAttempt.query.filter_by(student_id=student_id).delete()
        ExternalMarks.query.filter_by(student_id=student_id).delete()
        Student.query.filter_by(id=student_id).delete()
        db.session.commit()
        return jsonify({"message": "Student removed."})
    except Exception as e:
        db.session.rollback()
        return jsonify({"message": f"Could not remove student: {str(e)}"}), 500

@app.route('/students/<int:subject_id>', methods=['GET'])
def get_students(subject_id):
    enrollments = StudentSubject.query.filter_by(subject_id=subject_id).all()
    result = []
    for e in enrollments:
        s = Student.query.get(e.student_id)
        if s:
            result.append({"id": s.id, "roll_number": s.roll_number, "name": s.name})
    return jsonify(result)

@app.route('/student_login', methods=['POST'])
def student_login():
    data = request.json
    s = Student.query.filter_by(roll_number=data['roll_number']).first()
    if s and check_password_hash(s.password, data['password']):
        enrollments = StudentSubject.query.filter_by(student_id=s.id).all()
        subjects = []
        for e in enrollments:
            subj = Subject.query.get(e.subject_id)
            if subj:
                subjects.append({"id": subj.id, "name": subj.name, "code": subj.code, "semester": subj.semester})
        return jsonify({"message": "Login successful!", "id": s.id, "name": s.name, "subjects": subjects})
    return jsonify({"message": "Invalid credentials"}), 401

@app.route('/my_results_all/<int:student_id>', methods=['GET'])
def my_results_all(student_id):
    enrollments = StudentSubject.query.filter_by(student_id=student_id).all()
    result = []
    for e in enrollments:
        subj = Subject.query.get(e.subject_id)
        if not subj:
            continue
        internal = MCQAttempt.query.filter_by(student_id=student_id, subject_id=subj.id).order_by(MCQAttempt.attempted_at.desc()).first()
        external = ExternalMarks.query.filter_by(student_id=student_id, subject_id=subj.id).order_by(ExternalMarks.entered_at.desc()).first()
        result.append({
            "subject_id": subj.id,
            "subject_name": subj.name,
            "code": subj.code,
            "internal": {"marks": internal.marks_obtained, "max": internal.max_marks, "passed": internal.passed} if internal else None,
            "external": {"marks": external.marks_obtained, "max": external.max_marks, "passed": external.passed} if external else None
        })
    return jsonify(result)

@app.route('/add_mcq', methods=['POST'])
def add_mcq():
    data = request.json
    m = MCQQuestion(subject_id=data['subject_id'], question_text=data['question_text'],
        option_a=data['option_a'], option_b=data['option_b'], option_c=data['option_c'],
        option_d=data['option_d'], correct_option=data['correct_option'])
    db.session.add(m); db.session.commit()
    return jsonify({"message": "MCQ added successfully!"})

@app.route('/generate_mcqs_from_syllabus', methods=['POST'])
def generate_mcqs_route():
    data = request.json
    subject_id = data['subject_id']
    target_total = int(data.get('target_total', 30))

    subject = Subject.query.get(subject_id)
    if not subject:
        return jsonify({"message": "Subject not found."}), 404

    mcqs = generate_mcqs_with_ai(subject_id, subject.name, db, SyllabusUnit, target_total=target_total)

    if not mcqs:
        return jsonify({"message": "Could not generate MCQs. Make sure a syllabus with at least 4 topics is uploaded for this subject."}), 400

    batch = MCQBatch(subject_id=subject_id, total_questions=len(mcqs), posted=False)
    db.session.add(batch)
    db.session.flush()  # get batch.id before commit

    for m in mcqs:
        new_mcq = MCQQuestion(
            subject_id=subject_id,
            batch_id=batch.id,
            posted=False,
            question_text=m['question_text'],
            option_a=m['option_a'], option_b=m['option_b'],
            option_c=m['option_c'], option_d=m['option_d'],
            correct_option=m['correct_option']
        )
        db.session.add(new_mcq)
    db.session.commit()

    shortfall_note = "" if len(mcqs) >= target_total else f" (requested {target_total} — some Gemini calls returned fewer questions than asked, check the server console for details)"

    return jsonify({
        "message": f"{len(mcqs)} bits generated{shortfall_note}. View and post it from MCQ History to make it live.",
        "batch_id": batch.id,
        "total_questions": len(mcqs)
    })

@app.route('/mcq_batches/<int:subject_id>', methods=['GET'])
def mcq_batches(subject_id):
    batches = MCQBatch.query.filter_by(subject_id=subject_id).order_by(MCQBatch.created_at.desc()).all()
    return jsonify([{
        "id": b.id,
        "total_questions": b.total_questions,
        "posted": b.posted,
        "created_at": b.created_at.strftime("%d %b %Y, %I:%M %p") if b.created_at else ""
    } for b in batches])

@app.route('/mcq_batch_questions/<int:batch_id>', methods=['GET'])
def mcq_batch_questions(batch_id):
    qs = MCQQuestion.query.filter_by(batch_id=batch_id).all()
    return jsonify([{
        "id": q.id, "question_text": q.question_text,
        "option_a": q.option_a, "option_b": q.option_b,
        "option_c": q.option_c, "option_d": q.option_d,
        "correct_option": q.correct_option
    } for q in qs])

@app.route('/remove_mcq_question/<int:mcq_id>', methods=['POST'])
def remove_mcq_question(mcq_id):
    q = MCQQuestion.query.get(mcq_id)
    if not q:
        return jsonify({"message": "Question not found."}), 404
    batch = MCQBatch.query.get(q.batch_id)
    db.session.delete(q)
    if batch and batch.total_questions and batch.total_questions > 0:
        batch.total_questions -= 1
    db.session.commit()
    return jsonify({"message": "Bit removed."})

@app.route('/remove_mcq_batch/<int:batch_id>', methods=['POST'])
def remove_mcq_batch(batch_id):
    MCQQuestion.query.filter_by(batch_id=batch_id).delete()
    MCQBatch.query.filter_by(id=batch_id).delete()
    db.session.commit()
    return jsonify({"message": "Batch removed."})

@app.route('/post_mcq_batch/<int:batch_id>', methods=['POST'])
def post_mcq_batch(batch_id):
    batch = MCQBatch.query.get(batch_id)
    if not batch:
        return jsonify({"message": "Batch not found"}), 404

    # Only one live bit-set per subject at a time: unpost any previously posted batch
    other_batches = MCQBatch.query.filter_by(subject_id=batch.subject_id, posted=True).all()
    for ob in other_batches:
        ob.posted = False
        MCQQuestion.query.filter_by(batch_id=ob.id).update({"posted": False})

    batch.posted = True
    MCQQuestion.query.filter_by(batch_id=batch.id).update({"posted": True})
    db.session.commit()
    return jsonify({"message": "Posted! This set is now live for students."})

@app.route('/mcqs/<int:subject_id>', methods=['GET'])
def get_mcqs(subject_id):
    qs = MCQQuestion.query.filter_by(subject_id=subject_id, posted=True).all()
    return jsonify([{"id": q.id, "question_text": q.question_text, "option_a": q.option_a,
        "option_b": q.option_b, "option_c": q.option_c, "option_d": q.option_d} for q in qs])

@app.route('/submit_attempt', methods=['POST'])
def submit_attempt():
    data = request.json
    student_id = data['student_id']
    subject_id = data['subject_id']
    answers = data['answers']  # { "mcq_id": "A", ... }

    correct = 0
    for mcq_id, chosen in answers.items():
        q = MCQQuestion.query.get(int(mcq_id))
        if q and q.correct_option == chosen:
            correct += 1

    total = len(answers)
    marks = correct
    passed = marks >= (total * 0.35)

    attempt = MCQAttempt(student_id=student_id, subject_id=subject_id, total_questions=total,
        correct_answers=correct, marks_obtained=marks, max_marks=total, passed=passed)
    db.session.add(attempt); db.session.commit()
    return jsonify({"message": "Submitted!", "marks_obtained": marks, "max_marks": total, "passed": passed})

@app.route('/results_overview/<int:subject_id>', methods=['GET'])
def results_overview(subject_id):
    attempts = MCQAttempt.query.filter_by(subject_id=subject_id).all()
    total = len(attempts)
    passed = len([a for a in attempts if a.passed])
    return jsonify({
        "total_attempts": total,
        "passed": passed,
        "failed": total - passed,
        "pass_percentage": round((passed / total) * 100, 1) if total else 0
    })

@app.route('/my_attempt/<int:student_id>/<int:subject_id>', methods=['GET'])
def my_attempt(student_id, subject_id):
    attempt = MCQAttempt.query.filter_by(
        student_id=student_id, subject_id=subject_id
    ).order_by(MCQAttempt.attempted_at.desc()).first()

    if not attempt:
        return jsonify({"attempted": False})

    return jsonify({
        "attempted": True,
        "marks_obtained": attempt.marks_obtained,
        "max_marks": attempt.max_marks,
        "passed": attempt.passed
    })


@app.route('/my_external_marks/<int:student_id>/<int:subject_id>', methods=['GET'])
def my_external_marks(student_id, subject_id):
    m = ExternalMarks.query.filter_by(student_id=student_id, subject_id=subject_id).order_by(ExternalMarks.entered_at.desc()).first()
    if not m:
        return jsonify({"entered": False})
    return jsonify({"entered": True, "marks_obtained": m.marks_obtained, "max_marks": m.max_marks, "passed": m.passed})


@app.route('/add_external_marks', methods=['POST'])
def add_external_marks():
    data = request.json
    max_marks = data.get('max_marks', 100)
    marks = data['marks_obtained']
    passed = marks >= (max_marks * 0.35)
    rec = ExternalMarks(student_id=data['student_id'], subject_id=data['subject_id'],
                         marks_obtained=marks, max_marks=max_marks, passed=passed)
    db.session.add(rec)
    db.session.commit()
    return jsonify({"message": "Marks entered successfully!"})


@app.route('/faculty_results/<int:subject_id>', methods=['GET'])
def faculty_results(subject_id):
    enrollments = StudentSubject.query.filter_by(subject_id=subject_id).all()
    result = []
    for e in enrollments:
        s = Student.query.get(e.student_id)
        if not s:
            continue
        internal = MCQAttempt.query.filter_by(student_id=s.id, subject_id=subject_id).order_by(MCQAttempt.attempted_at.desc()).first()
        external = ExternalMarks.query.filter_by(student_id=s.id, subject_id=subject_id).order_by(ExternalMarks.entered_at.desc()).first()
        result.append({
            "student_id": s.id,
            "roll_number": s.roll_number,
            "name": s.name,
            "internal": {"marks": internal.marks_obtained, "max": internal.max_marks, "passed": internal.passed} if internal else None,
            "external": {"marks": external.marks_obtained, "max": external.max_marks, "passed": external.passed} if external else None
        })
    return jsonify(result)


@app.route('/admin_results_overview', methods=['GET'])
def admin_results_overview():
    subjects = Subject.query.all()
    result = []
    for s in subjects:
        assignments = FacultyAssignment.query.filter_by(subject_id=s.id).all()
        faculty_names = [User.query.get(a.faculty_id).name for a in assignments if User.query.get(a.faculty_id)]

        internal_attempts = MCQAttempt.query.filter_by(subject_id=s.id).all()
        internal_total = len(internal_attempts)
        internal_passed = len([a for a in internal_attempts if a.passed])

        external_records = ExternalMarks.query.filter_by(subject_id=s.id).all()
        external_total = len(external_records)
        external_passed = len([e for e in external_records if e.passed])

        result.append({
            "subject_name": s.name,
            "code": s.code,
            "semester": s.semester,
            "faculty": faculty_names,
            "internal_total": internal_total,
            "internal_passed": internal_total - (internal_total - internal_passed),
            "internal_pass_pct": round((internal_passed / internal_total) * 100, 1) if internal_total else None,
            "external_total": external_total,
            "external_passed": external_passed,
            "external_pass_pct": round((external_passed / external_total) * 100, 1) if external_total else None,
        })
    return jsonify(result)

@app.route('/all_student_results', methods=['GET'])
def all_student_results():
    rows = []
    subjects = Subject.query.all()
    for s in subjects:
        assignments = FacultyAssignment.query.filter_by(subject_id=s.id).all()
        faculty_names = [User.query.get(a.faculty_id).name for a in assignments if User.query.get(a.faculty_id)]
        faculty_str = ", ".join(faculty_names) if faculty_names else "Unassigned"

        enrollments = StudentSubject.query.filter_by(subject_id=s.id).all()
        for e in enrollments:
            st = Student.query.get(e.student_id)
            if not st:
                continue
            internal = MCQAttempt.query.filter_by(student_id=st.id, subject_id=s.id).order_by(MCQAttempt.attempted_at.desc()).first()
            external = ExternalMarks.query.filter_by(student_id=st.id, subject_id=s.id).order_by(ExternalMarks.entered_at.desc()).first()
            rows.append({
                "subject_name": s.name, "code": s.code, "semester": s.semester, "faculty": faculty_str,
                "roll_number": st.roll_number, "student_name": st.name,
                "internal_marks": internal.marks_obtained if internal else "",
                "internal_max": internal.max_marks if internal else "",
                "internal_result": ("Pass" if internal.passed else "Fail") if internal else "Not attempted",
                "external_marks": external.marks_obtained if external else "",
                "external_max": external.max_marks if external else "",
                "external_result": ("Pass" if external.passed else "Fail") if external else "Not entered"
            })
    return jsonify(rows)
if __name__ == '__main__':
    app.run(debug=True)