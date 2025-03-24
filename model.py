import re
import numpy as np
from transformers import pipeline

# IMPORTANT: Ensure you have upgraded transformers to 4.31.0 or later and
# that you are using TensorFlow 2.12.0 with Keras 3.0.0:
# pip install --upgrade transformers
# pip install tensorflow==2.12.0 keras==3.0.0

class GradingModel:
    def __init__(self, max_chars=512, min_words=20, full_mark_word_count=500):
        """
        Initializes the grading model.
          - max_chars: Maximum characters to consider for the sentiment model.
          - min_words: Minimum words required for a valid submission.
          - full_mark_word_count: Word count that corresponds to a full score (100).
        """
        self.max_chars = max_chars
        self.min_words = min_words
        self.full_mark_word_count = full_mark_word_count
        # Initialize the sentiment-analysis pipeline.
        self.sentiment_pipeline = pipeline("sentiment-analysis")

    def clean_text(self, text):
        """
        Cleans the input text: lowercases, normalizes whitespace, and removes non-ASCII characters.
        """
        text = text.lower()
        text = re.sub(r'\s+', ' ', text).strip()
        text = text.encode('ascii', errors='ignore').decode('ascii')
        return text

    def preprocess_text(self, text):
        """
        Preprocesses the text by cleaning it.
        """
        return self.clean_text(text)

    def _map_sentiment_to_grade(self, label, sentiment_score):
        """
        Maps the sentiment analysis output to a grade out of 100.
        For positive sentiment, returns sentiment_score * 100.
        For negative sentiment, applies a conservative mapping.
        """
        if label.upper() == "POSITIVE":
            return sentiment_score * 100
        else:
            return (1 - sentiment_score) * 50

    def predict_grade(self, assignment_text):
        """
        Predicts a grade out of 100 using sentiment analysis as a proxy.
        Combines sentiment and a word-count heuristic for calibration.
        """
        processed_text = self.preprocess_text(assignment_text)
        words = processed_text.split()
        if len(words) < self.min_words:
            return 0.0  # Insufficient work
        truncated_text = processed_text[:self.max_chars]
        try:
            result = self.sentiment_pipeline(truncated_text)
            label = result[0]['label']
            sentiment_score = result[0]['score']
            grade_from_sentiment = self._map_sentiment_to_grade(label, sentiment_score)
            word_based_grade = min(100, (len(words) / self.full_mark_word_count) * 100)
            final_grade = (grade_from_sentiment + word_based_grade) / 2.0
            return final_grade
        except Exception as e:
            fallback_grade = min(100, (len(words) / self.full_mark_word_count) * 100)
            return fallback_grade

    def generate_feedback(self, grade):
        """
        Generates feedback based solely on the predicted grade.
        """
        if grade >= 80:
            return "Excellent work! Your essay is well-structured and insightful."
        elif grade >= 50:
            return "Good job. Consider adding more examples and details to support your ideas."
        else:
            return "Your work needs improvement. Focus on developing your arguments more clearly."

    def train_on_examples(self, examples, epochs=10):
        """
        Placeholder for training a custom model using teacher-provided examples.
        Currently, this function simulates training.
        """
        return {"epochs": epochs, "status": "Training simulated; no changes applied."}

# Global instance and helper functions
grading_model = GradingModel()

def predict_score(assignment_text):
    return grading_model.predict_grade(assignment_text)

def generate_feedback(grade, text):
    return grading_model.generate_feedback(grade)

def train_on_examples(examples, epochs=10):
    return grading_model.train_on_examples(examples, epochs)
