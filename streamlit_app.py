
import streamlit as st
import os
import json
import re
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# --- Page Config (Must be the first Streamlit command) ---
st.set_page_config(page_title="Quizify Streamlit", layout="wide", initial_sidebar_state="expanded")

# --- Global Variables & Setup ---
try:
    import google.generativeai as genai_module
    from dotenv import load_dotenv

    load_dotenv()
    GOOGLE_API_KEY = os.environ.get('GOOGLE_API_KEY')
    EMAIL_HOST_USER = os.environ.get('EMAIL_HOST_USER')
    EMAIL_HOST_PASSWORD = os.environ.get('EMAIL_HOST_PASSWORD')


    if GOOGLE_API_KEY:
        genai_module.configure(api_key=GOOGLE_API_KEY)
        genai = genai_module 
    else:
        api_key_warning_message = "GOOGLE_API_KEY not found. AI generation will use placeholders."
except ImportError:
    library_warning_message = "google.generativeai or python-dotenv library not found. AI generation will use placeholders."


# --- Helper Function for AI Generation (adapted from Django views) ---
def generate_quiz_content_st(topic: str, question_type: str, difficulty: str, num_questions: int = 5, num_questions_per_type: dict = None):
    """
    Generates quiz content (explanation and questions) using the Gemini API if available,
    otherwise returns placeholder data. Handles single or mixed question types.
    """
    if not genai or not GOOGLE_API_KEY:
        # Placeholder logic for mixed types
        questions_list = []
        actual_total_questions = 0
        if question_type == 'mixed' and num_questions_per_type:
            for q_type, count in num_questions_per_type.items():
                actual_total_questions += count
                for i in range(count):
                    questions_list.append({
                        'question_text': f"Placeholder {q_type.upper()} Q{i+1} for {topic}?",
                        'type': q_type,
                        'difficulty': difficulty,
                        'answer': "Placeholder Answer" if q_type != 'mcq' else "Option C",
                        'options': ["Option A", "Option B", "Option C", "Option D"] if q_type == 'mcq' else []
                    })
            if not questions_list: # if all counts were 0
                 actual_total_questions = num_questions # fallback to main num_questions for placeholder
                 for idx in range(actual_total_questions):
                    questions_list.append({
                        'question_text': f"Placeholder Q{idx+1} for {topic} (default type)?",
                        'type': 'mcq', 'difficulty': difficulty, 'answer': "Option C",
                        'options': ["Option A", "Option B", "Option C", "Option D"]
                    })

        else: # Single type placeholder
            actual_total_questions = num_questions
            for idx in range(actual_total_questions):
                questions_list.append({
                    'question_text': f"Placeholder Q{idx+1} for {topic} ({question_type})?",
                    'type': question_type,
                    'difficulty': difficulty,
                    'answer': "Placeholder Answer" if question_type != 'mcq' else "Option C",
                    'options': ["Option A", "Option B", "Option C", "Option D"] if question_type == 'mcq' else []
                })
        
        return {
            'topic': topic,
            'difficulty': difficulty,
            'question_type': question_type,
            'content': f"This is a placeholder explanation for the topic: {topic} at {difficulty} level.",
            'questions': questions_list
        }

    model = genai.GenerativeModel('gemini-2.0-flash')
    
    actual_num_questions_for_prompt = num_questions

    prompt_parts = [
        f"""
    Generate educational content about the topic "{topic}" suitable for a "{difficulty}" difficulty level.
    Include the following in your response, formatted STRICTLY as a single JSON object:

    1.  A key "explanation" containing a concise explanation of the topic ({difficulty} level), appropriate for someone learning this topic."""
    ]

    if question_type == 'mixed' and num_questions_per_type:
        actual_num_questions_for_prompt = sum(num_questions_per_type.values())
        if actual_num_questions_for_prompt == 0:
            raise ValueError("For 'mixed' question types, at least one question must be specified for one of the types in Streamlit.")

        prompt_parts.append(f"2.  A key \"questions\" containing a JSON array of exactly {actual_num_questions_for_prompt} questions in total about the topic. The questions array MUST be structured to include:")
        
        question_details_prompt_parts = []
        example_questions_for_prompt = [] 

        if num_questions_per_type.get('mcq', 0) > 0:
            count = num_questions_per_type['mcq']
            question_details_prompt_parts.append(
                f'*   Exactly {count} questions of type "mcq". Each "mcq" question object MUST have: An "options" key with an array of exactly 4 distinct strings, and an "answer" key with the correct option string.'
            )
            example_questions_for_prompt.append(
                """{ "question_text": "Example MCQ...", "type": "mcq", "difficulty": "Easy", "options": ["A", "B", "C", "D"], "answer": "C" }"""
            )
        if num_questions_per_type.get('fill', 0) > 0:
            count = num_questions_per_type['fill']
            question_details_prompt_parts.append(
                f'*   Exactly {count} questions of type "fill". Each "fill" question object MUST have: An "answer" key with the single word or short phrase.'
            )
            example_questions_for_prompt.append(
                """{ "question_text": "Example Fill...", "type": "fill", "difficulty": "Easy", "answer": "Answer" }"""
            )
        if num_questions_per_type.get('tf', 0) > 0:
            count = num_questions_per_type['tf']
            question_details_prompt_parts.append(
                f'*   Exactly {count} questions of type "tf". Each "tf" question object MUST have: An "answer" key with a boolean value (true or false).'
            )
            example_questions_for_prompt.append(
                """{ "question_text": "Example T/F...", "type": "tf", "difficulty": "Easy", "answer": true }"""
            )
        
        prompt_parts.append("\n".join(question_details_prompt_parts))
        prompt_parts.append("""
    Each question object in the array, regardless of its type, MUST also have:
        *   A "question_text" key with the question itself (string).
        *   A "type" key indicating its type (e.g., "mcq", "fill", "tf").
        *   A "difficulty" key with the value "{difficulty}" (string).""")
        if example_questions_for_prompt:
            prompt_parts.append(f"""
    Example structure for "questions" array: [ {", ".join(example_questions_for_prompt)} ]""")

    else: # Single question type
        question_specific_prompt_instruction = ""
        # ... (same as Django's views.py single type prompt details)
        if question_type == 'mcq':
            question_specific_prompt_instruction = """*   For "mcq" type: An "options" key with an array of exactly 4 distinct strings, and an "answer" key with the correct option string."""
        elif question_type == 'fill':
            question_specific_prompt_instruction = """*   For "fill" type: An "answer" key with the single word or short phrase."""
        elif question_type == 'tf':
            question_specific_prompt_instruction = """*   For "tf" type: An "answer" key with a boolean value (true or false)."""

        prompt_parts.append(f"""
    2.  A key "questions" containing a JSON array of exactly {actual_num_questions_for_prompt} questions. Each question object MUST have:
        *   A "question_text" (string). *   A "type": "{question_type}" (string). *   A "difficulty": "{difficulty}" (string).
        {question_specific_prompt_instruction}""")

    prompt_parts.append(f"""
    Ensure the entire output is **only** a single, valid JSON object. The "questions" array must contain exactly {actual_num_questions_for_prompt} items.
    """)
    
    prompt = "\n".join(prompt_parts)

    try:
        response = model.generate_content(
            prompt,
            generation_config=genai.types.GenerationConfig(temperature=0.7)
        )
        raw_text = response.text
        # ... (JSON parsing logic as in Django views.py)
        try:
            generated_data = json.loads(raw_text)
        except json.JSONDecodeError:
            json_match_md = re.search(r'```json\s*(\{.*\})\s*```', raw_text, re.DOTALL | re.IGNORECASE)
            if json_match_md: json_str = json_match_md.group(1)
            else:
                json_match_braces = re.search(r'\{.*\}', raw_text, re.DOTALL)
                if json_match_braces: json_str = json_match_braces.group(0)
                else: raise ValueError(f"Failed to extract JSON. Raw: {raw_text}")
            generated_data = json.loads(json_str)


        if 'explanation' not in generated_data or not isinstance(generated_data['explanation'], str):
            raise ValueError("Generated JSON missing 'explanation'.")
        if 'questions' not in generated_data or not isinstance(generated_data['questions'], list):
            raise ValueError("Generated JSON missing 'questions' list.")
        
        # Validation for mixed types (simplified for Streamlit, detailed logging is better for dev)
        if question_type == "mixed" and num_questions_per_type:
            # Basic check for total count
            if len(generated_data['questions']) != actual_num_questions_for_prompt:
                 st.warning(f"AI returned {len(generated_data['questions'])} total questions for mixed, but {actual_num_questions_for_prompt} were expected. Using returned count.")
        elif question_type != "mixed": # Single type
            if len(generated_data['questions']) != actual_num_questions_for_prompt:
                 st.warning(f"AI returned {len(generated_data['questions'])} questions, but {actual_num_questions_for_prompt} were requested. Using returned count.")

        # Basic structure validation for each question
        for i, q in enumerate(generated_data['questions']):
             if not all(k in q for k in ['question_text', 'type', 'difficulty', 'answer']):
                 raise ValueError(f"Question {i+1} missing required keys.")
             # Further type-specific validation (as in views.py) can be added here if needed.

        result = {
            'topic': topic,
            'difficulty': difficulty,
            'question_type': question_type, # 'mixed' or single type
            'content': generated_data.get('explanation', 'Explanation not generated.'),
            'questions': generated_data.get('questions', [])
        }
        return result

    except Exception as e:
        st.error(f"AI Generation Error (Streamlit): {e}")
        raise Exception(f"An error occurred while communicating with the AI service in Streamlit: {e}") from e


# --- Email Sending Helper Functions (Same as before) ---
def generate_email_html_content_st(quiz_topic, quiz_difficulty, quiz_explanation, score, total_questions, percentage, detailed_results_list):
    html_body = f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Quiz Results: {quiz_topic}</title>
        <style>
            body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; margin: 0; padding: 0; background-color: #f4f4f4; }}
            .container {{ width: 90%; max-width: 600px; margin: 20px auto; background-color: #fff; padding: 20px; border-radius: 8px; box-shadow: 0 0 10px rgba(0,0,0,0.1); }}
            h1, h2, h3 {{ color: #0056b3; }}
            .score-summary {{ background-color: #e9ecef; padding: 15px; border-radius: 5px; margin-bottom: 20px; text-align: center; }}
            .explanation-box {{ background-color: #f9f9f9; padding: 15px; border-left: 4px solid #007bff; margin-bottom: 20px; border-radius: 4px; }}
            .question-item {{ margin-bottom: 20px; padding: 15px; border: 1px solid #ddd; border-radius: 5px; }}
            .question-item.correct {{ border-left: 4px solid #28a745; background-color: #e6ffed; }}
            .question-item.incorrect {{ border-left: 4px solid #dc3545; background-color: #ffebee; }}
            .question-text {{ font-weight: bold; margin-bottom: 10px; }}
            .answer-details span {{ display: inline-block; padding: 3px 8px; border-radius: 4px; font-size: 0.9em; }}
            .submitted-answer {{ background-color: #cfe2ff; }}
            .correct-answer {{ background-color: #d1e7dd; }}
            .result-status {{ font-weight: bold; margin-top: 8px; }}
            .result-status.correct {{ color: #155724; }}
            .result-status.incorrect {{ color: #721c24; }}
        </style>
    </head>
    <body>
        <div class="container">
            <h1>Quiz Results: {quiz_topic}</h1>
            <p>Difficulty: {quiz_difficulty}</p>
            <div class="score-summary">
                <h2>Your Score</h2>
                <p>You scored <strong>{score}</strong> out of <strong>{total_questions}</strong> questions.</p>
                <p>Percentage: <strong>{percentage:.2f}%</strong></p>
            </div>
    """
    if quiz_explanation:
        html_body += f"""
            <h2>Topic Explanation</h2>
            <div class="explanation-box"><p>{quiz_explanation.replace('&lt;br&gt;','<br>')}</p></div>
        """
    html_body += "<h2>Detailed Results</h2>"
    if detailed_results_list:
        for result in detailed_results_list:
            q_text_html = result['question_text'].replace('&lt;br&gt;','<br>') if result['question_text'] else 'N/A'
            submitted_ans_html = result['submitted_answer'] if result['submitted_answer'] is not None else "Not Answered"
            correct_ans_val = result['correct_answer']
            correct_ans_html = "True" if correct_ans_val is True else ("False" if correct_ans_val is False else correct_ans_val)
            
            status_class = "correct" if result['is_correct'] else "incorrect"
            status_text = "Correct!" if result['is_correct'] else "Incorrect"

            html_body += f"""
            <div class="question-item {status_class}">
                <h3>Question {result['question_index'] + 1} ({result.get('type', 'N/A').upper()})</h3>
                <p class="question-text">{q_text_html}</p>
                <div class="answer-details">
                    <p>Your Answer: <span class="submitted-answer">{submitted_ans_html}</span></p>
                    <p>Correct Answer: <span class="correct-answer">{correct_ans_html}</span></p>
                </div>
                <p class="result-status {status_class}">{status_text}</p>
            </div>
            """
    else:
        html_body += "<p>No detailed results available for this attempt.</p>"
    
    html_body += """
            <div style="text-align: center; margin-top: 30px; font-size: 0.9em; color: #777;">
                <p>&copy; Quizify. Keep learning!</p>
            </div>
        </div>
    </body>
    </html>
    """
    return html_body

def generate_email_text_content_st(quiz_topic, quiz_difficulty, quiz_explanation, score, total_questions, percentage, detailed_results_list):
    text_body = f"Quiz Results for: {quiz_topic} (Difficulty: {quiz_difficulty})\n\n"
    text_body += f"Your Score: {score}/{total_questions} ({percentage:.2f}%)\n\n"
    if quiz_explanation:
        text_body += f"Explanation:\n{quiz_explanation}\n\n"
    
    text_body += "--- Detailed Results ---\n"
    if detailed_results_list:
        for result in detailed_results_list:
            q_num = result['question_index'] + 1
            q_type_display = result.get('type', 'N/A').upper()
            q_text = result['question_text'] if result['question_text'] else 'N/A'
            submitted = result['submitted_answer'] if result['submitted_answer'] is not None else "Not Answered"
            correct_ans_val = result['correct_answer']
            correct_ans_text = "True" if correct_ans_val is True else ("False" if correct_ans_val is False else correct_ans_val)
            status = "Correct" if result['is_correct'] else "Incorrect"
            text_body += f"\nQuestion {q_num} ({q_type_display}): {q_text}\nYour Answer: {submitted}\nCorrect Answer: {correct_ans_text}\nStatus: {status}\n---"
    else:
        text_body += "No detailed results available.\n"
        
    text_body += "\n\nThank you for using Quizify!"
    return text_body

def send_quiz_email_st(to_email, quiz_main_data, score, total_questions, percentage, detailed_results_list):
    if not EMAIL_HOST_USER or not EMAIL_HOST_PASSWORD:
        st.error("Email server not configured. Administrator needs to set EMAIL_HOST_USER and EMAIL_HOST_PASSWORD in .env.")
        return False

    subject = f"Your Quiz Results: {quiz_main_data['topic']}"
    from_email = EMAIL_HOST_USER

    html_content = generate_email_html_content_st(
        quiz_main_data['topic'], quiz_main_data['difficulty'], quiz_main_data.get('content'),
        score, total_questions, percentage, detailed_results_list
    )
    text_content = generate_email_text_content_st(
        quiz_main_data['topic'], quiz_main_data['difficulty'], quiz_main_data.get('content'),
        score, total_questions, percentage, detailed_results_list
    )

    msg = MIMEMultipart('alternative')
    msg['Subject'] = subject
    msg['From'] = from_email
    msg['To'] = to_email

    part1 = MIMEText(text_content, 'plain')
    part2 = MIMEText(html_content, 'html')

    msg.attach(part1)
    msg.attach(part2)

    try:
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(EMAIL_HOST_USER, EMAIL_HOST_PASSWORD)
        server.sendmail(from_email, to_email, msg.as_string())
        server.quit()
        st.success(f"Quiz results successfully sent to {to_email}!")
        return True
    except Exception as e:
        st.error(f"Failed to send email: {e}")
        print(f"SMTP Error: {e}") 
        return False


def main():

    st.title("🧙 Quizify - AI Powered Quiz Generator")
    st.markdown("Generate quizzes on any topic using AI!")

    if 'quiz_data' not in st.session_state: st.session_state.quiz_data = None
    if 'submitted_answers' not in st.session_state: st.session_state.submitted_answers = {}
    if 'show_results' not in st.session_state: st.session_state.show_results = False
    if 'current_topic' not in st.session_state: st.session_state.current_topic = ""
    # ... (other session state initializations) ...
    if 'last_quiz_detailed_results' not in st.session_state: st.session_state.last_quiz_detailed_results = []
    if 'last_quiz_score' not in st.session_state: st.session_state.last_quiz_score = 0
    if 'last_quiz_total_questions' not in st.session_state: st.session_state.last_quiz_total_questions = 0
    if 'last_quiz_percentage' not in st.session_state: st.session_state.last_quiz_percentage = 0.0


    with st.sidebar:
        st.header("⚙️ Quiz Configuration")
        with st.form(key="quiz_generation_form_st"):
            topic = st.text_input("Enter Quiz Topic:", value=st.session_state.get('current_topic', "The Solar System"))
            question_type_options_st = {
                'mcq': 'Multiple Choice (MCQ)',
                'fill': 'Fill in the Blank',
                'tf': 'True/False',
                'mixed': 'Mixed Types'
            }
            question_type_display_st = st.selectbox("Select Question Type:", options=list(question_type_options_st.values()), index=0)
            question_type_st = [k for k, v in question_type_options_st.items() if v == question_type_display_st][0]

            num_questions_st = 0
            num_questions_per_type_st_dict = None

            if question_type_st == 'mixed':
                st.markdown("<small>Specify number of questions for each type (total max 20):</small>", unsafe_allow_html=True)
                num_mcq_st = st.number_input("Number of MCQs:", min_value=0, max_value=20, value=2, key="num_mcq_st")
                num_fill_st = st.number_input("Number of Fill-in-the-Blanks:", min_value=0, max_value=20, value=2, key="num_fill_st")
                num_tf_st = st.number_input("Number of True/False:", min_value=0, max_value=20, value=1, key="num_tf_st")
                num_questions_per_type_st_dict = {'mcq': num_mcq_st, 'fill': num_fill_st, 'tf': num_tf_st}
                num_questions_st = num_mcq_st + num_fill_st + num_tf_st
                st.caption(f"Total questions for mixed: {num_questions_st}")
            else:
                num_questions_st = st.number_input("Number of Questions:", min_value=1, max_value=20, value=5, key="num_questions_single_st")

            difficulty_st = st.select_slider("Select Difficulty:", options=['Easy', 'Medium', 'Hard'], value='Medium')
            generate_button_st = st.form_submit_button(label="🚀 Generate Quiz")

        if st.button("🔄 Reset Quiz & Start Over"):
            # ... (reset logic as before) ...
            st.session_state.quiz_data = None
            st.session_state.submitted_answers = {}
            st.session_state.show_results = False
            st.session_state.current_topic = ""
            st.session_state.last_quiz_detailed_results = []
            st.session_state.last_quiz_score = 0
            st.session_state.last_quiz_total_questions = 0
            st.session_state.last_quiz_percentage = 0.0
            st.rerun()


    if generate_button_st:
        if not topic.strip():
            st.error("Please enter a topic for the quiz.")
        elif question_type_st == 'mixed' and num_questions_st == 0:
            st.error("For 'Mixed' type, please specify at least one question for any category (total must be > 0).")
        elif question_type_st == 'mixed' and num_questions_st > 20:
            st.error(f"Total number of questions for 'Mixed' type ({num_questions_st}) cannot exceed 20.")
        elif question_type_st != 'mixed' and not (1 <= num_questions_st <= 20) :
             st.error("Number of questions must be between 1 and 20 for single type.")
        else:
            with st.spinner(f"Generating quiz..."):
                try:
                    st.session_state.quiz_data = generate_quiz_content_st(
                        topic, 
                        question_type_st, 
                        difficulty_st, 
                        num_questions=num_questions_st, # Total for mixed, or count for single
                        num_questions_per_type=num_questions_per_type_st_dict if question_type_st == 'mixed' else None
                    )
                    if not genai or not GOOGLE_API_KEY:
                        st.info("Displaying placeholder quiz data.")
                    
                    if not st.session_state.quiz_data or not st.session_state.quiz_data.get('questions'):
                         st.warning("The AI (or placeholder) did not return any questions.")
                    
                    st.session_state.submitted_answers = {} 
                    st.session_state.show_results = False 
                    st.session_state.current_topic = topic 
                    st.success("Quiz generated!")
                except Exception as e:
                    st.error(f"Failed to generate quiz: {e}")
                    st.session_state.quiz_data = None


    if st.session_state.quiz_data:
        quiz = st.session_state.quiz_data
        display_question_type = question_type_options_st.get(quiz['question_type'], quiz['question_type'].capitalize())
        st.header(f"📜 Quiz on: {quiz['topic']}")
        st.subheader(f"Difficulty: {quiz['difficulty']} | Type: {display_question_type}")

        with st.expander("💡 Topic Explanation", expanded=True):
            st.markdown(quiz.get('content', 'No explanation provided.'))

        st.markdown("---")
        st.subheader("❓ Questions")

        if not quiz['questions']:
            st.warning("No questions were generated.")
        else:
            user_answers_form_st = st.form(key="user_answers_form_st")
            for i, q in enumerate(quiz['questions']):
                question_key_st = f"q_st_{i}"
                q_type_display_item = q.get('type', 'N/A').upper()
                user_answers_form_st.markdown(f"**Question {i+1} ({q_type_display_item}):** {q['question_text']}")

                if q['type'] == 'mcq':
                    options_st = q.get('options', [])
                    st.session_state.submitted_answers[question_key_st] = user_answers_form_st.radio(
                        "Your answer:", options_st, key=question_key_st, index=None
                    ) if options_st else user_answers_form_st.markdown("_MCQ options missing._")
                elif q['type'] == 'fill':
                    st.session_state.submitted_answers[question_key_st] = user_answers_form_st.text_input(
                        "Your answer:", key=question_key_st
                    )
                elif q['type'] == 'tf':
                    st.session_state.submitted_answers[question_key_st] = user_answers_form_st.radio(
                        "Your answer:", ["True", "False"], key=question_key_st, index=None
                    )
                else:
                     user_answers_form_st.markdown(f"_Unsupported question type: {q.get('type', 'Unknown')}_")
                     st.session_state.submitted_answers[question_key_st] = None
                user_answers_form_st.markdown("---")

            submit_answers_button_st = user_answers_form_st.form_submit_button("✅ Submit Answers")

            if submit_answers_button_st:
                st.session_state.show_results = True
                current_score = 0
                current_total_questions = len(quiz['questions'])
                current_detailed_results = []

                for i_res, q_res in enumerate(quiz['questions']):
                    q_key_res = f"q_st_{i_res}"
                    submitted_ans_res = st.session_state.submitted_answers.get(q_key_res)
                    correct_ans_res = q_res.get('answer')
                    res_is_correct = False
                    # ... (answer checking logic as before) ...
                    if submitted_ans_res is not None:
                        if q_res['type'] == 'tf':
                            submitted_bool_res = str(submitted_ans_res).lower() == 'true'
                            res_is_correct = (submitted_bool_res == correct_ans_res)
                        elif q_res['type'] == 'fill':
                            res_is_correct = str(submitted_ans_res).strip().lower() == str(correct_ans_res).strip().lower()
                        else: # mcq
                            res_is_correct = str(submitted_ans_res) == str(correct_ans_res)
                    if res_is_correct:
                        current_score += 1
                    
                    current_detailed_results.append({
                        'question_index': i_res,
                        'question_text': q_res['question_text'],
                        'submitted_answer': submitted_ans_res,
                        'correct_answer': correct_ans_res,
                        'is_correct': res_is_correct,
                        'type': q_res.get('type', 'N/A') # Store type for email display
                    })
                st.session_state.last_quiz_score = current_score
                st.session_state.last_quiz_total_questions = current_total_questions
                st.session_state.last_quiz_percentage = (current_score / current_total_questions * 100) if current_total_questions > 0 else 0
                st.session_state.last_quiz_detailed_results = current_detailed_results


        if st.session_state.show_results and quiz['questions']:
            st.markdown("---"); st.header("📊 Quiz Results")
            # ... (results display logic as before, ensuring q_type_display_item is used for question type) ...
            detailed_results_to_display = st.session_state.last_quiz_detailed_results
            for result_item in detailed_results_to_display:
                with st.container():
                    q_type_display_item_res = result_item.get('type', 'N/A').upper()
                    st.markdown(f"**Question {result_item['question_index'] + 1} ({q_type_display_item_res}):** {result_item['question_text']}")
                    # ... rest of result item display ...
                    submitted_display = result_item['submitted_answer'] if result_item['submitted_answer'] is not None else 'Not Answered'
                    st.write(f"Your answer: `{submitted_display}`")
                    correct_ans_display_val = result_item['correct_answer']
                    correct_ans_display_text = "True" if correct_ans_display_val is True else ("False" if correct_ans_display_val is False else correct_ans_display_val)
                    if result_item['is_correct']: st.success(f"Correct! The answer is `{correct_ans_display_text}`.")
                    else: st.error(f"Incorrect. The correct answer is `{correct_ans_display_text}`.")
                st.markdown("---")
            
            st.subheader(f"🏆 Your Final Score: {st.session_state.last_quiz_score}/{st.session_state.last_quiz_total_questions}")
            st.progress(int(st.session_state.last_quiz_percentage))
            st.markdown(f"Percentage: **{st.session_state.last_quiz_percentage:.2f}%**")
            # ... (balloons, messages logic) ...

            st.markdown("---"); st.subheader("📧 Share Your Results via Email")
            if not EMAIL_HOST_USER or not EMAIL_HOST_PASSWORD:
                 st.warning("Email sending not configured.")
            else:
                email_address_st_send = st.text_input("Enter email:", key="email_results_input_st_send")
                if st.button("✉️ Send Email", key="send_email_button_st_send"):
                    if not email_address_st_send or not re.match(r"[^@]+@[^@]+\.[^@]+", email_address_st_send):
                        st.error("Invalid email address.")
                    else:
                        if st.session_state.quiz_data:
                            with st.spinner("Sending..."):
                                send_quiz_email_st(
                                    email_address_st_send, st.session_state.quiz_data,
                                    st.session_state.last_quiz_score, st.session_state.last_quiz_total_questions,
                                    st.session_state.last_quiz_percentage, st.session_state.last_quiz_detailed_results
                                )
                        else: st.error("No results to send.")
    else:
        st.info("Configure quiz in sidebar & click 'Generate Quiz'.")
        st.markdown("### How to use:\n1. Enter Topic, Type, Difficulty, Number of Questions.\n2. Click Generate Quiz!\nGood luck! 🍀")

    st.markdown("---"); st.caption("Quizify Streamlit App")

if __name__ == '__main__':
    main()
