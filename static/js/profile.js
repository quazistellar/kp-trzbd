document.addEventListener('DOMContentLoaded', function() {
    console.log('Profile page loaded');

    function initializeProgressCircles() {
        const progressCircles = document.querySelectorAll('.profile-progress-circle');
        
        progressCircles.forEach((circle, index) => {
            const progress = parseFloat(circle.getAttribute('data-progress')) || 0;
            const progressText = circle.querySelector('.profile-progress-text');
            
            console.log(`Circle ${index}: data-progress="${progress}"`);
            
            circle.style.setProperty('--progress', progress + '%');
            
            if (progressText) {
                progressText.textContent = Math.round(progress) + '%';
            }
            
            setTimeout(() => {
                circle.style.transition = '--progress 1s ease-in-out';
            }, index * 100);
        });
    }

    const navItems = document.querySelectorAll('.nav-item[href^="#"]');
    const tabContents = document.querySelectorAll('.tab-content');

    navItems.forEach(item => {
        item.addEventListener('click', function(e) {
            e.preventDefault();

            navItems.forEach(nav => nav.classList.remove('active'));
            tabContents.forEach(tab => tab.classList.remove('active'));

            this.classList.add('active');
            const tabId = this.getAttribute('data-tab');
            const targetTab = document.getElementById(tabId + '-tab');
            if (targetTab) {
                targetTab.classList.add('active');
            }

            if (tabId === 'analytics') {
                setTimeout(initializeCharts, 100);
            }
            
            setTimeout(initializeProgressCircles, 150);
        });
    });

    function initializeCharts() {

        const dataEl = document.getElementById('analytics-data-json');
        if (!dataEl) {
            return;
        }

        let analyticsData;
        try {
            analyticsData = JSON.parse(dataEl.textContent);
        } catch (e) {
            return;
        }


        const activityCtx = document.getElementById('activityChart');
        if (activityCtx) {
            const labels = analyticsData.daily_activity_labels || [];
            const data = analyticsData.daily_activity_data || [];

            if (activityCtx.chart) activityCtx.chart.destroy();

            activityCtx.chart = new Chart(activityCtx, {
                type: 'line',
                data: {
                    labels: labels,
                    datasets: [{
                        label: 'Активность пользователей (входы)',
                        data: data,
                        borderColor: '#4CAF50',
                        backgroundColor: 'rgba(76, 175, 80, 0.1)',
                        tension: 0.4,
                        fill: true,
                        borderWidth: 2
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        legend: { display: true, position: 'top' },
                        tooltip: {
                            callbacks: { label: ctx => `Пользователей: ${ctx.raw}` }
                        }
                    },
                    scales: {
                        y: { beginAtZero: true, title: { display: true, text: 'Количество' }, ticks: { stepSize: 1 } },
                        x: { title: { display: true, text: 'Дата' } }
                    }
                }
            });
            console.log('Activity chart initialized');
        }

        const coursesCtx = document.getElementById('coursesChart');
        if (coursesCtx) {
            const stats = analyticsData.course_stats || [];
            const names = stats.map(s => s.course_name);
            const total = stats.map(s => s.total_students);
            const completed = stats.map(s => s.completed_students);

            if (coursesCtx.chart) coursesCtx.chart.destroy();

            coursesCtx.chart = new Chart(coursesCtx, {
                type: 'bar',
                data: {
                    labels: names,
                    datasets: [
                        {
                            label: 'Всего слушателей',
                            data: total,
                            backgroundColor: 'rgba(54, 162, 235, 0.6)',
                            borderColor: 'rgba(54, 162, 235, 1)',
                            borderWidth: 1
                        },
                        {
                            label: 'Завершили курс',
                            data: completed,
                            backgroundColor: 'rgba(75, 192, 192, 0.6)',
                            borderColor: 'rgba(75, 192, 192, 1)',
                            borderWidth: 1
                        }
                    ]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        legend: { display: true, position: 'top' },
                        tooltip: {
                            callbacks: { label: ctx => `${ctx.dataset.label}: ${ctx.raw}` }
                        }
                    },
                    scales: {
                        y: { beginAtZero: true, title: { display: true, text: 'Количество' }, ticks: { stepSize: 1 } }
                    }
                }
            });
            console.log('Courses chart initialized');
        }
    }

    if (document.getElementById('analytics-tab')?.classList.contains('active')) {
        setTimeout(initializeCharts, 100);
    }

    const passwordForm = document.querySelector('.profile-security-form');
    if (passwordForm) {
        passwordForm.addEventListener('submit', function(e) {
            const new1 = document.getElementById('new_password1').value;
            const new2 = document.getElementById('new_password2').value;
            if (new1 !== new2) {
                e.preventDefault();
                showNotification('Пароли не совпадают', 'error');
            } else if (new1.length < 8) {
                e.preventDefault();
                showNotification('Пароль должен быть не менее 8 символов', 'error');
            }
        });
    }

    const profileForm = document.querySelector('input[name="profile_update"]')?.closest('form');
    if (profileForm) {
        profileForm.addEventListener('submit', function(e) {
            const username = document.getElementById('username').value.trim();
            if (!username) {
                e.preventDefault();
                showNotification('Имя пользователя обязательно', 'error');
            }
        });
    }

    setTimeout(() => {
        document.querySelectorAll('.profile-bar').forEach(bar => {
            const height = bar.style.height;
            bar.style.height = '0%';
            setTimeout(() => bar.style.height = height, 100);
        });
    }, 500);

    function showNotification(message, type) {
        const existing = document.querySelectorAll('.notification');
        existing.forEach(n => n.remove());

        const notification = document.createElement('div');
        notification.className = `notification ${type}`;
        notification.textContent = message;
        notification.style.cssText = `
            position: fixed; top: 20px; right: 20px; padding: 1rem 1.5rem;
            background: ${type === 'error' ? '#ff4444' : '#4CAF50'};
            color: white; border-radius: 8px; z-index: 1000; box-shadow: 0 4px 12px rgba(0,0,0,0.15);
            font-family: inherit;
        `;
        document.body.appendChild(notification);
        setTimeout(() => notification.remove(), 3000);
    }

    document.querySelectorAll('.alert, .message').forEach(msg => {
        const type = msg.classList.contains('error') || msg.classList.contains('alert-danger') ? 'error' : 'success';
        showNotification(msg.textContent.trim(), type);
        setTimeout(() => msg.remove(), 100);
    });

    initializeProgressCircles();
    setTimeout(initializeProgressCircles, 500);

});