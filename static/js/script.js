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

    // --- Mixed Question Type UI Elements ---
    const questionTypeSelect = document.getElementById('question_type');
    const mixedTypeOptionsDiv = document.getElementById('mixed-type-options');
    const singleTypeNumQuestionsDiv = document.getElementById('single-type-num-questions-container');
    const numMcqInput = document.getElementById('num_mcq');
    const numFillInput = document.getElementById('num_fill');
    const numTfInput = document.getElementById('num_tf');
    const mixedTotalCountSpan = document.getElementById('mixed-total-count');
    const numQuestionsInput = document.getElementById('num_questions'); // General num_questions

    let currentQuestionIndex = 0; 
    let allQuestions = []; 
    let answers = {}; 
    let isFocusMode = false; 
    let currentAttemptId = null; 

    // --- Focus Mode Logic ---
    function enableFocusMode() {
        if (!isFocusMode) {
            isFocusMode = true;
            body.classList.add('focus-mode-active');
            document.addEventListener('mousemove', moveFocusCursor);
            if (focusModeButton) {
                focusModeButton.classList.add('active'); 
                focusModeButton.title = 'Focus Mode Active (Double-click anywhere to disable)';
            }
             if (focusCursor) {
                 focusCursor.style.opacity = '1';
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
                focusModeButton.classList.remove('active'); 
                focusModeButton.title = 'Toggle Focus Mode (Double-click anywhere to enable)';
            }
            if (focusCursor) {
                focusCursor.style.opacity = '0'; 
            }
            console.log("Focus Mode Disabled");
        }
    }

    function moveFocusCursor(e) {
        if (isFocusMode && focusCursor) {
            const x = e.pageX;
            const y = e.pageY;
            focusCursor.style.left = `${x}px`;
            focusCursor.style.top = `${y}px`;
            focusCursor.style.opacity = '1'; 
        }
    }

    body.addEventListener('dblclick', (e) => {
        if (focusModeButton && focusModeButton.contains(e.target)) {
            return;
        }
        if (isFocusMode) {
            disableFocusMode();
        } else {
            enableFocusMode();
            if (focusCursor) {
                 focusCursor.style.left = `${e.pageX}px`;
                 focusCursor.style.top = `${e.pageY}px`;
                 focusCursor.style.opacity = '1';
            }
        }
    });

    if (focusModeButton) {
        focusModeButton.addEventListener('click', (e) => {
            e.stopPropagation(); 
            if (isFocusMode) {
                disableFocusMode();
            } else {
                enableFocusMode();
            }
        });
    }

    // --- Mixed Question Type UI Logic ---
    function updateTotalMixedQuestionsCount() {
        if (!numMcqInput || !numFillInput || !numTfInput || !mixedTotalCountSpan) return;
        const mcqCount = parseInt(numMcqInput.value) || 0;
        const fillCount = parseInt(numFillInput.value) || 0;
        const tfCount = parseInt(numTfInput.value) || 0;
        mixedTotalCountSpan.textContent = mcqCount + fillCount + tfCount;
    }

    if (questionTypeSelect) {
        questionTypeSelect.addEventListener('change', function() {
            if (this.value === 'mixed') {
                mixedTypeOptionsDiv.style.display = 'block';
                singleTypeNumQuestionsDiv.style.display = 'none';
                if (numQuestionsInput) numQuestionsInput.required = false; // Make general not required
                if (numMcqInput) numMcqInput.required = true; // At least one of mixed should be specified, handled by backend validation (sum > 0)
                if (numFillInput) numFillInput.required = true;
                if (numTfInput) numTfInput.required = true;
                updateTotalMixedQuestionsCount();
            } else {
                mixedTypeOptionsDiv.style.display = 'none';
                singleTypeNumQuestionsDiv.style.display = 'block';
                if (numQuestionsInput) numQuestionsInput.required = true;
                if (numMcqInput) numMcqInput.required = false;
                if (numFillInput) numFillInput.required = false;
                if (numTfInput) numTfInput.required = false;
            }
        });
        // Trigger change on load to set initial state if 'mixed' is pre-selected
        if (questionTypeSelect.value === 'mixed') {
             questionTypeSelect.dispatchEvent(new Event('change'));
        }
    }
    if (mixedTypeOptionsDiv && (numMcqInput && numFillInput && numTfInput)) {
        [numMcqInput, numFillInput, numTfInput].forEach(input => {
            input.addEventListener('input', updateTotalMixedQuestionsCount);
        });
        updateTotalMixedQuestionsCount(); // Initial call
    }


    // --- Quiz Generation & Display Logic ---
    if (generationForm) {
        generationForm.addEventListener('submit', function(event) {
            const generateBtn = generationForm.querySelector('button[type="submit"]');
            if (generateBtn) {
                generateBtn.disabled = true;
                generateBtn.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Generating...';
            }
             hideElementSmoothly(scoreContainer);
             hideElementSmoothly(quizContainer);
             const formCard = generationForm.closest('.card');
             formCard?.classList.add('animate__animated', 'animate__pulse'); 
        });
    }

     function showElementSmoothly(element, animationClass = 'animate__fadeInUp') { 
        if (element) {
             element.className = element.className.replace(/animate__\S+/g, '').trim();
             if (element.style.display !== 'none' && !element.classList.contains('visible')) {
                element.style.display = 'block'; 
                setTimeout(() => {
                    element.classList.add('visible', 'animate__animated', animationClass); 
                }, 10);
             } else if (element.style.display === 'none'){
                 element.style.display = 'block';
                 setTimeout(() => {
                    element.classList.add('visible', 'animate__animated', animationClass);
                 }, 10);
             }
        }
    }

    function hideElementSmoothly(element, animationClass = 'animate__fadeOutDown') { 
        if (element && element.classList.contains('visible')) {
             element.className = element.className.replace(/animate__\S+/g, '').trim(); 
             element.classList.add('animate__animated', animationClass);
            setTimeout(() => {
                if (!element.classList.contains('visible') || !element.matches(':hover')) { 
                    element.style.display = 'none';
                    element.classList.remove('visible', 'animate__animated', animationClass);
                }
            }, 1000); 
            element.classList.remove('visible'); 
        } else if (element && element.style.display !== 'none') {
             element.style.display = 'none';
        }
    }

    if (quizForm) {
        allQuestions = quizForm.querySelectorAll('.question-card');
        setupQuestionNavigation();
        showElementSmoothly(quizContainer, 'animate__zoomInUp');
        adjustQuizFormHeight(); 
    }

    function setupQuestionNavigation() {
        allQuestions.forEach((card, index) => {
            const nextBtn = card.querySelector('.btn-next');
            const submitBtn = card.querySelector('.btn-submit-quiz');
            const questionIndex = parseInt(card.dataset.questionIndex); 

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

    function validateAndStoreAnswer(card, questionIndex) {
        const questionKey = `q${questionIndex + 1}`;
        const inputs = card.querySelectorAll(`[name="${questionKey}"]`);
        const validationErrorEl = card.querySelector('.validation-error');
        let currentAnswer = null;
        let answered = false;

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
            } else if (inputType === 'text') { 
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
                validationErrorEl.style.display = 'block'; 
                validationErrorEl.classList.add('animate__animated', 'animate__shakeX'); 
            }
             card.classList.add('unanswered'); 
             validationErrorEl?.scrollIntoView({ behavior: 'smooth', block: 'center' });
            return false; 
        }

        answers[questionKey] = currentAnswer; 
        console.log(`Stored answer for ${questionKey}:`, currentAnswer);
        return true; 
    }

    function showNextQuestion(currentIndex) {
        const currentCard = allQuestions[currentIndex];
        const nextIndex = currentIndex + 1;

        if (nextIndex < allQuestions.length) {
            const nextCard = allQuestions[nextIndex];

            currentCard.classList.add('exiting');
            currentCard.classList.remove('active');

             nextCard.style.visibility = 'visible'; 
             nextCard.style.display = 'block';
             setTimeout(() => { 
                nextCard.classList.add('active');
                currentQuestionIndex = nextIndex;
                adjustQuizFormHeight(); 

                 const content = nextCard.querySelector('.card-body') || nextCard; 
                 content?.classList.add('animate__animated', 'animate__fadeInRight');
                 content?.addEventListener('animationend', () => content.classList.remove('animate__animated', 'animate__fadeInRight'), { once: true });
            }, 50); 
        }
    }

     function adjustQuizFormHeight() {
         if (!quizForm || allQuestions.length === 0) return;

         const activeCard = quizForm.querySelector('.question-card.active');
         if (activeCard) {
             const cardHeight = activeCard.offsetHeight;
             const targetHeight = cardHeight + 40; 
             quizForm.style.minHeight = `${targetHeight}px`;
         } else if (allQuestions.length > 0 && allQuestions[0]) {
             const firstCardHeight = allQuestions[0].offsetHeight;
              const targetHeight = firstCardHeight + 40;
             quizForm.style.minHeight = `${targetHeight}px`;
         }
     }
     window.addEventListener('resize', adjustQuizFormHeight);

    function submitQuiz() {
        console.log("Submitting quiz with answers:", answers);
        if (submissionErrorEl) {
            submissionErrorEl.style.display = 'none'; 
            submissionErrorEl.textContent = '';
             submissionErrorEl.classList.remove('animate__animated', 'animate__shakeX');
        }

        let submitBtn = null;
        if (allQuestions.length > 0) {
             const lastCard = allQuestions[allQuestions.length - 1];
             submitBtn = lastCard.querySelector('.btn-submit-quiz');
             if (submitBtn) {
                submitBtn.disabled = true;
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

        const dataToSend = {
            quiz_id: quizId,
            answers: answers, 
        };

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
            return response.json(); 
        })
        .then(data => {
            console.log("Received check_answers data:", data);
            if (data.error) {
                displaySubmissionError(`Submission Error: ${data.error}`);
            } else {
                currentAttemptId = data.attempt_id; 
                hideElementSmoothly(quizContainer, 'animate__zoomOut'); 
                setTimeout(() => {
                     displayFeedbackAndResults(data);
                }, 500); 
            }
        })
        .catch(error => {
            console.error('Error submitting answers:', error);
            displaySubmissionError(`An error occurred: ${error.message}. Please check your connection and try again.`);
        })
        .finally(() => {
             if (submitBtn && submitBtn.disabled) {
                 if (submissionErrorEl && submissionErrorEl.style.display !== 'none') {
                    submitBtn.disabled = false;
                    submitBtn.textContent = 'Submit Quiz';
                 }
             }
        });
    }

    function displayFeedbackAndResults(data) {
        showElementSmoothly(scoreContainer, 'animate__bounceInUp'); 

        if (finalScoreEl) finalScoreEl.textContent = data.score;
        if (totalQuestionsEl) totalQuestionsEl.textContent = data.total_questions;
        if (scorePercentageEl) scorePercentageEl.textContent = data.percentage;
        if (resultsTopicEl) resultsTopicEl.textContent = data.topic || 'N/A';
        if (resultsDifficultyEl) resultsDifficultyEl.textContent = data.difficulty || 'N/A';

        populateDetailedResultsList(data.results);
        scoreContainer?.scrollIntoView({ behavior: 'smooth', block: 'start' });
        if (submissionErrorEl) submissionErrorEl.style.display = 'none';
    }

    function populateDetailedResultsList(resultsData) {
        const resultItemTemplate = document.getElementById('result-item-template');
        if (!detailedResultsContainer || !resultItemTemplate) {
            console.error("Detailed results container or template not found.");
            return; 
        }

        detailedResultsContainer.innerHTML = ''; 

        if (resultsData && resultsData.length > 0) {
            resultsData.forEach((result, index) => { 
                const templateContent = resultItemTemplate.content.cloneNode(true);
                const resultCard = templateContent.querySelector('.result-item');
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
                detailedResultsContainer.appendChild(templateContent);
            });
        } else {
             detailedResultsContainer.innerHTML = '<p class="text-muted">No detailed results available.</p>';
        }
    }

     function displaySubmissionError(message) {
         if (submissionErrorEl) {
            submissionErrorEl.textContent = message;
            submissionErrorEl.style.display = 'block';
            submissionErrorEl.classList.remove('animate__animated', 'animate__shakeX'); 
            setTimeout(() => { 
                 submissionErrorEl.classList.add('animate__animated', 'animate__shakeX');
            }, 10);
            submissionErrorEl.scrollIntoView({ behavior: 'smooth', block: 'center' });
         }
     }

     if(tryAgainBtn) {
         tryAgainBtn.addEventListener('mouseenter', () => tryAgainBtn.classList.add('animate__animated', 'animate__headShake'));
         tryAgainBtn.addEventListener('animationend', () => tryAgainBtn.classList.remove('animate__animated', 'animate__headShake'));
         tryAgainBtn.addEventListener('click', () => {
              hideElementSmoothly(scoreContainer, 'animate__fadeOutRight');
              setTimeout(() => {
                 window.location.href = GENERATE_URL; 
              }, 800); 
         });
     }

     if (emailQuizForm && sendEmailBtn && emailAddressInput && emailStatusMessageEl) {
        emailQuizForm.addEventListener('submit', function(event) {
            event.preventDefault(); 

            const email = emailAddressInput.value.trim();
            if (!email) {
                displayEmailStatus("Please enter an email address.", "error");
                return;
            }
            if (!currentAttemptId) {
                displayEmailStatus("No quiz attempt found to send. Please complete a quiz first.", "error");
                return;
            }

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
                    return response.json().then(errData => {
                        throw new Error(errData.error || `Server Error: ${response.statusText}`);
                    }).catch(() => { 
                        throw new Error(`HTTP error! Status: ${response.status}`);
                    });
                }
                return response.json();
            })
            .then(data => {
                if (data.success) {
                    displayEmailStatus(data.message || "Email sent successfully!", "success");
                    emailAddressInput.value = ''; 
                } else {
                    displayEmailStatus(data.error || "Failed to send email.", "error");
                }
            })
            .catch(error => {
                console.error('Error sending email:', error);
                displayEmailStatus(`An error occurred: ${error.message}`, "error");
            })
            .finally(() => {
                sendEmailBtn.disabled = false;
                sendEmailBtn.textContent = 'Send Email';
            });
        });
    }

    function displayEmailStatus(message, type = "info", autoHide = true) {
        if (!emailStatusMessageEl) return;
        emailStatusMessageEl.textContent = message;
        emailStatusMessageEl.className = 'form-text mt-2'; 
        if (type === "success") {
            emailStatusMessageEl.classList.add('text-success');
        } else if (type === "error") {
            emailStatusMessageEl.classList.add('text-danger');
        } else { 
            emailStatusMessageEl.classList.add('text-muted');
        }
        emailStatusMessageEl.style.display = 'block';

        if (emailStatusMessageEl.timeoutId) {
            clearTimeout(emailStatusMessageEl.timeoutId);
        }

        if (autoHide) {
            emailStatusMessageEl.timeoutId = setTimeout(() => {
                hideElementSmoothly(emailStatusMessageEl, 'animate__fadeOut');
            }, 5000); 
        }
    }

     const initialFormCard = document.querySelector('.form-section .card');
     const initialPlaceholder = document.querySelector('.placeholder .card'); 

     if (initialFormCard) {
         initialFormCard.classList.add('animate__animated', 'animate__zoomIn');
     }
     if (initialPlaceholder) {
          initialPlaceholder.classList.add('animate__animated', 'animate__fadeIn');
     }
});

    
