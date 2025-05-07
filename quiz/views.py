
from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpRequest, HttpResponse, Http404, JsonResponse # Use JsonResponse
from django.urls import reverse
from django.conf import settings
from google import genai
import json
import re # Import regular expressions
from .models import Quiz, QuizAttempt # Import models
from django.core.mail import EmailMultiAlternatives # Updated import
from django.template.loader import render_to_string
from django.contrib import messages
from django.views.decorators.csrf import csrf_exempt # For CSRF exemption on AJAX calls

# --- Helper Function for AI Generation ---
def generate_quiz_content(topic: str, question_type: str, difficulty: str, num_questions: int = 5):
    """
    Generates quiz content (explanation and questions) using the Gemini API.
    """
    api_key = settings.GOOGLE_API_KEY
    if not api_key:
        print("Error: GOOGLE_API_KEY not found in settings.")
        raise ValueError("Google API Key not configured.")

    client = genai.Client(api_key=api_key)
    model = 'gemini-2.0-flash'

    type_map = {
        'mcq': 'Multiple Choice (MCQ)',
        'fill': 'Fill in the Blank',
        'tf': 'True/False'
    }

    # Conditional prompt based on question type
    question_specific_prompt_instruction = ""
    if question_type == 'mcq':
        question_specific_prompt_instruction = """
        *   For "mcq" type: An "options" key with an array of exactly 4 distinct strings (potential answers), and an "answer" key with the correct option string (must exactly match one of the options).
        Example for MCQ:
        {{
          "question_text": "What is the powerhouse of the cell?",
          "type": "mcq",
          "difficulty": "Easy",
          "options": ["Nucleus", "Ribosome", "Mitochondrion", "Chloroplast"],
          "answer": "Mitochondrion"
        }}"""
    elif question_type == 'fill':
        question_specific_prompt_instruction = """
        *   For "fill" type: An "answer" key with the single word or short phrase (string) that correctly fills the blank (often indicated by '____' in the question_text). The answer should be concise.
        Example for Fill in the Blank:
        {{
          "question_text": "The chemical symbol for water is ____.",
          "type": "fill",
          "difficulty": "Easy",
          "answer": "H2O"
        }}"""
    elif question_type == 'tf':
        question_specific_prompt_instruction = """
        *   For "tf" type: An "answer" key with the boolean value true or false (not the string "true" or "false").
        Example for True/False:
        {{
          "question_text": "The sun revolves around the Earth.",
          "type": "tf",
          "difficulty": "Easy",
          "answer": false
        }}"""


    prompt = f"""
    Generate educational content about the topic "{topic}" suitable for a "{difficulty}" difficulty level.
    Include the following in your response, formatted STRICTLY as a single JSON object:

    1.  A key "explanation" containing a concise explanation of the topic ({difficulty} level), appropriate for someone learning this topic.
    2.  A key "questions" containing a JSON array of exactly {num_questions} questions about the topic. Each question object in the array MUST have:
        *   A "question_text" key with the question itself (string).
        *   A "type" key with the value "{question_type}" (string).
        *   A "difficulty" key with the value "{difficulty}" (string).
        {question_specific_prompt_instruction}

    Ensure the entire output is **only** a single, valid JSON object starting with {{ and ending with }}. Do not include any text, explanations, or markdown formatting like ```json before or after the JSON object itself. The "questions" array must contain exactly {num_questions} items.
    """

    try:
        response = client.models.generate_content(model=model, contents=prompt)
        raw_text = response.text
        # Attempt to parse JSON, with fallback for markdown-wrapped JSON
        try:
            generated_data = json.loads(raw_text)
        except json.JSONDecodeError:
            # Try to extract JSON from markdown code blocks
            json_match_md = re.search(r'```json\s*(\{.*\})\s*```', raw_text, re.DOTALL | re.IGNORECASE)
            if json_match_md:
                json_str = json_match_md.group(1)
            else:
                # Fallback: Try to find JSON between the first '{' and last '}'
                json_match_braces = re.search(r'\{.*\}', raw_text, re.DOTALL)
                if json_match_braces:
                    json_str = json_match_braces.group(0)
                else:
                    print(f"Failed to extract JSON. Raw response:\n{raw_text}")
                    raise ValueError("Could not find valid JSON in the AI response after multiple cleaning attempts.")
            try:
                generated_data = json.loads(json_str)
            except json.JSONDecodeError as e:
                print(f"Error decoding cleaned JSON: {e}")
                print(f"Cleaned JSON string was:\n{json_str}")
                print(f"Original raw response was:\n{raw_text}")
                raise ValueError(f"Failed to parse the AI's response as valid JSON even after cleaning. {e}") from e

        # Validate the structure of the generated JSON
        if 'explanation' not in generated_data or not isinstance(generated_data['explanation'], str):
            raise ValueError("Generated JSON is missing 'explanation' key or it's not a string.")
        if 'questions' not in generated_data or not isinstance(generated_data['questions'], list):
            raise ValueError("Generated JSON is missing 'questions' key or it's not a list.")
        
        # Validate number of questions returned vs requested
        if len(generated_data['questions']) != num_questions:
             # Log a warning but proceed with what was returned.
             print(f"Warning: AI returned {len(generated_data['questions'])} questions, but {num_questions} were requested. Using the {len(generated_data['questions'])} questions returned by the AI.")
             # num_questions variable in the current scope is not updated here, but the length of generated_data['questions'] is what matters for iteration.

        # Validate each question's structure
        for i, q in enumerate(generated_data['questions']):
             if not all(k in q for k in ['question_text', 'type', 'difficulty', 'answer']):
                 raise ValueError(f"Question {i+1} is missing required keys (question_text, type, difficulty, answer).")
             if q['type'] == 'mcq' and (not isinstance(q.get('options'), list) or len(q['options']) != 4 or q.get('answer') not in q['options']):
                 raise ValueError(f"MCQ Question {i+1} has invalid 'options' or 'answer'. Options must be a list of 4 strings, and answer must match one option.")
             if q['type'] == 'tf' and not isinstance(q.get('answer'), bool):
                 # Attempt to convert string "true"/"false" to boolean
                 if isinstance(q.get('answer'), str):
                     if q['answer'].lower() == 'true':
                         q['answer'] = True
                     elif q['answer'].lower() == 'false':
                         q['answer'] = False
                     else:
                         raise ValueError(f"True/False Question {i+1} has non-boolean answer: {q['answer']}.")
                 else:
                     raise ValueError(f"True/False Question {i+1} has non-boolean answer: {q['answer']}.")

        # Prepare the final result
        result = {
            'topic': topic,
            'difficulty': difficulty,
            'question_type': question_type,
            'content': generated_data.get('explanation', 'Explanation not generated.'),
            'questions': generated_data.get('questions', [])
        }
        return result

    except json.JSONDecodeError as e:
        # This catch block might be redundant if the inner try-except handles it,
        # but it's good for safety if the initial json.loads() fails before cleanup.
        print(f"Error decoding JSON response: {e}")
        print(f"Raw response text was:\n{response.text if 'response' in locals() else 'No response object'}")
        raise ValueError(f"Failed to parse the AI's response as valid JSON. Check the Gemini API response format. Error: {e}") from e
    except Exception as e:
        # Catch any other unexpected errors during generation
        print(f"An unexpected error occurred during AI generation: {e}")
        import traceback
        traceback.print_exc() # Print full traceback for debugging
        # Re-raise a more generic error to the view
        raise Exception(f"An error occurred while communicating with the AI service: {e}") from e


# --- Django Views ---

def index(request: HttpRequest) -> HttpResponse:
    """
    Renders the main quiz generation page (GET) and handles form submission
    to generate a quiz (POST).
    """
    context = {'form_data': {}} # Initialize form_data

    if request.method == 'POST':
        topic = request.POST.get('topic', '').strip()
        question_type = request.POST.get('question_type')
        difficulty = request.POST.get('difficulty')
        num_questions_str = request.POST.get('num_questions', '5') # Default to 5

        try:
            num_questions = int(num_questions_str)
            if not (1 <= num_questions <= 100): # Example: limit to 1-20 questions
                raise ValueError("Number of questions must be between 1 and 20.")
        except ValueError:
            num_questions = 5 # Default or error case
            context['error'] = "Invalid number of questions. Defaulting to 5."
            # Don't return yet, let the user see the error with their other inputs preserved

        # Store form data to repopulate the form on error or success
        context['form_data'] = {
            'topic': topic,
            'question_type': question_type,
            'difficulty': difficulty,
            'num_questions': num_questions # Store the validated or default number
        }

        # Validate required fields
        if not topic or not question_type or not difficulty:
            errors = []
            if not topic: errors.append("Please enter a topic.")
            if not question_type: errors.append("Please select a question type.")
            if not difficulty: errors.append("Please select a difficulty level.")
            # If there's already an error (e.g., num_questions), append to it
            current_error = context.get('error', '')
            context['error'] = (current_error + " " if current_error else "") + " ".join(errors)
            return render(request, 'quiz/index.html', context)
        
        # If there was a num_questions error earlier and other fields are also missing,
        # we might have already returned. This check ensures we handle it if not.
        if context.get('error') and ("Invalid number of questions" in context['error'] and (not topic or not question_type or not difficulty)):
             return render(request, 'quiz/index.html', context)


        try:
            quiz_data = generate_quiz_content(topic, question_type, difficulty, num_questions)

            # Create and save the Quiz object
            new_quiz = Quiz.objects.create(
                topic=quiz_data['topic'],
                difficulty=quiz_data['difficulty'],
                question_type=quiz_data['question_type'],
                explanation=quiz_data['content'],
                questions_data=quiz_data['questions']
            )
            # Store quiz ID in session if needed for subsequent actions (like check_answers)
            request.session['current_quiz_id'] = new_quiz.id

            context['quiz_result'] = {
                'quiz_id': new_quiz.id, # Pass the ID to the template
                'topic': new_quiz.topic,
                'difficulty': new_quiz.difficulty,
                'content': new_quiz.explanation,
                'questions': new_quiz.get_questions() # Use helper to get list
            }

        except ValueError as ve:
             # Specific errors from JSON parsing or validation within generate_quiz_content
             context['error'] = f"Generation Error: {ve}"
        except Exception as e:
            # General errors from AI communication or other unexpected issues
            context['error'] = f"Error generating quiz: {e}. Check API key and Gemini API status."
            print(f"Error in quiz generation view: {e}")
            import traceback
            traceback.print_exc()

    return render(request, 'quiz/index.html', context)


def check_answers(request: HttpRequest) -> JsonResponse:
    """
    Processes submitted quiz answers (POST request from AJAX).
    Compares submitted answers against the correct answers for the quiz.
    Saves the attempt to the database and returns a JSON response with results.
    """
    if request.method != 'POST':
        return JsonResponse({'error': 'Invalid request method. Use POST.'}, status=405)

    try:
        submitted_data = json.loads(request.body)
        submitted_answers = submitted_data.get('answers')
        quiz_id = submitted_data.get('quiz_id') # Get quiz_id from submitted data
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON data.'}, status=400)

    if not isinstance(submitted_answers, dict):
         return JsonResponse({'error': 'Invalid answers format. Expected a dictionary.'}, status=400)
    if not quiz_id:
         # quiz_id could also be retrieved from session if frontend doesn't send it explicitly
         # quiz_id = request.session.get('current_quiz_id')
         # if not quiz_id:
         return JsonResponse({'error': 'Missing quiz ID.'}, status=400)

    try:
        correct_quiz = Quiz.objects.get(pk=quiz_id)
    except Quiz.DoesNotExist:
        return JsonResponse({'error': 'Quiz not found.'}, status=404)

    correct_questions = correct_quiz.get_questions()
    results = []
    score = 0
    total_questions = len(correct_questions)

    if total_questions == 0:
         return JsonResponse({'error': 'Quiz has no questions.'}, status=400)

    for i, question in enumerate(correct_questions):
        question_key = f"q{i+1}" # e.g., "q1", "q2"
        submitted_answer = submitted_answers.get(question_key)
        correct_answer = question.get('answer') # Answer from the Quiz model's question data
        is_correct = False

        # Compare answers (case-insensitive for fill, exact for others after type conversion)
        if submitted_answer is not None:
            if question['type'] == 'tf':
                # Convert submitted "True"/"False" string to boolean for comparison
                submitted_bool = None
                if isinstance(submitted_answer, str):
                    submitted_bool = submitted_answer.lower() == 'true'
                elif isinstance(submitted_answer, bool): # if JS sends boolean directly
                     submitted_bool = submitted_answer
                is_correct = (submitted_bool is not None and submitted_bool == correct_answer)
            elif question['type'] == 'fill':
                 # Case-insensitive comparison for fill-in-the-blank
                 is_correct = str(submitted_answer).strip().lower() == str(correct_answer).strip().lower()
            else: # mcq
                 # Direct comparison for MCQ (should be exact match)
                 is_correct = str(submitted_answer) == str(correct_answer)

        if is_correct:
            score += 1

        results.append({
            'question_index': i,
            'question_key': question_key,
            'submitted_answer': submitted_answer,
            'correct_answer': correct_answer,
            'is_correct': is_correct,
            'question_text': question.get('question_text', 'N/A') # Include question text for review
        })

    percentage = round((score / total_questions) * 100) if total_questions > 0 else 0

    # Save the quiz attempt
    attempt = QuizAttempt.objects.create(
        quiz=correct_quiz,
        # user=request.user if request.user.is_authenticated else None, # Optional: if you have user auth
        submitted_answers=submitted_answers, # Store the raw submitted answers
        score=score,
        total_questions=total_questions,
        percentage=percentage,
        results_data=results # Store the detailed feedback for each question
    )
    # Store the attempt ID in the session for the email function
    request.session['current_attempt_id'] = attempt.id


    # Prepare JSON response
    response_data = {
        'attempt_id': attempt.id, # Include attempt_id for email functionality
        'score': score,
        'total_questions': total_questions,
        'percentage': percentage,
        'results': results,
        'topic': correct_quiz.topic, # For display on results page
        'difficulty': correct_quiz.difficulty # For display on results page
    }

    return JsonResponse(response_data, status=200)

@csrf_exempt
def send_quiz_email(request: HttpRequest) -> JsonResponse:
    if request.method != 'POST':
        return JsonResponse({'error': 'Invalid request method. Use POST.'}, status=405)

    try:
        data = json.loads(request.body)
        email_address = data.get('email_address')
        attempt_id_from_request = data.get('attempt_id') # Attempt ID is sent from JS
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON data.'}, status=400)

    if not email_address:
        return JsonResponse({'error': 'Email address is required.'}, status=400)
    if not re.match(r"[^@]+@[^@]+\.[^@]+", email_address): # Basic email validation
        return JsonResponse({'error': 'Invalid email address format.'}, status=400)
    
    # Prioritize attempt_id from the request body (sent by JS)
    attempt_id = attempt_id_from_request
    if not attempt_id:
        # Fallback to session if not provided in request (less ideal for stateless API calls)
        attempt_id = request.session.get('current_attempt_id')
        if not attempt_id:
            return JsonResponse({'error': 'Quiz attempt ID is required and was not found in request or session.'}, status=400)
            
    print(f"Attempting to send email for attempt_id: {attempt_id} to {email_address}")

    try:
        # Ensure pk is an integer if it's coming as a string from JSON
        quiz_attempt = get_object_or_404(QuizAttempt, pk=int(attempt_id))
        quiz = quiz_attempt.quiz
    except (QuizAttempt.DoesNotExist, Http404):
        print(f"QuizAttempt with ID {attempt_id} not found.")
        return JsonResponse({'error': 'Quiz attempt not found.'}, status=404)
    except ValueError:
        print(f"Invalid attempt_id format: {attempt_id}")
        return JsonResponse({'error': 'Invalid quiz attempt ID format.'}, status=400)


    subject = f"Your Quiz Results: {quiz.topic}"
    
    email_context = {
        'quiz_topic': quiz.topic,
        'quiz_difficulty': quiz.difficulty,
        'quiz_explanation': quiz.explanation,
        'quiz_questions': quiz.get_questions(), # These are the original questions, not tied to specific attempt answers here
        'quiz_attempt_score': quiz_attempt.score,
        'quiz_attempt_total_questions': quiz_attempt.total_questions,
        'quiz_attempt_percentage': quiz_attempt.percentage,
        'detailed_results': quiz_attempt.get_detailed_results() # These are the specific results of the attempt
    }

    # Render HTML content
    try:
        html_content = render_to_string('quiz/email/quiz_results_email.html', email_context)
    except Exception as e:
        print(f"Error rendering email template: {e}")
        return JsonResponse({'error': 'Failed to render email content.'}, status=500)
    
    # Create a simple plain text version (can be improved or rendered from a .txt template)
    text_content = f"""
    Quiz Results for: {quiz.topic} (Difficulty: {quiz.difficulty})

    Your Score: {quiz_attempt.score}/{quiz_attempt.total_questions} ({quiz_attempt.percentage}%)

    Explanation:
    {quiz.explanation}

    --- Detailed Results ---
    """
    for result in email_context['detailed_results']:
        q_num = result['question_index'] + 1
        q_text = result['question_text']
        submitted = result['submitted_answer'] if result['submitted_answer'] is not None else "Not Answered"
        correct_ans = result['correct_answer']
        # Handle boolean display for True/False questions
        if isinstance(correct_ans, bool):
            correct_ans = "True" if correct_ans else "False"
        status = "Correct" if result['is_correct'] else "Incorrect"
        text_content += f"\nQuestion {q_num}: {q_text}\nYour Answer: {submitted}\nCorrect Answer: {correct_ans}\nStatus: {status}\n---"

    text_content += "\n\nThank you for using Quizify!"


    try:
        print(f"Attempting to send email from: {settings.DEFAULT_FROM_EMAIL} to: {email_address}")
        if not settings.EMAIL_HOST_USER or not settings.EMAIL_HOST_PASSWORD:
            print("Email credentials (EMAIL_HOST_USER or EMAIL_HOST_PASSWORD) are not set in settings.")
            # Depending on policy, either raise error or just log if console backend is active
            if settings.EMAIL_BACKEND != 'django.core.mail.backends.console.EmailBackend':
                 return JsonResponse({'error': 'Email server not configured correctly on the server.'}, status=500)


        msg = EmailMultiAlternatives(
            subject,
            text_content, # Plain text body
            settings.DEFAULT_FROM_EMAIL, # From address
            [email_address] # To address(es)
        )
        msg.attach_alternative(html_content, "text/html") # Attach HTML version
        msg.send()
        
        print(f"Email successfully sent to {email_address} for attempt {attempt_id}.")
        return JsonResponse({'success': True, 'message': f'Quiz results sent to {email_address}.'})
    except Exception as e:
        print(f"Error sending email: {e}")
        import traceback
        traceback.print_exc()
        # Provide a more generic error to the client for security
        return JsonResponse({'error': 'Failed to send email. Please try again later or contact support if the issue persists.'}, status=500)

