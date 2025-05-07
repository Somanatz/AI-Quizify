# Quizify - AI Powered Quiz Generator

This project contains two main applications:
1.  A **Django application** for generating and managing quizzes.
2.  A **Streamlit application** providing an alternative UI for quiz generation.

## Common Setup (for both Django and Streamlit if using local AI generation)

1.  **Create and activate a virtual environment:**
    ```bash
    python -m venv venv
    # On Windows
    venv\Scripts\activate
    # On macOS/Linux
    source venv/bin/activate
    ```

2.  **Install dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

3.  **Environment Variables:**
    Create a `.env` file in the root of your project and add your Google API Key:
    ```env
    GOOGLE_API_KEY="YOUR_GOOGLE_API_KEY_HERE"
    DJANGO_SECRET_KEY="your_django_secret_key_for_dev_or_prod" # Add a strong secret key
    # For Django Email (optional, defaults to console if not set in DEBUG mode)
    # EMAIL_HOST_USER="your_gmail_address@gmail.com"
    # EMAIL_HOST_PASSWORD="your_gmail_app_password"
    ```
    Replace `"YOUR_GOOGLE_API_KEY_HERE"` with your actual Gemini API key.
    Replace `"your_django_secret_key_for_dev_or_prod"` with a long, random string.

## Django Application

### Setup & Run

1.  **Apply migrations (after installing requirements):**
    ```bash
    python manage.py migrate
    ```

2.  **Create a superuser (to access Django Admin):**
    ```bash
    python manage.py createsuperuser
    ```

3.  **Run the development server:**
    ```bash
    python manage.py runserver
    ```
    The Django application will be available at http://127.0.0.1:8000/.
    The Django admin panel will be at http://127.0.0.1:8000/admin/.

### Features
*   Generate quizzes on various topics, difficulties, and question types.
*   View topic explanations.
*   Answer questions sequentially.
*   View detailed results and scores.
*   Save quiz attempts to the database.
*   Option to send quiz results via email.

## Streamlit Application

### Run

1.  **Ensure you have completed the "Common Setup" steps above (virtual environment, installed requirements, and `.env` file with `GOOGLE_API_KEY`).**

2.  **Run the Streamlit app:**
    Navigate to the project root directory in your terminal (where `streamlit_app.py` is located) and run:
    ```bash
    streamlit run streamlit_app.py
    ```
    The Streamlit application will typically open in your web browser, or you can access it at http://localhost:8501.

### Features (Streamlit App)
*   User-friendly interface to specify quiz topic, type, difficulty, and number of questions.
*   Generates quiz explanation and questions using the Gemini API (if configured).
*   Allows users to answer questions directly in the app.
*   Displays immediate feedback and a final score.
*   (Note: The Streamlit app currently operates independently of the Django database for quiz attempts and user accounts.)

---
**(Note:** For AI generation to work in either application, a valid `GOOGLE_API_KEY` for the Gemini API must be provided in the `.env` file.)
