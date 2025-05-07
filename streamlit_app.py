
import streamlit as st
import os
import json
import re

# Attempt to import google.generativeai, but handle if not available or API key is missing
try:
    from google import genai
    from dotenv import load_dotenv

    # Load environment variables from .env file if present
    # Useful if running streamlit app locally in an environment where .env is used
    load_dotenv()
    GOOGLE_API_KEY = os.environ.get('GOOGLE_API_KEY')

    if GOOGLE_API_KEY:
        client = genai.configure(api_key=GOOGLE_API_KEY)
    else:
        st.warning("GOOGLE_API_KEY not found. AI generation will use placeholders.")
        genai = None # Ensure genai is None if key is missing
except ImportError:
    st.warning("google.generativeai or python-dotenv library not found. AI generation will use placeholders.")
    genai = None # Ensure genai is None if library is missing

# --- Helper Function for AI Generation (adapted from Django views) ---
def generate_quiz_content_st(topic: str, question_type: str, difficulty: str, num_questions: int = 5):
    """
    Generates quiz content (explanation and questions) using the Gemini API if available,
    otherwise returns placeholder data.
    """
    if not genai or not GOOGLE_API_KEY:
        # Placeholder data if API key or library is not available
        st.info("Using placeholder data as Google API Key or genai library is not configured.")
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

    model = 'gemini-2.0-flash'

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
                    st.error(f"Failed to extract JSON. Raw response:\n{raw_text}")
                    raise ValueError("Could not find valid JSON in the AI response after multiple cleaning attempts.")
            try:
                generated_data = json.loads(json_str)
            except json.JSONDecodeError as e:
                st.error(f"Error decoding cleaned JSON: {e}\nCleaned JSON string was:\n{json_str}\nOriginal raw response was:\n{raw_text}")
                raise ValueError(f"Failed to parse the AI's response as valid JSON even after cleaning. {e}") from e

        if 'explanation' not in generated_data or not isinstance(generated_data['explanation'], str):
            raise ValueError("Generated JSON is missing 'explanation' key or it's not a string.")
        if 'questions' not in generated_data or not isinstance(generated_data['questions'], list):
            raise ValueError("Generated JSON is missing 'questions' key or it's not a list.")
        
        if len(generated_data['questions']) != num_questions:
             st.warning(f"AI returned {len(generated_data['questions'])} questions, but {num_questions} were requested. Using the {len(generated_data['questions'])} questions returned.")

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
        st.error(f"An unexpected error occurred during AI generation: {e}")
        # Re-raise a more generic error to the view
        raise Exception(f"An error occurred while communicating with the AI service: {e}") from e


def main():
    st.set_page_config(page_title="Quizify Streamlit", layout="wide", initial_sidebar_state="expanded")

    st.title("🧙 Quizify - AI Powered Quiz Generator")
    st.markdown("Generate quizzes on any topic using AI!")

    # Initialize session state for quiz data and submission
    if 'quiz_data' not in st.session_state:
        st.session_state.quiz_data = None
    if 'submitted_answers' not in st.session_state:
        st.session_state.submitted_answers = {}
    if 'show_results' not in st.session_state:
        st.session_state.show_results = False
    if 'current_topic' not in st.session_state:
        st.session_state.current_topic = ""


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
            # Convert display name back to key for processing
            question_type = [k for k, v in question_type_options.items() if v == question_type_display][0]

            difficulty = st.select_slider("Select Difficulty:", options=['Easy', 'Medium', 'Hard'], value='Medium')
            num_questions = st.number_input("Number of Questions:", min_value=1, max_value=20, value=5)
            generate_button = st.form_submit_button(label="🚀 Generate Quiz")

        if st.button("🔄 Reset Quiz & Start Over"):
            st.session_state.quiz_data = None
            st.session_state.submitted_answers = {}
            st.session_state.show_results = False
            st.session_state.current_topic = ""
            st.rerun()


    if generate_button:
        if not topic.strip():
            st.error("Please enter a topic for the quiz.")
        else:
            with st.spinner(f"Generating {difficulty} {question_type_options[question_type]} quiz on '{topic}'... Please wait."):
                try:
                    st.session_state.quiz_data = generate_quiz_content_st(topic, question_type, difficulty, num_questions)
                    st.session_state.submitted_answers = {} # Reset answers for new quiz
                    st.session_state.show_results = False # Hide previous results
                    st.session_state.current_topic = topic # Store current topic
                    st.success("Quiz generated successfully!")
                except Exception as e:
                    st.error(f"Failed to generate quiz: {e}")
                    st.session_state.quiz_data = None


    if st.session_state.quiz_data:
        quiz = st.session_state.quiz_data
        st.header(f"📜 Quiz on: {quiz['topic']}")
        st.subheader(f"Difficulty: {quiz['difficulty']} | Type: {question_type_options[quiz['question_type']]}")

        with st.expander("💡 Topic Explanation", expanded=True):
            st.markdown(quiz['content'])

        st.markdown("---")
        st.subheader("❓ Questions")

        if not quiz['questions']:
            st.warning("No questions were generated for this topic. Try different parameters.")
        else:
            user_answers_form = st.form(key="user_answers_form")
            for i, q in enumerate(quiz['questions']):
                question_key = f"q_{i}"
                user_answers_form.markdown(f"**Question {i+1}:** {q['question_text']}")

                if q['type'] == 'mcq':
                    options = q.get('options', [])
                    # Ensure options are strings for display
                    options_display = [str(opt) for opt in options]
                    st.session_state.submitted_answers[question_key] = user_answers_form.radio(
                        "Your answer:", options_display, key=question_key, index=None
                    )
                elif q['type'] == 'fill':
                    st.session_state.submitted_answers[question_key] = user_answers_form.text_input(
                        "Your answer:", key=question_key
                    )
                elif q['type'] == 'tf':
                    st.session_state.submitted_answers[question_key] = user_answers_form.radio(
                        "Your answer:", ["True", "False"], key=question_key, index=None
                    )
                user_answers_form.markdown("---")

            submit_answers_button = user_answers_form.form_submit_button("✅ Submit Answers")

            if submit_answers_button:
                st.session_state.show_results = True


        if st.session_state.show_results and quiz['questions']:
            st.markdown("---")
            st.header("📊 Quiz Results")
            score = 0
            total_questions_answered = len(quiz['questions'])

            for i, q in enumerate(quiz['questions']):
                question_key = f"q_{i}"
                submitted_answer_val = st.session_state.submitted_answers.get(question_key)
                correct_answer_val = q.get('answer')
                is_correct = False

                with st.container():
                    st.markdown(f"**Question {i+1}:** {q['question_text']}")
                    st.write(f"Your answer: `{submitted_answer_val if submitted_answer_val is not None else 'Not Answered'}`")

                    # Type conversion and comparison
                    if submitted_answer_val is not None:
                        if q['type'] == 'tf':
                            # Convert submitted "True"/"False" string to boolean
                            submitted_bool = str(submitted_answer_val).lower() == 'true'
                            is_correct = (submitted_bool == correct_answer_val)
                        elif q['type'] == 'fill':
                            is_correct = str(submitted_answer_val).strip().lower() == str(correct_answer_val).strip().lower()
                        else: # mcq
                            is_correct = str(submitted_answer_val) == str(correct_answer_val)
                    
                    if is_correct:
                        score += 1
                        st.success(f"Correct! The answer is `{correct_answer_val}`.")
                    else:
                        st.error(f"Incorrect. The correct answer is `{correct_answer_val}`.")
                st.markdown("---")

            st.subheader(f"🏆 Your Final Score: {score}/{total_questions_answered}")
            percentage = (score / total_questions_answered * 100) if total_questions_answered > 0 else 0
            st.progress(int(percentage))
            st.markdown(f"Percentage: **{percentage:.2f}%**")

            if percentage == 100:
                st.balloons()
                st.success("🎉 Congratulations! You got a perfect score! 🎉")
            elif percentage >= 70:
                st.info("👍 Great job!")
            elif percentage >= 50:
                st.warning("🙂 Good effort, keep practicing!")
            else:
                st.error("😕 Keep trying! Review the explanations and try again.")


    else:
        st.info("Configure your quiz in the sidebar and click 'Generate Quiz' to start.")
        st.markdown("""
        ### How to use Quizify Streamlit:
        1.  **Enter a Topic**: Type any subject you want a quiz on (e.g., "Python Programming", "World History", "Photosynthesis").
        2.  **Select Question Type**: Choose from Multiple Choice, Fill in the Blank, or True/False.
        3.  **Choose Difficulty**: Pick Easy, Medium, or Hard.
        4.  **Number of Questions**: Decide how many questions you want (1-100).
        5.  Click **Generate Quiz**!
        
        The quiz explanation and questions will appear here. Good luck! 🍀
        """)

    st.markdown("---")
    st.caption("Quizify Streamlit App - Powered by AI")

if __name__ == '__main__':
    main()
