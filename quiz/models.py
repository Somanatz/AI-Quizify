from django.db import models
from django.conf import settings # To potentially link to the User model
import json

class Quiz(models.Model):
    """Stores the details of a generated quiz."""
    id = models.AutoField(primary_key=True) # Explicitly define the primary key
    topic = models.CharField(max_length=255)
    difficulty = models.CharField(max_length=10, choices=[('Easy', 'Easy'), ('Medium', 'Medium'), ('Hard', 'Hard')])
    question_type = models.CharField(max_length=10, choices=[('mcq', 'Multiple Choice'), ('fill', 'Fill in the Blank'), ('tf', 'True/False')])
    explanation = models.TextField(blank=True, null=True)
    # Store the questions list as JSON
    questions_data = models.JSONField(default=list)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Quiz on '{self.topic}' ({self.difficulty}) - {self.created_at.strftime('%Y-%m-%d %H:%M')}"

    def get_questions(self):
        """Helper to load questions from JSON."""
        return self.questions_data if isinstance(self.questions_data, list) else []

class QuizAttempt(models.Model):
    """Stores the results of a user attempting a specific quiz."""
    id = models.AutoField(primary_key=True) # Explicitly define the primary key
    quiz = models.ForeignKey(Quiz, on_delete=models.CASCADE, related_name='attempts')
    # Optional: Link to the logged-in user if you have user authentication
    # user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, null=True, blank=True)
    submitted_answers = models.JSONField(default=dict) # Store user's answers { 'q1': 'answer1', ... }
    score = models.IntegerField()
    total_questions = models.IntegerField()
    percentage = models.FloatField()
    # Store detailed results for feedback
    results_data = models.JSONField(default=list) # Store the list of result dicts from check_answers
    attempted_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        user_info = f"User {self.user_id}" if hasattr(self, 'user') and self.user else "Anonymous User"
        return f"Attempt on '{self.quiz.topic}' by {user_info} - Score: {self.score}/{self.total_questions} ({self.percentage}%)"

    def get_detailed_results(self):
        """Helper to load detailed results from JSON."""
        return self.results_data if isinstance(self.results_data, list) else []
