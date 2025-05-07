from django.contrib import admin
from .models import Quiz, QuizAttempt

class QuizAdmin(admin.ModelAdmin):
    list_display = ('topic', 'difficulty', 'question_type', 'created_at', 'get_question_count')
    list_filter = ('difficulty', 'question_type', 'created_at')
    search_fields = ('topic', 'explanation')
    readonly_fields = ('created_at',)

    def get_question_count(self, obj):
        return len(obj.get_questions())
    get_question_count.short_description = 'No. Questions'

class QuizAttemptAdmin(admin.ModelAdmin):
    list_display = ('quiz', 'score', 'total_questions', 'percentage', 'attempted_at')
    list_filter = ('attempted_at', 'quiz__difficulty')
    search_fields = ('quiz__topic',)
    readonly_fields = ('attempted_at', 'quiz', 'submitted_answers', 'results_data') # Make fields non-editable in admin

    # Optional: If using User model
    # raw_id_fields = ('user',)

admin.site.register(Quiz, QuizAdmin)
admin.site.register(QuizAttempt, QuizAttemptAdmin)
