
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

# --- Helper Function for AI Generation ---
def generate_quiz_content(topic: str, question_type: str, difficulty: str, num_questions: int = 5, num_questions_per_type: dict = None):
    """
    Generates quiz content (explanation and questions) using the Gemini API.
    Can handle single question type or a mix of types if question_type is 'mixed'.
    """
    api_key = settings.GOOGLE_GENAI_API_KEY
    if not api_key:
        print("Error: GOOGLE_API_KEY not found in settings.")
        raise ValueError("Google API Key not configured.")

    genai.configure(api_key=api_key)
    model = "gemini-2.0-flash"

    type_map_display = {
        'mcq': 'Multiple Choice (MCQ)',
        'fill': 'Fill in the Blank',
        'tf': 'True/False'
    }
    
    actual_num_questions = num_questions # This will be the total number of questions

    prompt_parts = [
        f"""
    Generate educational content about the topic "{topic}" suitable for a "{difficulty}" difficulty level.
    Include the following in your response, formatted STRICTLY as a single JSON object:

    1.  A key "explanation" containing a concise explanation of the topic ({difficulty} level), appropriate for someone learning this topic."""
    ]

    if question_type == 'mixed' and num_questions_per_type:
        actual_num_questions = sum(num_questions_per_type.values())
        if actual_num_questions == 0:
            raise ValueError("For 'mixed' question types, at least one question must be specified for one of the types.")

        prompt_parts.append(f"2.  A key \"questions\" containing a JSON array of exactly {actual_num_questions} questions in total about the topic. The questions array MUST be structured to include:")
        
        question_details_prompt_parts = []
        example_questions_for_prompt = [] # For the example section

        if num_questions_per_type.get('mcq', 0) > 0:
            count = num_questions_per_type['mcq']
            question_details_prompt_parts.append(
                f'*   Exactly {count} questions of type "mcq". Each "mcq" question object MUST have: An "options" key with an array of exactly 4 distinct strings, and an "answer" key with the correct option string (must exactly match one of the options).'
            )
            example_questions_for_prompt.append(
                """{ "question_text": "Example MCQ: What is 2+2?", "type": "mcq", "difficulty": "Easy", "options": ["3", "4", "5", "6"], "answer": "4" }"""
            )
        if num_questions_per_type.get('fill', 0) > 0:
            count = num_questions_per_type['fill']
            question_details_prompt_parts.append(
                f'*   Exactly {count} questions of type "fill". Each "fill" question object MUST have: An "answer" key with the single word or short phrase (string) that correctly fills the blank.'
            )
            example_questions_for_prompt.append(
                """{ "question_text": "Example Fill: The capital of France is ____.", "type": "fill", "difficulty": "Easy", "answer": "Paris" }"""
            )
        if num_questions_per_type.get('tf', 0) > 0:
            count = num_questions_per_type['tf']
            question_details_prompt_parts.append(
                f'*   Exactly {count} questions of type "tf". Each "tf" question object MUST have: An "answer" key with a boolean value (true or false).'
            )
            example_questions_for_prompt.append(
                """{ "question_text": "Example T/F: The sky is green.", "type": "tf", "difficulty": "Easy", "answer": false }"""
            )
        
        prompt_parts.append("\n".join(question_details_prompt_parts))
        prompt_parts.append("""
    Each question object in the array, regardless of its type, MUST also have:
        *   A "question_text" key with the question itself (string).
        *   A "type" key indicating its type (e.g., "mcq", "fill", "tf").
        *   A "difficulty" key with the value "{difficulty}" (string).""")

        if example_questions_for_prompt:
            prompt_parts.append(f"""
    Example structure for the "questions" array:
    "questions": [
      {", ".join(example_questions_for_prompt)}
    ]""")

    else: # Single question type
        question_specific_prompt_instruction = ""
        if question_type == 'mcq':
            question_specific_prompt_instruction = """
            *   For "mcq" type: An "options" key with an array of exactly 4 distinct strings (potential answers), and an "answer" key with the correct option string (must exactly match one of the options).
            Example for MCQ:
            {{
              "question_text": "What is the powerhouse of the cell?", "type": "mcq", "difficulty": "Easy",
              "options": ["Nucleus", "Ribosome", "Mitochondrion", "Chloroplast"], "answer": "Mitochondrion"
            }}"""
        elif question_type == 'fill':
            question_specific_prompt_instruction = """
            *   For "fill" type: An "answer" key with the single word or short phrase (string) that correctly fills the blank (often indicated by '____' in the question_text). The answer should be concise.
            Example for Fill in the Blank:
            {{
              "question_text": "The chemical symbol for water is ____.", "type": "fill", "difficulty": "Easy", "answer": "H2O"
            }}"""
        elif question_type == 'tf':
            question_specific_prompt_instruction = """
            *   For "tf" type: An "answer" key with the boolean value true or false (not the string "true" or "false").
            Example for True/False:
            {{
              "question_text": "The sun revolves around the Earth.", "type": "tf", "difficulty": "Easy", "answer": false
            }}"""
        
        prompt_parts.append(f"""
    2.  A key "questions" containing a JSON array of exactly {actual_num_questions} questions about the topic. Each question object in the array MUST have:
        *   A "question_text" key with the question itself (string).
        *   A "type" key with the value "{question_type}" (string).
        *   A "difficulty" key with the value "{difficulty}" (string).
        {question_specific_prompt_instruction}""")

    prompt_parts.append(f"""
    Ensure the entire output is **only** a single, valid JSON object starting with {{ and ending with }}. Do not include any text, explanations, or markdown formatting like ```json before or after the JSON object itself. The "questions" array must contain exactly {actual_num_questions} items in total, matching the specified counts for each type if 'mixed' type was requested.
    """)
    
    prompt = "\n".join(prompt_parts)

    try:
        response = client.models.generate_content(model=model, contents=prompt)
        raw_text = response.text
        try:
            generated_data = json.loads(raw_text)
        except json.JSONDecodeError:
            json_match_md = re.search(r'```json\s*(\{.*\})\s*```', raw_text, re.DOTALL | re.IGNORECASE)
            if json_match_md:
                json_str = json_match_md.group(1)
            else:
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

        if 'explanation' not in generated_data or not isinstance(generated_data['explanation'], str):
            raise ValueError("Generated JSON is missing 'explanation' key or it's not a string.")
        if 'questions' not in generated_data or not isinstance(generated_data['questions'], list):
            raise ValueError("Generated JSON is missing 'questions' key or it's not a list.")
        
        # Validate number of questions returned vs requested
        if question_type == "mixed" and num_questions_per_type:
            type_counts_returned = {'mcq': 0, 'fill': 0, 'tf': 0}
            for q_gen in generated_data['questions']:
                q_gen_type = q_gen.get('type')
                if q_gen_type in type_counts_returned:
                    type_counts_returned[q_gen_type] += 1
            
            valid_mix = True
            for q_type_req, count_req in num_questions_per_type.items():
                if count_req > 0 and type_counts_returned.get(q_type_req, 0) != count_req:
                    print(f"Warning: AI returned {type_counts_returned.get(q_type_req, 0)} '{q_type_req}' questions, but {count_req} were requested.")
                    # valid_mix = False # Decided to proceed with what AI returned, but log warning
            
            if len(generated_data['questions']) != actual_num_questions:
                 print(f"Warning: AI returned {len(generated_data['questions'])} total questions for mixed type, but {actual_num_questions} were expected. Using the {len(generated_data['questions'])} questions returned by the AI.")
        elif question_type != "mixed":
            if len(generated_data['questions']) != actual_num_questions:
                 print(f"Warning: AI returned {len(generated_data['questions'])} questions, but {actual_num_questions} were requested for single type. Using the {len(generated_data['questions'])} questions returned by the AI.")

        for i, q in enumerate(generated_data['questions']):
             if not all(k in q for k in ['question_text', 'type', 'difficulty', 'answer']):
                 raise ValueError(f"Question {i+1} is missing required keys (question_text, type, difficulty, answer).")
             q_type_from_ai = q.get('type')
             if q_type_from_ai == 'mcq' and (not isinstance(q.get('options'), list) or len(q['options']) != 4 or q.get('answer') not in q['options']):
                 raise ValueError(f"MCQ Question {i+1} (text: {q.get('question_text')[:50]}...) has invalid 'options' or 'answer'. Options must be a list of 4 strings, and answer must match one option.")
             if q_type_from_ai == 'tf' and not isinstance(q.get('answer'), bool):
                 if isinstance(q.get('answer'), str):
                     if q['answer'].lower() == 'true': q['answer'] = True
                     elif q['answer'].lower() == 'false': q['answer'] = False
                     else: raise ValueError(f"True/False Question {i+1} (text: {q.get('question_text')[:50]}...) has non-boolean answer: {q['answer']}.")
                 else: raise ValueError(f"True/False Question {i+1} (text: {q.get('question_text')[:50]}...) has non-boolean answer: {q['answer']}.")
             # Ensure the type in the question matches what was expected if single type, or is one of the mixed types.
             if question_type != 'mixed' and q_type_from_ai != question_type:
                 raise ValueError(f"Question {i+1} has type '{q_type_from_ai}' but '{question_type}' was expected.")
             elif question_type == 'mixed' and q_type_from_ai not in num_questions_per_type:
                 raise ValueError(f"Question {i+1} has unexpected type '{q_type_from_ai}' for mixed request.")


        result = {
            'topic': topic,
            'difficulty': difficulty,
            'question_type': question_type, # This is the overall request type ('mixed' or single)
            'num_questions_requested_details': num_questions_per_type if question_type == 'mixed' else {question_type: actual_num_questions},
            'content': generated_data.get('explanation', 'Explanation not generated.'),
            'questions': generated_data.get('questions', [])
        }
        return result

    except json.JSONDecodeError as e:
        print(f"Error decoding JSON response: {e}")
        print(f"Raw response text was:\n{response.text if 'response' in locals() else 'No response object'}")
        raise ValueError(f"Failed to parse the AI's response as valid JSON. Check the Gemini API response format. Error: {e}") from e
    except Exception as e:
        print(f"An unexpected error occurred during AI generation: {e}")
        import traceback
        traceback.print_exc() 
        raise Exception(f"An error occurred while communicating with the AI service: {e}") from e


# --- Django Views ---

def index(request: HttpRequest) -> HttpResponse:
    context = {'form_data': {}} 

    if request.method == 'POST':
        topic = request.POST.get('topic', '').strip()
        question_type = request.POST.get('question_type')
        difficulty = request.POST.get('difficulty')
        
        num_questions = 0
        num_questions_per_type_dict = None

        # Store form data to repopulate
        context['form_data'] = {
            'topic': topic,
            'question_type': question_type,
            'difficulty': difficulty,
        }

        if question_type == 'mixed':
            try:
                num_mcq = int(request.POST.get('num_mcq', '0'))
                num_fill = int(request.POST.get('num_fill', '0'))
                num_tf = int(request.POST.get('num_tf', '0'))

                if not (num_mcq >= 0 and num_fill >= 0 and num_tf >= 0):
                    raise ValueError("Number of questions for each type must be non-negative.")
                
                num_questions_per_type_dict = {'mcq': num_mcq, 'fill': num_fill, 'tf': num_tf}
                num_questions = num_mcq + num_fill + num_tf

                if num_questions == 0:
                    raise ValueError("For 'Mixed' type, please specify at least one question for any category.")
                if num_questions > 20: # Overall limit for mixed
                     raise ValueError("Total number of questions for 'Mixed' type cannot exceed 20.")


                context['form_data'].update({
                    'num_mcq': num_mcq,
                    'num_fill': num_fill,
                    'num_tf': num_tf,
                })
            except ValueError as ve:
                context['error'] = str(ve)
                return render(request, 'quiz/index.html', context)
        else: # Single question type
            num_questions_str = request.POST.get('num_questions', '5')
            try:
                num_questions = int(num_questions_str)
                if not (1 <= num_questions <= 20):
                    raise ValueError("Number of questions must be between 1 and 20.")
                context['form_data']['num_questions'] = num_questions
            except ValueError as ve:
                context['error'] = str(ve)
                return render(request, 'quiz/index.html', context)


        if not topic or not question_type or not difficulty:
            errors = []
            if not topic: errors.append("Please enter a topic.")
            if not question_type: errors.append("Please select a question type.")
            if not difficulty: errors.append("Please select a difficulty level.")
            current_error = context.get('error', '')
            context['error'] = (current_error + " " if current_error else "") + " ".join(errors)
            return render(request, 'quiz/index.html', context)
        
        if context.get('error'): # If any validation error occurred before this point
             return render(request, 'quiz/index.html', context)

        try:
            quiz_data = generate_quiz_content(
                topic, 
                question_type, 
                difficulty, 
                num_questions=num_questions, # This is total for mixed, or specific for single
                num_questions_per_type=num_questions_per_type_dict if question_type == 'mixed' else None
            )

            new_quiz = Quiz.objects.create(
                topic=quiz_data['topic'],
                difficulty=quiz_data['difficulty'],
                question_type=quiz_data['question_type'], # Stores 'mixed' or the single type
                explanation=quiz_data['content'],
                questions_data=quiz_data['questions']
            )
            request.session['current_quiz_id'] = new_quiz.id

            context['quiz_result'] = {
                'quiz_id': new_quiz.id,
                'topic': new_quiz.topic,
                'difficulty': new_quiz.difficulty,
                'question_type_display': 'Mixed Types' if new_quiz.question_type == 'mixed' else dict(Quiz.QUESTION_TYPE_CHOICES).get(new_quiz.question_type, new_quiz.question_type.capitalize()),
                'content': new_quiz.explanation,
                'questions': new_quiz.get_questions() 
            }

        except ValueError as ve:
             context['error'] = f"Generation Error: {ve}"
        except Exception as e:
            context['error'] = f"Error generating quiz: {e}. Check API key and Gemini API status."
            print(f"Error in quiz generation view: {e}")
            import traceback
            traceback.print_exc()

    return render(request, 'quiz/index.html', context)


def check_answers(request: HttpRequest) -> JsonResponse:
    if request.method != 'POST':
        return JsonResponse({'error': 'Invalid request method. Use POST.'}, status=405)

    try:
        submitted_data = json.loads(request.body)
        submitted_answers = submitted_data.get('answers')
        quiz_id = submitted_data.get('quiz_id') 
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON data.'}, status=400)

    if not isinstance(submitted_answers, dict):
         return JsonResponse({'error': 'Invalid answers format. Expected a dictionary.'}, status=400)
    if not quiz_id:
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
        question_key = f"q{i+1}" 
        submitted_answer = submitted_answers.get(question_key)
        correct_answer = question.get('answer') 
        is_correct = False

        if submitted_answer is not None:
            if question['type'] == 'tf':
                submitted_bool = None
                if isinstance(submitted_answer, str):
                    submitted_bool = submitted_answer.lower() == 'true'
                elif isinstance(submitted_answer, bool): 
                     submitted_bool = submitted_answer
                is_correct = (submitted_bool is not None and submitted_bool == correct_answer)
            elif question['type'] == 'fill':
                 is_correct = str(submitted_answer).strip().lower() == str(correct_answer).strip().lower()
            else: # mcq
                 is_correct = str(submitted_answer) == str(correct_answer)

        if is_correct:
            score += 1

        results.append({
            'question_index': i,
            'question_key': question_key,
            'submitted_answer': submitted_answer,
            'correct_answer': correct_answer,
            'is_correct': is_correct,
            'question_text': question.get('question_text', 'N/A') 
        })

    percentage = round((score / total_questions) * 100) if total_questions > 0 else 0

    attempt = QuizAttempt.objects.create(
        quiz=correct_quiz,
        submitted_answers=submitted_answers, 
        score=score,
        total_questions=total_questions,
        percentage=percentage,
        results_data=results 
    )
    request.session['current_attempt_id'] = attempt.id


    response_data = {
        'attempt_id': attempt.id, 
        'score': score,
        'total_questions': total_questions,
        'percentage': percentage,
        'results': results,
        'topic': correct_quiz.topic, 
        'difficulty': correct_quiz.difficulty 
    }

    return JsonResponse(response_data, status=200)


def send_quiz_email(request: HttpRequest) -> JsonResponse:
    if request.method != 'POST':
        return JsonResponse({'error': 'Invalid request method. Use POST.'}, status=405)

    try:
        data = json.loads(request.body)
        email_address = data.get('email_address')
        attempt_id_from_request = data.get('attempt_id') 
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON data.'}, status=400)

    if not email_address:
        return JsonResponse({'error': 'Email address is required.'}, status=400)
    if not re.match(r"[^@]+@[^@]+\.[^@]+", email_address): 
        return JsonResponse({'error': 'Invalid email address format.'}, status=400)
    
    attempt_id = attempt_id_from_request
    if not attempt_id:
        attempt_id = request.session.get('current_attempt_id')
        if not attempt_id:
            return JsonResponse({'error': 'Quiz attempt ID is required and was not found in request or session.'}, status=400)
            
    print(f"Attempting to send email for attempt_id: {attempt_id} to {email_address}")

    try:
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
        'quiz_questions': quiz.get_questions(), 
        'quiz_attempt_score': quiz_attempt.score,
        'quiz_attempt_total_questions': quiz_attempt.total_questions,
        'quiz_attempt_percentage': quiz_attempt.percentage,
        'detailed_results': quiz_attempt.get_detailed_results() 
    }

    try:
        html_content = render_to_string('quiz/email/quiz_results_email.html', email_context)
    except Exception as e:
        print(f"Error rendering email template: {e}")
        return JsonResponse({'error': 'Failed to render email content.'}, status=500)
    
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
        if isinstance(correct_ans, bool):
            correct_ans = "True" if correct_ans else "False"
        status = "Correct" if result['is_correct'] else "Incorrect"
        text_content += f"\nQuestion {q_num}: {q_text}\nYour Answer: {submitted}\nCorrect Answer: {correct_ans}\nStatus: {status}\n---"
    text_content += "\n\nThank you for using Quizify!"

    try:
        print(f"Attempting to send email from: {settings.DEFAULT_FROM_EMAIL} to: {email_address}")
        if not settings.EMAIL_HOST_USER or not settings.EMAIL_HOST_PASSWORD:
            print("Email credentials (EMAIL_HOST_USER or EMAIL_HOST_PASSWORD) are not set in settings.")
            if settings.EMAIL_BACKEND != 'django.core.mail.backends.console.EmailBackend':
                 return JsonResponse({'error': 'Email server not configured correctly on the server.'}, status=500)

        msg = EmailMultiAlternatives(
            subject,
            text_content, 
            settings.DEFAULT_FROM_EMAIL, 
            [email_address] 
        )
        msg.attach_alternative(html_content, "text/html") 
        msg.send()
        
        print(f"Email successfully sent to {email_address} for attempt {attempt_id}.")
        return JsonResponse({'success': True, 'message': f'Quiz results sent to {email_address}.'})
    except Exception as e:
        print(f"Error sending email: {e}")
        import traceback
        traceback.print_exc()
        return JsonResponse({'error': 'Failed to send email. Please try again later or contact support if the issue persists.'}, status=500)
