from django.urls import path
from . import views

app_name = 'quiz'

urlpatterns = [
    path('', views.index, name='index'),
    path('check/', views.check_answers, name='check_answers'), # Added route for checking answers
    path('send_quiz_email/', views.send_quiz_email, name='send_quiz_email'),
]
