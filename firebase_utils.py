import firebase_admin
from firebase_admin import credentials, db

# Initialize Firebase once in your project
def initialize_firebase():
    try:
        cred = credentials.Certificate("credentials/firebase-credentials.json")
        firebase_admin.initialize_app(cred, {
            'databaseURL': 'https://teacher-assistant-65215-default-rtdb.firebaseio.com/'
        })
        print("Firebase initialized successfully.")
    except Exception as e:
        print("Firebase initialization failed:", e)

def update_student_progress(student_id, progress_data):
    """
    Update student progress in Firebase.
    """
    try:
        ref = db.reference(f'/students/{student_id}/progress')
        ref.update(progress_data)
        return "Progress updated successfully."
    except Exception as e:
        return f"Failed to update progress: {e}"
