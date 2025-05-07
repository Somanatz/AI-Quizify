from django.test import TestCase
from django.urls import reverse

class QuizViewTests(TestCase):
    def test_index_view_get(self):
        """
        Test that the index view loads correctly via GET request.
        """
        response = self.client.get(reverse('quiz:index'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Quizify") # Check for a key element

    def test_index_view_post_placeholder(self):
        """
        Test the POST request to the index view (with placeholder logic).
        """
        response = self.client.post(reverse('quiz:index'), {
            'topic': 'Test Topic',
            'question_type': 'mcq',
            'difficulty': 'Easy',
        })
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Placeholder explanation")
        self.assertContains(response, "Test Topic")
        self.assertContains(response, "Easy")
        self.assertContains(response, "Placeholder Q1 (mcq)")
