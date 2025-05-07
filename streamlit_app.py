
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

# Attempt to import google.generativeai, but handle if not available or API key is missing
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
         # Assign to global genai
    else:
        api_key_warning_message = "GOOGLE_API_KEY not found. AI generation will use placeholders."
        # genai remains None
except ImportError:
    library_warning_message = "google.generativeai or python-dotenv library not found. AI generation will use placeholders."
    # genai remains None


# --- Helper Function for AI Generation (adapted from Django views) ---
def generate_quiz_content_st(topic: str, question_type: str, difficulty: str, num_questions: int = 5):
    """
    Generates quiz content (explanation and questions) using the Gemini API if available,
    otherwise returns placeholder data.
    """
    if not genai_module or not GOOGLE_API_KEY:
        # Placeholder data if API key or library is not available
        # We'll display warnings in the main app flow, not here, to avoid early Streamlit calls.
        # st.info("Using placeholder data as Google API Key or genai library is not configured.")
        return {
            'topic': topic,
            'difficulty': difficulty,
            'question_type': question_type,
            'content': f"This is a placeholder explanation for the topic: {topic} at {difficulty} level.",
            'questions': [
                {
                    'question_text': f"Placeholder Q1 for {topic} ({question_type})?",
                    'type': question_type,
                    'difficulty': difficulty,
                    'answer': "Placeholder Answer 1" if question_type != 'mcq' else "Option C",
                    'options': ["Option A", "Option B", "Option C", "Option D"] if question_type == 'mcq' else []
                }
                for _ in range(num_questions)
            ]
        }

    #model = 'gemini-2.0-flash'
    model = genai.GenerativeModel('gemini-2.0-flash')

    type_map = {
        'mcq': 'Multiple Choice (MCQ)',
        'fill': 'Fill in the Blank',
        'tf': 'True/False'
    }

    question_specific_prompt_instruction = ""
    if question_type == 'mcq':
        question_specific_prompt_instruction = """
        *   For "mcq" type: An "options" key with an array of exactly 4 distinct strings (potential answers), and an "answer" key with the correct option string (must exactly match one of the options).
        Example for MCQ:
        {
          "question_text": "What is the powerhouse of the cell?",
          "type": "mcq",
          "difficulty": "Easy",
          "options": ["Nucleus", "Ribosome", "Mitochondrion", "Chloroplast"],
          "answer": "Mitochondrion"
        }"""
    elif question_type == 'fill':
        question_specific_prompt_instruction = """
        *   For "fill" type: An "answer" key with the single word or short phrase (string) that correctly fills the blank (often indicated by '____' in the question_text). The answer should be concise.
        Example for Fill in the Blank:
        {
          "question_text": "The chemical symbol for water is ____.",
          "type": "fill",
          "difficulty": "Easy",
          "answer": "H2O"
        }"""
    elif question_type == 'tf':
        question_specific_prompt_instruction = """
        *   For "tf" type: An "answer" key with the boolean value true or false (not the string "true" or "false").
        Example for True/False:
        {
          "question_text": "The sun revolves around the Earth.",
          "type": "tf",
          "difficulty": "Easy",
          "answer": false
        }"""

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
        response = model.generate_content(
            prompt,
            generation_config=genai.types.GenerationConfig(temperature=0.7)
        )
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
                    # Use st.error inside the main app flow if this function is called from there
                    # For now, raise ValueError which will be caught
                    raise ValueError(f"Failed to extract JSON. Raw response:\n{raw_text}")
            try:
                generated_data = json.loads(json_str)
            except json.JSONDecodeError as e:
                raise ValueError(f"Error decoding cleaned JSON: {e}\nCleaned JSON string was:\n{json_str}\nOriginal raw response was:\n{raw_text}") from e

        if 'explanation' not in generated_data or not isinstance(generated_data['explanation'], str):
            raise ValueError("Generated JSON is missing 'explanation' key or it's not a string.")
        if 'questions' not in generated_data or not isinstance(generated_data['questions'], list):
            raise ValueError("Generated JSON is missing 'questions' key or it's not a list.")
        
        if len(generated_data['questions']) != num_questions:
             # st.warning can be called in the main flow if this function returns a flag or specific error
             print(f"Warning: AI returned {len(generated_data['questions'])} questions, but {num_questions} were requested.")


        for i, q in enumerate(generated_data['questions']):
             if not all(k in q for k in ['question_text', 'type', 'difficulty', 'answer']):
                 raise ValueError(f"Question {i+1} is missing required keys (question_text, type, difficulty, answer).")
             if q['type'] == 'mcq' and (not isinstance(q.get('options'), list) or len(q['options']) != 4 or q.get('answer') not in q['options']):
                 raise ValueError(f"MCQ Question {i+1} has invalid 'options' or 'answer'. Options must be a list of 4 strings, and answer must match one option.")
             if q['type'] == 'tf' and not isinstance(q.get('answer'), bool):
                 if isinstance(q.get('answer'), str):
                     if q['answer'].lower() == 'true': q['answer'] = True
                     elif q['answer'].lower() == 'false': q['answer'] = False
                     else: raise ValueError(f"True/False Question {i+1} has non-boolean answer: {q['answer']}.")
                 else: raise ValueError(f"True/False Question {i+1} has non-boolean answer: {q['answer']}.")

        result = {
            'topic': topic,
            'difficulty': difficulty,
            'question_type': question_type,
            'content': generated_data.get('explanation', 'Explanation not generated.'),
            'questions': generated_data.get('questions', [])
        }
        return result

    except Exception as e:
        # st.error(f"An unexpected error occurred during AI generation: {e}") # Call in main flow
        # Re-raise a more generic error to the view
        raise Exception(f"An error occurred while communicating with the AI service: {e}") from e

# --- Email Sending Helper Functions ---
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
            <div class="explanation-box"><p>{quiz_explanation.replace  ('&lt;br&gt;','<br>')}</p></div>
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
                <h3>Question {result['question_index'] + 1}</h3>
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
            q_text = result['question_text'] if result['question_text'] else 'N/A'
            submitted = result['submitted_answer'] if result['submitted_answer'] is not None else "Not Answered"
            correct_ans_val = result['correct_answer']
            correct_ans_text = "True" if correct_ans_val is True else ("False" if correct_ans_val is False else correct_ans_val)
            status = "Correct" if result['is_correct'] else "Incorrect"
            text_body += f"\nQuestion {q_num}: {q_text}\nYour Answer: {submitted}\nCorrect Answer: {correct_ans_text}\nStatus: {status}\n---"
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
        print(f"SMTP Error: {e}") # Log to console for debugging
        return False


def main():
    # Display warnings if API key or library issues were detected during startup
    if library_warning_message:
        st.warning(library_warning_message)
    if api_key_warning_message:
        st.warning(api_key_warning_message)
    if not genai or not GOOGLE_API_KEY: # Additional check for clarity
        st.info("AI features will use placeholder data due to missing configuration.")

    st.title("🧙 Quizify - AI Powered Quiz Generator")
    st.markdown("Generate quizzes on any topic using AI!")

    # Initialize session state
    if 'quiz_data' not in st.session_state:
        st.session_state.quiz_data = None
    if 'submitted_answers' not in st.session_state:
        st.session_state.submitted_answers = {}
    if 'show_results' not in st.session_state:
        st.session_state.show_results = False
    if 'current_topic' not in st.session_state:
        st.session_state.current_topic = ""
    if 'last_quiz_detailed_results' not in st.session_state:
        st.session_state.last_quiz_detailed_results = []
    if 'last_quiz_score' not in st.session_state:
        st.session_state.last_quiz_score = 0
    if 'last_quiz_total_questions' not in st.session_state:
        st.session_state.last_quiz_total_questions = 0
    if 'last_quiz_percentage' not in st.session_state:
        st.session_state.last_quiz_percentage = 0.0


    with st.sidebar:
        st.header("⚙️ Quiz Configuration")
        with st.form(key="quiz_generation_form"):
            topic = st.text_input("Enter Quiz Topic:", value=st.session_state.get('current_topic', "The Solar System"))
            question_type_options = {
                'mcq': 'Multiple Choice (MCQ)',
                'fill': 'Fill in the Blank',
                'tf': 'True/False'
            }
            question_type_display = st.selectbox("Select Question Type:", options=list(question_type_options.values()), index=0)
            question_type = [k for k, v in question_type_options.items() if v == question_type_display][0]

            difficulty = st.select_slider("Select Difficulty:", options=['Easy', 'Medium', 'Hard'], value='Medium')
            num_questions = st.number_input("Number of Questions:", min_value=1, max_value=20, value=5)
            generate_button = st.form_submit_button(label="🚀 Generate Quiz")

        if st.button("🔄 Reset Quiz & Start Over"):
            st.session_state.quiz_data = None
            st.session_state.submitted_answers = {}
            st.session_state.show_results = False
            st.session_state.current_topic = ""
            st.session_state.last_quiz_detailed_results = []
            st.session_state.last_quiz_score = 0
            st.session_state.last_quiz_total_questions = 0
            st.session_state.last_quiz_percentage = 0.0
            st.rerun()


    if generate_button:
        if not topic.strip():
            st.error("Please enter a topic for the quiz.")
        else:
            with st.spinner(f"Generating {difficulty} {question_type_options[question_type]} quiz on '{topic}'... Please wait."):
                try:
                    st.session_state.quiz_data = generate_quiz_content_st(topic, question_type, difficulty, num_questions)
                    if not genai or not GOOGLE_API_KEY:
                        st.info("Displaying placeholder quiz data as AI generation is not fully configured.")

                    if not st.session_state.quiz_data or not st.session_state.quiz_data.get('questions'):
                         st.warning("The AI (or placeholder) did not return any questions. Try adjusting parameters or check AI configuration.")
                    
                    st.session_state.submitted_answers = {} 
                    st.session_state.show_results = False 
                    st.session_state.current_topic = topic 
                    st.success("Quiz generated successfully!")
                except Exception as e:
                    st.error(f"Failed to generate quiz: {e}")
                    st.session_state.quiz_data = None


    if st.session_state.quiz_data:
        quiz = st.session_state.quiz_data
        st.header(f"📜 Quiz on: {quiz['topic']}")
        st.subheader(f"Difficulty: {quiz['difficulty']} | Type: {question_type_options[quiz['question_type']]}")

        with st.expander("💡 Topic Explanation", expanded=True):
            st.markdown(quiz.get('content', 'No explanation provided.'))

        st.markdown("---")
        st.subheader("❓ Questions")

        if not quiz['questions']:
            st.warning("No questions were generated for this topic. Try different parameters or check AI settings.")
        else:
            user_answers_form = st.form(key="user_answers_form")
            for i, q in enumerate(quiz['questions']):
                question_key = f"q_{i}"
                user_answers_form.markdown(f"**Question {i+1}:** {q['question_text']}")

                if q['type'] == 'mcq':
                    options = q.get('options', [])
                    options_display = [str(opt) for opt in options]
                    if options_display and len(options_display) > 0:
                        st.session_state.submitted_answers[question_key] = user_answers_form.radio(
                            "Your answer:", options_display, key=question_key, index=None
                        )
                    else:
                        user_answers_form.markdown("_MCQ options not available for this question._")
                        st.session_state.submitted_answers[question_key] = None

                elif q['type'] == 'fill':
                    st.session_state.submitted_answers[question_key] = user_answers_form.text_input(
                        "Your answer:", key=question_key
                    )
                elif q['type'] == 'tf':
                    st.session_state.submitted_answers[question_key] = user_answers_form.radio(
                        "Your answer:", ["True", "False"], key=question_key, index=None
                    )
                else:
                     user_answers_form.markdown(f"_Unsupported question type: {q.get('type', 'Unknown')}_")
                     st.session_state.submitted_answers[question_key] = None
                user_answers_form.markdown("---")

            submit_answers_button = user_answers_form.form_submit_button("✅ Submit Answers")

            if submit_answers_button:
                st.session_state.show_results = True
                # Calculate results and store them for email function
                current_score = 0
                current_total_questions = len(quiz['questions'])
                current_detailed_results = []

                for i_res, q_res in enumerate(quiz['questions']):
                    q_key_res = f"q_{i_res}"
                    submitted_ans_res = st.session_state.submitted_answers.get(q_key_res)
                    correct_ans_res = q_res.get('answer')
                    res_is_correct = False
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
                        'is_correct': res_is_correct
                    })
                
                st.session_state.last_quiz_score = current_score
                st.session_state.last_quiz_total_questions = current_total_questions
                st.session_state.last_quiz_percentage = (current_score / current_total_questions * 100) if current_total_questions > 0 else 0
                st.session_state.last_quiz_detailed_results = current_detailed_results


        if st.session_state.show_results and quiz['questions']:
            st.markdown("---")
            st.header("📊 Quiz Results")
            
            # Use stored results for display
            score_to_display = st.session_state.last_quiz_score
            total_questions_to_display = st.session_state.last_quiz_total_questions
            percentage_to_display = st.session_state.last_quiz_percentage
            detailed_results_to_display = st.session_state.last_quiz_detailed_results

            for result_item in detailed_results_to_display:
                with st.container():
                    st.markdown(f"**Question {result_item['question_index'] + 1}:** {result_item['question_text']}")
                    submitted_display = result_item['submitted_answer'] if result_item['submitted_answer'] is not None else 'Not Answered'
                    st.write(f"Your answer: `{submitted_display}`")
                    
                    correct_ans_display_val = result_item['correct_answer']
                    correct_ans_display_text = "True" if correct_ans_display_val is True else ("False" if correct_ans_display_val is False else correct_ans_display_val)

                    if result_item['is_correct']:
                        st.success(f"Correct! The answer is `{correct_ans_display_text}`.")
                    else:
                        st.error(f"Incorrect. The correct answer is `{correct_ans_display_text}`.")
                st.markdown("---")

            st.subheader(f"🏆 Your Final Score: {score_to_display}/{total_questions_to_display}")
            st.progress(int(percentage_to_display))
            st.markdown(f"Percentage: **{percentage_to_display:.2f}%**")

            if percentage_to_display == 100:
                st.balloons()
                st.success("🎉 Congratulations! You got a perfect score! 🎉")
            elif percentage_to_display >= 70:
                st.info("👍 Great job!")
            elif percentage_to_display >= 50:
                st.warning("🙂 Good effort, keep practicing!")
            else:
                st.error("😕 Keep trying! Review the explanations and try again.")

            # Email sharing section
            st.markdown("---")
            st.subheader("📧 Share Your Results via Email")
            if not EMAIL_HOST_USER or not EMAIL_HOST_PASSWORD:
                 st.warning("Email sending is not configured by the administrator (missing credentials).")
            else:
                email_address_st = st.text_input("Enter your email address:", key="email_results_input_st")
                if st.button("✉️ Send Email", key="send_email_button_st"):
                    if not email_address_st:
                        st.error("Please enter an email address.")
                    elif not re.match(r"[^@]+@[^@]+\.[^@]+", email_address_st): # Basic email validation
                        st.error("Invalid email address format.")
                    else:
                        if 'last_quiz_detailed_results' in st.session_state and st.session_state.quiz_data:
                            with st.spinner("Sending email..."):
                                send_quiz_email_st(
                                    email_address_st,
                                    st.session_state.quiz_data, # topic, difficulty, explanation, original questions
                                    st.session_state.last_quiz_score,
                                    st.session_state.last_quiz_total_questions,
                                    st.session_state.last_quiz_percentage,
                                    st.session_state.last_quiz_detailed_results
                                )
                        else:
                            st.error("No quiz results found to send. Please complete a quiz first.")


    else:
        st.info("Configure your quiz in the sidebar and click 'Generate Quiz' to start.")
        st.markdown("""
        ### How to use Quizify Streamlit:
        1.  **Enter a Topic**: Type any subject you want a quiz on.
        2.  **Select Question Type**: Choose from Multiple Choice, Fill in the Blank, or True/False.
        3.  **Choose Difficulty**: Pick Easy, Medium, or Hard.
        4.  **Number of Questions**: Decide how many questions you want (1-20).
        5.  Click **Generate Quiz**!
        
        The quiz explanation and questions will appear here. Good luck! 🍀
        """)

    st.markdown("---")
    st.caption("Quizify Streamlit App - Powered by AI")

if __name__ == '__main__':
    main()
