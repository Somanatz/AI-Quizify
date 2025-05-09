
from django.db import models
from django.conf import settings # To potentially link to the User model
import json

class Quiz(models.Model):
    """Stores the details of a generated quiz."""
    QUESTION_TYPE_CHOICES = [
        ('mcq', 'Multiple Choice'),
        ('fill', 'Fill in the Blank'),
        ('tf', 'True/False'),
        ('mixed', 'Mixed Types') # Added mixed type
    ]
    DIFFICULTY_CHOICES = [
        ('Easy', 'Easy'), 
        ('Medium', 'Medium'), 
        ('Hard', 'Hard')
    ]

    id = models.AutoField(primary_key=True) 
    topic = models.CharField(max_length=255)
    difficulty = models.CharField(max_length=10, choices=DIFFICULTY_CHOICES)
    # This field will store the primary requested type, e.g., 'mcq', 'fill', 'tf', or 'mixed'
    question_type = models.CharField(max_length=10, choices=QUESTION_TYPE_CHOICES) 
    explanation = models.TextField(blank=True, null=True)
    questions_data = models.JSONField(default=list) # Each question in this list will have its own 'type' key
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        type_display = dict(self.QUESTION_TYPE_CHOICES).get(self.question_type, self.question_type.capitalize())
        return f"Quiz on '{self.topic}' ({type_display}, {self.difficulty}) - {self.created_at.strftime('%Y-%m-%d %H:%M')}"

    def get_questions(self):
        return self.questions_data if isinstance(self.questions_data, list) else []

class QuizAttempt(models.Model):
    """Stores the results of a user attempting a specific quiz."""
    id = models.AutoField(primary_key=True)
    quiz = models.ForeignKey(Quiz, on_delete=models.CASCADE, related_name='attempts')
    submitted_answers = models.JSONField(default=dict) 
    score = models.IntegerField()
    total_questions = models.IntegerField()
    percentage = models.FloatField()
    results_data = models.JSONField(default=list) 
    attempted_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        user_info = f"User {self.user_id}" if hasattr(self, 'user') and self.user else "Anonymous User" # Placeholder if user model is added
        return f"Attempt on '{self.quiz.topic}' by {user_info} - Score: {self.score}/{self.total_questions} ({self.percentage}%)"

    def get_detailed_results(self):
        return self.results_data if isinstance(self.results_data, list) else []


    
