document.addEventListener('DOMContentLoaded', function() {
    const navItems = document.querySelectorAll('.study-nav-item');
    const tabContents = document.querySelectorAll('.study-tab-content');
    
    navItems.forEach(item => {
        item.addEventListener('click', function(e) {
            e.preventDefault();
            
            navItems.forEach(nav => nav.classList.remove('active'));
            tabContents.forEach(tab => tab.classList.remove('active'));
            
            this.classList.add('active');
            
            const tabId = this.getAttribute('data-tab') + '-tab';
            const targetTab = document.getElementById(tabId);
            if (targetTab) {
                targetTab.classList.add('active');
            }
        });
    });
    
    const lectureModal = document.getElementById('lectureModal');
    const openLectureButtons = document.querySelectorAll('.open-lecture');
    const closeModalButton = document.querySelector('.study-modal-close');
    
    function openLectureModal(lectureId) {
        window.location.href = `/lecture/${lectureId}/`;
    }
    
    function closeModal() {
        lectureModal.classList.remove('active');
    }
    
    openLectureButtons.forEach(button => {
        button.addEventListener('click', function() {
            const lectureId = this.getAttribute('data-lecture-id');
            openLectureModal(lectureId);
        });
    });
    
    closeModalButton.addEventListener('click', closeModal);
    
    lectureModal.addEventListener('click', function(e) {
        if (e.target === lectureModal) {
            closeModal();
        }
    });
    
    const submitAssignmentButtons = document.querySelectorAll('.submit-assignment');
    
    submitAssignmentButtons.forEach(button => {
        button.addEventListener('click', function() {
            const assignmentId = this.getAttribute('data-assignment-id');
            window.location.href = `/practical/submit/${assignmentId}/`;
        });
    });
    
    const startTestButtons = document.querySelectorAll('.start-test');
    
    startTestButtons.forEach(button => {
        button.addEventListener('click', function() {
            const testId = this.getAttribute('data-test-id');
            window.location.href = `/test/start/${testId}/`;
        });
    });
    
    const deadlineItems = document.querySelectorAll('.deadline-item');
    
    deadlineItems.forEach(item => {
        item.addEventListener('click', function() {
            const type = this.classList.contains('deadline-practical') ? 'practical' : 'test';
            const id = this.getAttribute('data-id');
            
            if (type === 'practical') {
                window.location.href = `/practical/submit/${id}/`;
            } else {
                window.location.href = `/test/start/${id}/`;
            }
        });
    });
    
    const progressBars = document.querySelectorAll('.progress-fill');
    progressBars.forEach(bar => {
        const width = bar.style.width;
        bar.style.width = '0';
        setTimeout(() => {
            bar.style.width = width;
        }, 100);
    });
    
    const downloadButtons = document.querySelectorAll('.study-btn-outline[href]');
    downloadButtons.forEach(button => {
        button.addEventListener('click', function(e) {

        });
    });
});