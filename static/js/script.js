console.log("Quizify JS loaded. Sequential questions & Focus Mode enabled.");

document.addEventListener('DOMContentLoaded', function() {
    const quizForm = document.getElementById('quiz-form'); // Form containing questions
    const generationForm = document.getElementById('generation-form'); // The initial form to generate quiz
    const quizContainer = document.getElementById('quiz-container'); // Div holding the displayed quiz
    const scoreContainer = document.getElementById('score-container'); // Div holding the final score/results summary
    const detailedResultsContainer = document.getElementById('detailed-results'); // Detailed breakdown in score container
    const finalScoreEl = document.getElementById('final-score');
    const totalQuestionsEl = document.getElementById('total-questions');
    const scorePercentageEl = document.getElementById('score-percentage');
    const resultsTopicEl = document.getElementById('results-topic');
    const resultsDifficultyEl = document.getElementById('results-difficulty');
    const submissionErrorEl = document.getElementById('quiz-submission-error'); // General submission error div
    const tryAgainBtn = document.getElementById('try-again-btn'); // Button in score container
    const focusCursor = document.getElementById('focus-cursor'); // Focus mode cursor element
    const focusModeButton = document.getElementById('focus-mode-toggle'); // Focus mode toggle button
    const body = document.body;

    // Email form elements
    const emailQuizForm = document.getElementById('email-quiz-form');
    const emailAddressInput = document.getElementById('email-address');
    const sendEmailBtn = document.getElementById('send-email-btn');
    const emailStatusMessageEl = document.getElementById('email-status-message');

    let currentQuestionIndex = 0; // Track the currently displayed question
    let allQuestions = []; // Store all question card elements
    let answers = {}; // Store user answers as they progress
    let isFocusMode = false; // State variable for focus mode
    let currentAttemptId = null; // To store the attempt ID for sending email

    // --- Focus Mode Logic ---
    function enableFocusMode() {
        if (!isFocusMode) {
            isFocusMode = true;
            body.classList.add('focus-mode-active');
            // Use the entire document for mousemove events to track cursor everywhere
            document.addEventListener('mousemove', moveFocusCursor);
            if (focusModeButton) {
                focusModeButton.classList.add('active'); // Update button style
                focusModeButton.title = 'Focus Mode Active (Double-click anywhere to disable)';
            }
             // Ensure cursor is visible immediately and positioned correctly
             if (focusCursor) {
                 focusCursor.style.opacity = '1';
                 // Initial positioning might be off, but will correct on first move
                 // Could potentially set initial position based on click event if needed
             }
            console.log("Focus Mode Enabled");
        }
    }

    function disableFocusMode() {
        if (isFocusMode) {
            isFocusMode = false;
            body.classList.remove('focus-mode-active');
            document.removeEventListener('mousemove', moveFocusCursor);
            if (focusModeButton) {
                focusModeButton.classList.remove('active'); // Update button style
                focusModeButton.title = 'Toggle Focus Mode (Double-click anywhere to enable)';
            }
            if (focusCursor) {
                focusCursor.style.opacity = '0'; // Ensure it hides fully
            }
            console.log("Focus Mode Disabled");
        }
    }

    function moveFocusCursor(e) {
        if (isFocusMode && focusCursor) {
            // Use pageX/pageY which are relative to the whole document, including scrolled area
            // Ensure the cursor follows precisely even when the page is scrolled
            const x = e.pageX;
            const y = e.pageY;
            focusCursor.style.left = `${x}px`;
            focusCursor.style.top = `${y}px`;
            focusCursor.style.opacity = '1'; // Make sure it's visible while moving
        }
    }

    // Toggle focus mode on double-click (body)
    body.addEventListener('dblclick', (e) => {
        // Prevent toggling if the double-click was on the toggle button itself
        if (focusModeButton && focusModeButton.contains(e.target)) {
            return;
        }
        if (isFocusMode) {
            disableFocusMode();
        } else {
            enableFocusMode();
            // Optionally, immediately move cursor to double-click location
            if (focusCursor) {
                 focusCursor.style.left = `${e.pageX}px`;
                 focusCursor.style.top = `${e.pageY}px`;
                 focusCursor.style.opacity = '1';
            }
        }
    });

    // Toggle focus mode with the button click
    if (focusModeButton) {
        focusModeButton.addEventListener('click', (e) => {
            e.stopPropagation(); // Prevent body double-click from firing immediately
            if (isFocusMode) {
                disableFocusMode();
            } else {
                enableFocusMode();
            }
        });
    }


    // --- Quiz Generation & Display Logic ---
    if (generationForm) {
        generationForm.addEventListener('submit', function(event) {
            // Optional: Add a loading indicator
            const generateBtn = generationForm.querySelector('button[type="submit"]');
            if (generateBtn) {
                generateBtn.disabled = true;
                // Using Bootstrap spinner classes
                generateBtn.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Generating...';
            }
             // Hide previous results smoothly if any
             hideElementSmoothly(scoreContainer);
             hideElementSmoothly(quizContainer);
             // Add animations to generation form card on submit maybe?
             const formCard = generationForm.closest('.card');
             formCard?.classList.add('animate__animated', 'animate__pulse'); // Example animation
        });
    }

     // --- Function to show an element smoothly ---
     function showElementSmoothly(element, animationClass = 'animate__fadeInUp') { // Added animation parameter
        if (element) {
             // Reset animation classes before showing
             element.className = element.className.replace(/animate__\S+/g, '').trim();

             // Check if already visible or has the class to prevent re-triggering animation
             if (element.style.display !== 'none' && !element.classList.contains('visible')) {
                element.style.display = 'block'; // Or 'flex', 'grid' depending on layout needs
                setTimeout(() => {
                    element.classList.add('visible', 'animate__animated', animationClass); // Add visibility and animation classes
                }, 10);
             } else if (element.style.display === 'none'){
                 element.style.display = 'block';
                 setTimeout(() => {
                    element.classList.add('visible', 'animate__animated', animationClass);
                 }, 10);
             }
        }
    }

    // --- Function to hide an element smoothly ---
    function hideElementSmoothly(element, animationClass = 'animate__fadeOutDown') { // Added animation parameter
        if (element && element.classList.contains('visible')) {
            // Apply exit animation
             element.className = element.className.replace(/animate__\S+/g, '').trim(); // Clear previous animations
             element.classList.add('animate__animated', animationClass);

            // Wait for animation to finish before setting display to none and removing classes
            // Assumes animation duration is around 1s from Animate.css default
            setTimeout(() => {
                // Check if it hasn't been made visible again in the meantime
                if (!element.classList.contains('visible') || !element.matches(':hover')) { // Check visibility and hover state
                    element.style.display = 'none';
                    element.classList.remove('visible', 'animate__animated', animationClass);
                }
            }, 1000); // Match common Animate.css duration

            element.classList.remove('visible'); // Remove visible class immediately for state tracking

        } else if (element && element.style.display !== 'none') {
             // If it was visible but didn't have the class, hide directly
             element.style.display = 'none';
        }
    }


    // After quiz generation (when the page reloads with quiz_result)
    if (quizForm) {
        allQuestions = quizForm.querySelectorAll('.question-card');
        setupQuestionNavigation();
        // Initially show the quiz container smoothly with animation
        // Choose different animations for quiz/score containers
        showElementSmoothly(quizContainer, 'animate__zoomInUp');
        adjustQuizFormHeight(); // Set initial height after it's visible
    }

    // --- Function to Set Up Navigation Buttons (Next/Submit) ---
    function setupQuestionNavigation() {
        allQuestions.forEach((card, index) => {
            const nextBtn = card.querySelector('.btn-next');
            const submitBtn = card.querySelector('.btn-submit-quiz');
            const questionIndex = parseInt(card.dataset.questionIndex); // Get index from data attribute

            // Add animations to buttons on hover maybe?
            [nextBtn, submitBtn].forEach(btn => {
                if (btn) {
                    btn.addEventListener('mouseenter', () => btn.classList.add('animate__animated', 'animate__pulse'));
                    btn.addEventListener('animationend', () => btn.classList.remove('animate__animated', 'animate__pulse'));
                }
            });


            if (nextBtn) {
                nextBtn.addEventListener('click', () => {
                    if (validateAndStoreAnswer(card, questionIndex)) {
                        showNextQuestion(questionIndex);
                    }
                });
            }

            if (submitBtn) {
                submitBtn.addEventListener('click', () => {
                    if (validateAndStoreAnswer(card, questionIndex)) {
                         submitQuiz();
                    }
                });
            }
        });
    }

    // --- Function to Validate the Current Question's Answer and Store It ---
    function validateAndStoreAnswer(card, questionIndex) {
        const questionKey = `q${questionIndex + 1}`;
        const inputs = card.querySelectorAll(`[name="${questionKey}"]`);
        const validationErrorEl = card.querySelector('.validation-error');
        let currentAnswer = null;
        let answered = false;

        // Clear previous validation state
        if (validationErrorEl) {
             validationErrorEl.style.display = 'none';
             validationErrorEl.classList.remove('animate__animated', 'animate__shakeX');
        }
        card.classList.remove('unanswered');


        if (inputs.length > 0) {
            const inputType = inputs[0].type;
            if (inputType === 'radio') {
                const checkedOption = card.querySelector(`input[name="${questionKey}"]:checked`);
                if (checkedOption) {
                    currentAnswer = checkedOption.value;
                    answered = true;
                }
            } else if (inputType === 'text') { // Assumes 'fill' uses type="text"
                const textInput = inputs[0];
                if (textInput.value.trim() !== '') {
                    currentAnswer = textInput.value.trim();
                    answered = true;
                }
            }
        }

        if (!answered) {
            if (validationErrorEl) {
                validationErrorEl.textContent = 'Please select or enter an answer before proceeding.';
                validationErrorEl.style.display = 'block'; // Show validation error
                validationErrorEl.classList.add('animate__animated', 'animate__shakeX'); // Add shake animation
            }
             card.classList.add('unanswered'); // Highlight if unanswered
             validationErrorEl?.scrollIntoView({ behavior: 'smooth', block: 'center' });
            return false; // Validation failed
        }

        answers[questionKey] = currentAnswer; // Store the valid answer
        console.log(`Stored answer for ${questionKey}:`, currentAnswer);
        return true; // Validation passed
    }


    // --- Function to Show the Next Question ---
    function showNextQuestion(currentIndex) {
        const currentCard = allQuestions[currentIndex];
        const nextIndex = currentIndex + 1;

        if (nextIndex < allQuestions.length) {
            const nextCard = allQuestions[nextIndex];

            // Add 'exiting' class to current card for CSS transition out
            currentCard.classList.add('exiting');
            currentCard.classList.remove('active');

             // Make the next card active to trigger CSS transition in
             nextCard.style.visibility = 'visible'; // Ensure it's visible before adding active
             nextCard.style.display = 'block';
             setTimeout(() => { // Use timeout to ensure styles apply for transition
                nextCard.classList.add('active');
                currentQuestionIndex = nextIndex;
                adjustQuizFormHeight(); // Adjust height for the new card

                // Optionally add entry animation to the new card content
                 const content = nextCard.querySelector('.card-body') || nextCard; // Target inner content if exists
                 content?.classList.add('animate__animated', 'animate__fadeInRight');
                 content?.addEventListener('animationend', () => content.classList.remove('animate__animated', 'animate__fadeInRight'), { once: true });

            }, 50); // Small delay for transition


        }
         // If it's the last question, the submit button handles the final action
    }

     // --- Function to Dynamically Adjust Quiz Form Height ---
     function adjustQuizFormHeight() {
         if (!quizForm || allQuestions.length === 0) return;

         const activeCard = quizForm.querySelector('.question-card.active');
         if (activeCard) {
             const cardHeight = activeCard.offsetHeight;
             // Add some padding/buffer to the height
             const targetHeight = cardHeight + 40; // Increased buffer slightly
             quizForm.style.minHeight = `${targetHeight}px`;
         } else if (allQuestions.length > 0 && allQuestions[0]) {
             // Fallback: If no active card (e.g., initial load), use the first card
             const firstCardHeight = allQuestions[0].offsetHeight;
              const targetHeight = firstCardHeight + 40;
             quizForm.style.minHeight = `${targetHeight}px`;
         }
     }
     // Adjust height on window resize as well
     window.addEventListener('resize', adjustQuizFormHeight);


    // --- Function to Handle Final Quiz Submission ---
    function submitQuiz() {
        console.log("Submitting quiz with answers:", answers);
        if (submissionErrorEl) {
            submissionErrorEl.style.display = 'none'; // Hide previous errors
            submissionErrorEl.textContent = '';
             submissionErrorEl.classList.remove('animate__animated', 'animate__shakeX');
        }


        // Disable the submit button on the last card during processing
        let submitBtn = null;
        if (allQuestions.length > 0) {
             const lastCard = allQuestions[allQuestions.length - 1];
             submitBtn = lastCard.querySelector('.btn-submit-quiz');
             if (submitBtn) {
                submitBtn.disabled = true;
                // Use innerHTML for spinner
                submitBtn.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Checking...';
             }
        }


        const quizId = quizForm.dataset.quizId;
        if (!quizId) {
            displaySubmissionError("Error: Could not find Quiz ID. Please regenerate the quiz.");
            if (submitBtn) {
                 submitBtn.disabled = false;
                 submitBtn.textContent = 'Submit Quiz';
            }
            return;
        }

        // Prepare data for sending
        const dataToSend = {
            quiz_id: quizId,
            answers: answers, // Send all collected answers
        };

        // Send data using Fetch API
        fetch(CHECK_ANSWERS_URL, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': CSRF_TOKEN
            },
            body: JSON.stringify(dataToSend)
        })
        .then(response => {
            if (!response.ok) {
                return response.json().then(errData => {
                     throw new Error(errData.error || `Server Error: ${response.statusText}`);
                }).catch(() => {
                    throw new Error(`HTTP error! Status: ${response.status}`);
                });
            }
            return response.json(); // Parse successful response
        })
        .then(data => {
            console.log("Received check_answers data:", data);
            if (data.error) {
                displaySubmissionError(`Submission Error: ${data.error}`);
            } else {
                currentAttemptId = data.attempt_id; // Store attempt ID for email
                // Hide the quiz form container smoothly after successful submission
                hideElementSmoothly(quizContainer, 'animate__zoomOut'); // Different exit animation
                // Process and display feedback + final score with delay for exit animation
                setTimeout(() => {
                     displayFeedbackAndResults(data);
                }, 500); // Delay display of results
            }
        })
        .catch(error => {
            console.error('Error submitting answers:', error);
            displaySubmissionError(`An error occurred: ${error.message}. Please check your connection and try again.`);
        })
        .finally(() => {
             // Re-enable submit button only if there was an error
             if (submitBtn && submitBtn.disabled) {
                 if (submissionErrorEl && submissionErrorEl.style.display !== 'none') {
                    submitBtn.disabled = false;
                    submitBtn.textContent = 'Submit Quiz';
                 }
             }
        });
    }


    // --- Function to Display Feedback on Questions and Final Score/Results ---
    function displayFeedbackAndResults(data) {
        // 1. Quiz Container is already hidden in submitQuiz success logic

        // 2. Show the final score container smoothly with animation
        showElementSmoothly(scoreContainer, 'animate__bounceInUp'); // Different entry animation for results


        // 3. Populate score summary
        if (finalScoreEl) finalScoreEl.textContent = data.score;
        if (totalQuestionsEl) totalQuestionsEl.textContent = data.total_questions;
        if (scorePercentageEl) scorePercentageEl.textContent = data.percentage;
        if (resultsTopicEl) resultsTopicEl.textContent = data.topic || 'N/A';
        if (resultsDifficultyEl) resultsDifficultyEl.textContent = data.difficulty || 'N/A';

        // 4. Populate detailed results list
        populateDetailedResultsList(data.results);

        // 5. Scroll to the score section smoothly (optional)
        scoreContainer?.scrollIntoView({ behavior: 'smooth', block: 'start' });

        // 6. Hide any lingering submission errors
        if (submissionErrorEl) submissionErrorEl.style.display = 'none';
    }

    // --- Function to Populate the Detailed Results List (at the bottom) ---
    function populateDetailedResultsList(resultsData) {
        const resultItemTemplate = document.getElementById('result-item-template');
        if (!detailedResultsContainer || !resultItemTemplate) {
            console.error("Detailed results container or template not found.");
            return; // Exit if elements don't exist
        }

        detailedResultsContainer.innerHTML = ''; // Clear previous results

        if (resultsData && resultsData.length > 0) {
            resultsData.forEach((result, index) => { // Add index for animation delay
                const templateContent = resultItemTemplate.content.cloneNode(true);
                const resultCard = templateContent.querySelector('.result-item');

                 // Get elements within the cloned template content
                 const qNumberEl = templateContent.querySelector('.result-q-number');
                 const qTextEl = templateContent.querySelector('.result-q-text');
                 const submittedEl = templateContent.querySelector('.result-submitted');
                 const correctEl = templateContent.querySelector('.result-correct');
                 const statusEl = templateContent.querySelector('.result-status');

                if (qNumberEl) qNumberEl.textContent = result.question_index + 1;
                if (qTextEl) qTextEl.innerHTML = result.question_text ? result.question_text.replace(/\n/g, '<br>') : 'N/A';
                if (submittedEl) submittedEl.textContent = result.submitted_answer !== null ? `${result.submitted_answer}` : 'Not Answered';

                let correctAnswerDisplay = result.correct_answer;
                 if (typeof result.correct_answer === 'boolean') {
                    correctAnswerDisplay = result.correct_answer ? 'True' : 'False';
                 }
                 if (correctEl) correctEl.textContent = `${correctAnswerDisplay}`;

                if (statusEl && resultCard) {
                    if (result.is_correct) {
                        statusEl.textContent = 'Correct!';
                        resultCard.classList.add('correct');
                    } else {
                        statusEl.textContent = 'Incorrect';
                         resultCard.classList.add('incorrect');
                    }
                }

                // Apply staggered animation delay (using CSS for this now)
                 // if (resultCard) {
                 //    resultCard.style.animationDelay = `${index * 0.1}s`;
                 // }


                detailedResultsContainer.appendChild(templateContent);
            });
        } else {
             detailedResultsContainer.innerHTML = '<p class="text-muted">No detailed results available.</p>';
        }
    }


     // --- Function to Display Submission Errors (General errors during fetch) ---
     function displaySubmissionError(message) {
         if (submissionErrorEl) {
            submissionErrorEl.textContent = message;
            submissionErrorEl.style.display = 'block';
            submissionErrorEl.classList.remove('animate__animated', 'animate__shakeX'); // Remove first if exists
            setTimeout(() => { // Add after slight delay
                 submissionErrorEl.classList.add('animate__animated', 'animate__shakeX');
            }, 10);
             // Scroll to the error message if it's potentially off-screen
            submissionErrorEl.scrollIntoView({ behavior: 'smooth', block: 'center' });
         }
     }

     // --- Try Again Button ---
     if(tryAgainBtn) {
         // Add hover animation
         tryAgainBtn.addEventListener('mouseenter', () => tryAgainBtn.classList.add('animate__animated', 'animate__headShake'));
         tryAgainBtn.addEventListener('animationend', () => tryAgainBtn.classList.remove('animate__animated', 'animate__headShake'));

         tryAgainBtn.addEventListener('click', () => {
              // Smoothly hide the score container before redirecting
              hideElementSmoothly(scoreContainer, 'animate__fadeOutRight');
              // Redirect after a delay to allow transition
              setTimeout(() => {
                 window.location.href = GENERATE_URL; // Use the URL provided by the template
              }, 800); // Delay slightly less than hide transition
         });
     }

     // --- Email Quiz Form Handling ---
     if (sendEmailBtn && emailAddressInput) {
        emailQuizForm.addEventListener('submit', function(event) {
            event.preventDefault(); // Prevent default form submission

            const email = emailAddressInput.value.trim();
            if (!email) {
                displayEmailStatus("Please enter an email address.", "error");
                return;
            }
            if (!currentAttemptId) {
                displayEmailStatus("No quiz attempt found to send. Please complete a quiz first.", "error");
                return;
            }

            // Disable button and show spinner
            sendEmailBtn.disabled = true;
            sendEmailBtn.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Sending...';
            displayEmailStatus("Sending email...", "info", false);


            const dataToSend = {
                email_address: email,
                attempt_id: currentAttemptId,
            };

            fetch(SEND_EMAIL_URL, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': CSRF_TOKEN
                },
                body: JSON.stringify(dataToSend)
            })
            .then(response => {
                if (!response.ok) {
                    // Try to parse JSON error from server, otherwise use statusText
                    return response.json().then(errData => {
                        throw new Error(errData.error || `Server Error: ${response.statusText}`);
                    }).catch(() => { // If parsing error JSON fails
                        throw new Error(`HTTP error! Status: ${response.status}`);
                    });
                }
                return response.json();
            })
            .then(data => {
                if (data.success) {
                    displayEmailStatus(data.message || "Email sent successfully!", "success");
                    emailAddressInput.value = ''; // Clear input on success
                } else {
                    // This case might be less common if !response.ok handles most errors
                    displayEmailStatus(data.error || "Failed to send email.", "error");
                }
            })
            .catch(error => {
                console.error('Error sending email:', error);
                displayEmailStatus(`An error occurred: ${error.message}`, "error");
            })
            .finally(() => {
                // Re-enable button
                sendEmailBtn.disabled = false;
                sendEmailBtn.textContent = 'Send Email';
            });
        });
    }

    function displayEmailStatus(message, type = "info", autoHide = true) {
        if (!emailStatusMessageEl) return;
        emailStatusMessageEl.textContent = message;
        emailStatusMessageEl.className = 'form-text mt-2'; // Reset classes, add margin top
        if (type === "success") {
            emailStatusMessageEl.classList.add('text-success');
        } else if (type === "error") {
            emailStatusMessageEl.classList.add('text-danger');
        } else { // info
            emailStatusMessageEl.classList.add('text-muted');
        }
        emailStatusMessageEl.style.display = 'block';

        // Clear previous timeout if one exists
        if (emailStatusMessageEl.timeoutId) {
            clearTimeout(emailStatusMessageEl.timeoutId);
        }

        if (autoHide) {
            emailStatusMessageEl.timeoutId = setTimeout(() => {
                hideElementSmoothly(emailStatusMessageEl, 'animate__fadeOut');
                // emailStatusMessageEl.style.display = 'none';
            }, 5000); // Hide after 5 seconds
        }
    }


     // --- Add initial animations to elements present on load ---
     const initialFormCard = document.querySelector('.form-section .card');
     const initialPlaceholder = document.querySelector('.placeholder .card'); // If placeholder exists

     if (initialFormCard) {
         initialFormCard.classList.add('animate__animated', 'animate__zoomIn');
     }
     if (initialPlaceholder) {
          initialPlaceholder.classList.add('animate__animated', 'animate__fadeIn');
     }

});
