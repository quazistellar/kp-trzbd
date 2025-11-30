function initTest(testId, totalQuestions, attemptNumber) {
    console.log('Initializing test with parameters:', { 
        testId: testId, 
        totalQuestions: totalQuestions, 
        attemptNumber: attemptNumber 
    });

    const testForm = document.getElementById('testForm');
    const questions = document.querySelectorAll('.question-card');
    const prevBtn = document.getElementById('prevQuestion');
    const nextBtn = document.getElementById('nextQuestion');
    const submitBtn = document.getElementById('submitTest');
    const progressFill = document.getElementById('progressFill');
    const answeredCount = document.getElementById('answeredCount');
    const navButtons = document.querySelectorAll('.nav-question');
    
    if (!testForm) {
        console.error('Test form not found');
        return;
    }
    
    if (!questions || questions.length === 0) {
        console.error('No questions found');
        return;
    }

    let currentQuestion = 0;
    let answeredQuestions = new Set();
    let collectedAnswers = {};

    function showQuestion(index) {
        console.log(`Showing question ${index} of ${questions.length}`);
        
        questions.forEach(q => {
            if (q) q.style.display = 'none';
        });
        
        if (questions[index]) {
            questions[index].style.display = 'block';
            currentQuestion = index;
            
            if (prevBtn) {
                prevBtn.style.display = index > 0 ? 'inline-block' : 'none';
            }
            if (nextBtn) {
                nextBtn.style.display = index < questions.length - 1 ? 'inline-block' : 'none';
            }
            if (submitBtn) {
                submitBtn.style.display = index === questions.length - 1 ? 'inline-block' : 'none';
            }
            
            navButtons.forEach((btn, i) => {
                if (btn) {
                    btn.classList.toggle('active', i === index);
                    btn.classList.toggle('answered', answeredQuestions.has(i));
                }
            });
        }
    }

    function saveAnswer(questionIndex) {
        const question = questions[questionIndex];
        if (!question) return;
        
        const questionId = question.dataset.questionId;
        const answerType = getAnswerType(question);
        
        let answerData = null;
        
        try {
            switch (answerType) {
                case 'single_choice':
                    const selectedRadio = question.querySelector('input[type="radio"]:checked');
                    answerData = selectedRadio ? selectedRadio.value : null;
                    break;
                    
                case 'multiple_choice':
                    const selectedCheckboxes = Array.from(question.querySelectorAll('input[type="checkbox"]:checked'))
                        .map(cb => cb.value);
                    answerData = selectedCheckboxes.length > 0 ? selectedCheckboxes : null;
                    break;
                    
                case 'text_answer':
                    const textarea = question.querySelector('textarea');
                    answerData = textarea && textarea.value.trim() ? textarea.value.trim() : null;
                    break;
                    
                case 'matching':
                    const selects = question.querySelectorAll('select');
                    const matchingAnswers = {};
                    selects.forEach(select => {
                        if (select && select.value) {
                            matchingAnswers[select.name] = select.value;
                        }
                    });
                    answerData = Object.keys(matchingAnswers).length > 0 ? matchingAnswers : null;
                    break;
                    
                default:
                    console.warn('Unknown question type:', answerType);
            }
        } catch (error) {
            console.error('Error saving answer:', error);
        }
        
        if (answerData) {
            collectedAnswers[questionId] = answerData;
            answeredQuestions.add(questionIndex);
            console.log(`Saved answer for question ${questionId}:`, answerData);
        } else {
            delete collectedAnswers[questionId];
            answeredQuestions.delete(questionIndex);
            console.log(`Removed answer for question ${questionId}`);
        }
    }

    function getAnswerType(question) {
        if (question.querySelector('.single-choice-answers')) return 'single_choice';
        if (question.querySelector('.multiple-choice-answers')) return 'multiple_choice';
        if (question.querySelector('.text-answer')) return 'text_answer';
        if (question.querySelector('.matching-answer')) return 'matching';
        return 'unknown';
    }

    function updateProgress() {
        const progress = (answeredQuestions.size / questions.length) * 100;
        if (progressFill) {
            progressFill.style.width = `${progress}%`;
        }
        if (answeredCount) {
            answeredCount.textContent = answeredQuestions.size;
        }
    }

    function updateNavigation() {
        navButtons.forEach((btn, index) => {
            if (btn) {
                btn.classList.toggle('answered', answeredQuestions.has(index));
            }
        });
    }

    if (prevBtn) {
        prevBtn.addEventListener('click', () => {
            if (currentQuestion > 0) {
                showQuestion(currentQuestion - 1);
            }
        });
    }

    if (nextBtn) {
        nextBtn.addEventListener('click', () => {
            if (currentQuestion < questions.length - 1) {
                showQuestion(currentQuestion + 1);
            }
        });
    }

    testForm.addEventListener('submit', function(e) {
        e.preventDefault();
        
        console.log('Form submission started:', {
            testId: testId,
            answeredQuestions: answeredQuestions.size,
            totalQuestions: questions.length,
            attemptNumber: attemptNumber,
            answers: collectedAnswers
        });

        if (answeredQuestions.size !== questions.length) {
            if (!confirm('Вы ответили не на все вопросы. Вы уверены, что хотите завершить тест?')) {
                return;
            }
        }
        
        const formData = {
            answers: collectedAnswers,
            attempt_number: attemptNumber
        };
        
        console.log('Sending data:', formData);
        console.log('Request URL:', `/test/${testId}/submit/`);

        if (submitBtn) {
            submitBtn.disabled = true;
            submitBtn.innerHTML = '<span class="loading-spinner"></span> Проверка...';
        }
 
        const csrfToken = getCSRFToken();
        if (!csrfToken) {
            alert('Ошибка безопасности. Перезагрузите страницу.');
            resetSubmitButton();
            return;
        }

        fetch(`/test/${testId}/submit/`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': csrfToken,
                'X-Requested-With': 'XMLHttpRequest'
            },
            body: JSON.stringify(formData),
            credentials: 'same-origin'
        })
        .then(response => {
            console.log('Response status:', response.status, response.statusText);
            if (!response.ok) {
                return response.text().then(text => {
                    throw new Error(`HTTP ${response.status}: ${text}`);
                });
            }
            return response.json();
        })
        .then(data => {
            console.log('Server response:', data);
            if (data.success) {
                showResultModal(data);
            } else {
                const errorMsg = data.error || 'Неизвестная ошибка сервера';
                console.error('Server error:', errorMsg);
                alert('Ошибка при отправке теста: ' + errorMsg);
                resetSubmitButton();
            }
        })
        .catch(error => {
            console.error('Network error:', error);
            let errorMessage = 'Произошла ошибка при отправке теста. ';
            
            if (error.message.includes('400')) {
                errorMessage += 'Ошибка 400: Неверный запрос. Проверьте данные.';
            } else if (error.message.includes('403')) {
                errorMessage += 'Ошибка 403: Доступ запрещен. Проверьте CSRF токен.';
            } else if (error.message.includes('404')) {
                errorMessage += 'Ошибка 404: Страница не найдена.';
            } else {
                errorMessage += error.message;
            }
            
            alert(errorMessage);
            resetSubmitButton();
        });
    });

    function getCSRFToken() {
        let csrfToken = '';

        const csrfInput = document.querySelector('[name=csrfmiddlewaretoken]');
        if (csrfInput) {
            csrfToken = csrfInput.value;
        }
        
        if (!csrfToken) {
            const cookieValue = document.cookie
                .split('; ')
                .find(row => row.startsWith('csrftoken='))
                ?.split('=')[1];
            if (cookieValue) {
                csrfToken = cookieValue;
            }
        }

        if (!csrfToken) {
            const metaToken = document.querySelector('meta[name="csrf-token"]');
            if (metaToken) {
                csrfToken = metaToken.getAttribute('content');
            }
        }
        
        console.log('CSRF Token found:', csrfToken ? 'Yes' : 'No');
        return csrfToken;
    }

    function resetSubmitButton() {
        if (submitBtn) {
            submitBtn.disabled = false;
            submitBtn.textContent = 'Завершить тест';
        }
    }

    function showResultModal(data) {
        console.log('Showing result modal:', data);
        
        const modal = document.getElementById('resultModal');
        const resultContent = document.getElementById('resultContent');
        
        if (!modal || !resultContent) {
            console.error('Modal elements not found, redirecting...');
            window.location.href = `/course/${data.course_id || ''}/study/`;
            return;
        }
        
        let resultHTML = '';
        
        if (data.grading_form === 'points') {
            resultHTML = `
                <div class="result-points">
                    <div class="result-score-large">${data.score}/${data.max_score}</div>
                    <div class="result-text">Вы набрали ${data.score} из ${data.max_score} возможных баллов</div>
                    <div class="result-passing">Проходной балл: ${data.passing_score}</div>
                    <div class="result-status ${data.passed ? 'status-passed' : 'status-failed'}">
                        ${data.passed ? 'Тест сдан!' : 'Тест не сдан'}
                    </div>
                </div>
            `;
        } else {
            resultHTML = `
                <div class="result-pass-fail">
                    <div class="result-status-large ${data.passed ? 'status-passed' : 'status-failed'}">
                        ${data.passed ? 'ЗАЧЁТ' : 'НЕЗАЧЁТ'}
                    </div>
                    <div class="result-text">
                        ${data.passed ? 'Поздравляем! Вы успешно сдали тест.' : 'К сожалению, вы не сдали тест.'}
                    </div>
                </div>
            `;
        }
        
        resultContent.innerHTML = resultHTML;
        modal.style.display = 'block';
        
        console.log('Modal displayed successfully');

        const closeModalHandler = function(event) {
            if (event.target === modal) {
                modal.style.display = 'none';
                modal.removeEventListener('click', closeModalHandler);
                window.location.href = `/course/${data.course_id || ''}/study/`;
            }
        };
        
        modal.addEventListener('click', closeModalHandler);
    }

    function init() {
        console.log('Starting test initialization...');
        showQuestion(0);
        updateProgress();
        updateNavigation();
        
        navButtons.forEach((btn, index) => {
            if (btn) {
                btn.addEventListener('click', () => showQuestion(index));
            }
        });
        
        questions.forEach((question, index) => {
            const inputs = question.querySelectorAll('input[type="radio"], input[type="checkbox"], textarea, select');
            inputs.forEach(input => {
                if (input) {
                    input.addEventListener('change', () => {
                        saveAnswer(index);
                        updateProgress();
                        updateNavigation();
                    });
                    
                    if (input.tagName === 'TEXTAREA') {
                        input.addEventListener('input', () => {
                            saveAnswer(index);
                            updateProgress();
                            updateNavigation();
                        });
                    }
                }
            });
        });

        console.log('Test initialized successfully');
    }

    init();
}

window.initTest = initTest;