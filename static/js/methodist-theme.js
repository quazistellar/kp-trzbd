class MethodistTheme {
    constructor() {
        this.theme = localStorage.getItem('methodist-theme') || 'light';
        this.init();
    }

    init() {
        this.applyTheme(this.theme);
        this.addThemeToggle();
        this.setupFormEnhancements();
    }

    applyTheme(theme) {
        document.documentElement.setAttribute('data-theme', theme);
        localStorage.setItem('methodist-theme', theme);
        
        const toggleBtn = document.querySelector('.methodist-theme-toggle-btn');
        if (toggleBtn) {
            const icon = toggleBtn.querySelector('i') || document.createElement('i');
            icon.className = theme === 'dark' ? 'fas fa-sun' : 'fas fa-moon';
            if (!toggleBtn.querySelector('i')) {
                toggleBtn.appendChild(icon);
            }
        }
    }

    toggleTheme() {
        this.theme = this.theme === 'light' ? 'dark' : 'light';
        this.applyTheme(this.theme);
    }

    addThemeToggle() {
        if (document.querySelector('.methodist-theme-toggle')) return;

        const toggleBtn = document.createElement('button');
        toggleBtn.className = 'methodist-theme-toggle-btn';
        toggleBtn.innerHTML = '<i class="fas fa-moon"></i>';
        toggleBtn.addEventListener('click', () => this.toggleTheme());

        const toggleContainer = document.createElement('div');
        toggleContainer.className = 'methodist-theme-toggle';
        toggleContainer.appendChild(toggleBtn);

        document.body.appendChild(toggleContainer);
    }

    setupFormEnhancements() {
        const gradingTypeSelects = document.querySelectorAll('select[name="grading_type"], select[name="grading_form"]');
        
        gradingTypeSelects.forEach(select => {
            select.addEventListener('change', function() {
                const maxScoreField = this.closest('form').querySelector('input[name="max_score"]');
                const passingScoreField = this.closest('form').querySelector('input[name="passing_score"]');
                
                if (this.value === 'points') {
                    if (maxScoreField) {
                        maxScoreField.disabled = false;
                        maxScoreField.required = true;
                    }
                    if (passingScoreField) {
                        passingScoreField.disabled = false;
                        passingScoreField.required = true;
                    }
                } else {
                    if (maxScoreField) {
                        maxScoreField.disabled = true;
                        maxScoreField.required = false;
                        maxScoreField.value = '';
                    }
                    if (passingScoreField) {
                        passingScoreField.disabled = true;
                        passingScoreField.required = false;
                        passingScoreField.value = '';
                    }
                }
            });
            
            select.dispatchEvent(new Event('change'));
        });

        const fileInputs = document.querySelectorAll('input[type="file"]');
        fileInputs.forEach(input => {
            input.addEventListener('change', function() {
                const fileName = this.files[0]?.name || 'Файл не выбран';
                console.log('Selected file:', fileName);
            });
        });

        const deleteButtons = document.querySelectorAll('.methodist-btn-danger');
        deleteButtons.forEach(button => {
            button.addEventListener('click', function(e) {
                if (!confirm('Вы уверены, что хотите выполнить это действие?')) {
                    e.preventDefault();
                }
            });
        });
    }
}

document.addEventListener('DOMContentLoaded', () => {
    new MethodistTheme();
});