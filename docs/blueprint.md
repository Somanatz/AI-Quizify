# **App Name**: Quizify

## Core Features:

- Question Generation: Generate multiple choice, fill-in-the-blank, or true/false questions based on a given topic and difficulty level using the Mistral-7B-Instruct-v0.3 model. The generated questions are based on content which is generated using the same LLM. This is a tool for generating the questions.
- Question Display: Display the generated questions in a clear and organized format, with appropriate input fields for each question type (multiple choice, fill-in-the-blank, true/false).
- User Input: Allow users to select a topic, question type (MCQ, fill-in-the-blank, true/false), and difficulty level for question generation. 

## Style Guidelines:

- Primary color: A calm teal (#4DB6AC) for a learning-focused environment.
- Secondary color: Light gray (#EEEEEE) for clean backgrounds and content separation.
- Accent: A vivid orange (#FF8A65) for interactive elements and call-to-action buttons.
- Clean and structured layout to focus on the generated questions.
- Use simple, clear icons for different question types (MCQ, fill-in-the-blank, true/false).

## Original User Request:
using this python file code (from rest_framework.views import APIView from rest_framework.response import Response from rest_framework import status from huggingface_hub import InferenceClient from .models import QuestionRequest from .serializers import QuestionRequestSerializer

client = InferenceClient( model="mistralai/Mistral-7B-Instruct-v0.3", token="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" # Replace with your actual API key )

class GenerateQuestionsAPI(APIView): def post(self, request): # Validate request data serializer = QuestionRequestSerializer(data=request.data) if not serializer.is_valid(): return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST) else: serializer.save()

    data = serializer.validated_data
    topic = data["topic"]
    question_type = data["question_type"]
    difficulty = data["difficulty"]

    # Step 1: Generate Content using Hugging Face Model
    content_prompt = f"Provide a detailed explanation about {topic} with difficulty level: {difficulty}."
    content = client.text_generation(content_prompt, max_new_tokens=500, temperature=0.7)

    if not content:
        return Response({"error": "Failed to generate content"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    # Step 2: Select Prompt Based on Question Type
    if question_type == "mcq":
        question_prompt = (
            f"Generate 5 multiple-choice questions (MCQs) based on the following content: ({content}) with difficulty level: {difficulty}.\n\n"
            f"Format:\n1) Question\n  a) Option A\n  b) Option B\n  c) Option C\n  d) Option D\nAnswer: Correct Option\n\n"
        )
    elif question_type == "fill":
        question_prompt = (
            f"Generate 5 fill-in-the-blank questions based on the following Forma (The ______ is an example of topic) and content: ({content}) with difficulty level: {difficulty}.\n\n"
        )
    elif question_type == "tf":
        question_prompt = (
            f"Generate Five True/False questions based on the following content: ({content}) with difficulty level: {difficulty}.\n\n"
            f"question format should be like this:\n1) Statement\n  a) True\n  b) False\n\n"
        )
    else:
        return Response({"error": "Invalid question type"}, status=status.HTTP_400_BAD_REQUEST)

    # Step 3: Generate Questions
    questions = client.text_generation(question_prompt, max_new_tokens=300, temperature=0.7).strip()

    if not questions:
        return Response({"error": "Failed to generate questions"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    # Step 4: Return Response in JSON Format
    return Response({
        "topic": topic,
        "difficulty": difficulty,
        "content": content,
        "questions": questions.split("\n")  # Convert to list format
    }, status=status.HTTP_200_OK).
- use tech stack python, django framework (frentend and backend part)
  