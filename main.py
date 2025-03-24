import os
from flask import Flask, request, jsonify, render_template
from werkzeug.utils import secure_filename
import PyPDF2

from model import predict_score, generate_feedback, train_on_examples
from firebase_utils import initialize_firebase, update_student_progress
from classroom_integration import ClassroomService

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16 MB

# Ensure the uploads folder exists
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

initialize_firebase()

def extract_text_from_pdf(filepath):
    text = ""
    try:
        with open(filepath, "rb") as f:
            reader = PyPDF2.PdfReader(f)
            for page in reader.pages:
                extracted = page.extract_text()
                if extracted:
                    text += extracted
    except Exception as e:
        text = f"Error extracting PDF text: {e}"
    return text

@app.route('/')
def home():
    return render_template('index.html')

# -------------------------------
# List courses from Classroom
# -------------------------------
@app.route('/list-courses', methods=['GET'])
def list_courses():
    cs = ClassroomService()
    courses = cs.list_courses()
    if isinstance(courses, list):
        return render_template('courses.html', courses=courses)
    else:
        return jsonify({"error": courses})

# -------------------------------
# Fetch assignments and auto-grade them for a given course
# -------------------------------
@app.route('/fetch-assignments', methods=['GET'])
def fetch_and_grade():
    course_id = request.args.get('course_id')
    if not course_id:
        return jsonify({"error": "course_id query parameter is required"}), 400
    cs = ClassroomService()
    assignments = cs.fetch_assignments(course_id)
    results = []
    if isinstance(assignments, list):
        for assignment in assignments:
            assignment_id = assignment.get('id')
            title = assignment.get('title', 'Untitled')
            description = assignment.get('description', '')
            grade = predict_score(description)
            feedback = generate_feedback(grade, description)
            results.append({
                "course_id": course_id,
                "coursework_id": assignment_id,
                "title": title,
                "grade": grade,
                "feedback": feedback
            })
        return render_template('assignments.html', assignments=results)
    else:
        return jsonify({"error": assignments})

# -------------------------------
# Automatically grade every student submission for every assignment in a course
# -------------------------------
@app.route('/grade-all', methods=['GET'])
def grade_all():
    course_id = request.args.get('course_id')
    if not course_id:
        return jsonify({"error": "course_id is required"}), 400
    cs = ClassroomService()
    assignments = cs.fetch_assignments(course_id)
    graded_results = []
    if not isinstance(assignments, list):
        return jsonify({"error": assignments}), 500
    for assignment in assignments:
        coursework_id = assignment.get('id')
        title = assignment.get('title', 'Untitled')
        grade = predict_score(assignment.get('description', ''))
        submissions = cs.get_student_submissions(course_id, coursework_id)
        if isinstance(submissions, list):
            for submission in submissions:
                student_submission_id = submission.get('id')
                result = cs.post_grade(course_id, coursework_id, student_submission_id, grade)
                graded_results.append({
                    "coursework_id": coursework_id,
                    "title": title,
                    "student_submission_id": student_submission_id,
                    "grade": grade,
                    "result": result
                })
        else:
            graded_results.append({
                "coursework_id": coursework_id,
                "title": title,
                "error": submissions
            })
    return render_template('grade_all_results.html', graded_results=graded_results)

# -------------------------------
# Upload a master copy for training (PDF or text)
# -------------------------------
@app.route('/upload-master', methods=['GET', 'POST'])
def upload_master():
    if request.method == 'POST':
        if 'master_file' in request.files and request.files['master_file'].filename != "":
            file = request.files['master_file']
            filename = secure_filename(file.filename)
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(filepath)
            master_text = extract_text_from_pdf(filepath)
        else:
            master_text = request.form.get('master_text', '')
        master_score = float(request.form.get('master_score', 0))
        training_example = {'text': master_text, 'score': master_score}
        history = train_on_examples([training_example], epochs=5)
        return render_template('master_upload.html', message="Master copy processed and model updated.", history=history)
    return render_template('master_upload.html')

# -------------------------------
# Upload a student assignment (PDF) for grading
# -------------------------------
@app.route('/upload-assignment', methods=['POST'])
def upload_assignment():
    try:
        if 'assignment_file' not in request.files:
            return jsonify({"error": "No file part in the request"}), 400
        file = request.files['assignment_file']
        if file.filename == '':
            return jsonify({"error": "No selected file"}), 400
        filename = secure_filename(file.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)
        assignment_text = extract_text_from_pdf(filepath)
        student_id = request.form.get('student_id')
        if not student_id:
            return jsonify({"error": "student_id is required"}), 400
        grade = predict_score(assignment_text)
        feedback = generate_feedback(grade, assignment_text)
        progress_data = {
            'last_assignment_grade': grade,
            'feedback': feedback
        }
        firebase_message = update_student_progress(student_id, progress_data)
        return jsonify({
            'grade': grade,
            'feedback': feedback,
            'firebase_message': firebase_message
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# -------------------------------
# Teacher training using multiple examples (JSON input)
# -------------------------------
@app.route('/train-model', methods=['POST'])
def train_model():
    try:
        data = request.get_json(force=True)
        examples = data.get('examples')
        if not examples:
            return jsonify({"error": "No examples provided"}), 400
        training_history = train_on_examples(examples, epochs=10)
        return jsonify({
            'status': 'Model updated successfully',
            'training_history': training_history
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True)
