document.addEventListener('DOMContentLoaded', function() {
    const filterRadios = document.querySelectorAll('input[name="resultFilter"]');
    const resultCards = document.querySelectorAll('.result-card');

    filterRadios.forEach(radio => {
        radio.addEventListener('change', function() {
            const filterValue = this.value;
            
            resultCards.forEach(card => {
                const cardStatus = card.getAttribute('data-status');
                
                if (filterValue === 'all') {
                    card.style.display = 'flex';
                } else if (filterValue === 'passed') {
                    card.style.display = cardStatus === 'passed' ? 'flex' : 'none';
                } else if (filterValue === 'failed') {
                    card.style.display = cardStatus === 'failed' ? 'flex' : 'none';
                }
            });
        });
    });

    const observerOptions = {
        threshold: 0.1,
        rootMargin: '0px 0px -50px 0px'
    };

    const observer = new IntersectionObserver(function(entries) {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                entry.target.style.opacity = '1';
                entry.target.style.transform = 'translateY(0)';
            }
        });
    }, observerOptions);

    resultCards.forEach((card, index) => {
        card.style.opacity = '0';
        card.style.transform = 'translateY(20px)';
        card.style.transition = `opacity 0.5s ease ${index * 0.1}s, transform 0.5s ease ${index * 0.1}s`;
        
        observer.observe(card);
    });

    filterRadios.forEach(radio => {
        radio.addEventListener('change', function() {
            document.querySelectorAll('.filter-option').forEach(option => {
                option.classList.remove('active');
            });
            this.closest('.filter-option').classList.add('active');
        });
    });

    const activeFilter = document.querySelector('input[name="resultFilter"]:checked');
    if (activeFilter) {
        activeFilter.closest('.filter-option').classList.add('active');
    }

    filterRadios.forEach(radio => {
        radio.addEventListener('change', function() {
            const resultsMain = document.querySelector('.results-main');
            if (resultsMain) {
                window.scrollTo({
                    top: resultsMain.offsetTop - 20,
                    behavior: 'smooth'
                });
            }
        });
    });

    const retryButtons = document.querySelectorAll('.retry-btn');
    retryButtons.forEach(button => {
        button.addEventListener('click', function(e) {
            if (!confirm('Вы уверены, что хотите пересдать этот тест? Результаты предыдущей попытки будут сохранены.')) {
                e.preventDefault();
            }
        });
    });

    resultCards.forEach(card => {
        card.addEventListener('mouseenter', function() {
            this.style.transform = 'translateY(-5px)';
            this.style.boxShadow = '0 8px 25px rgba(0,0,0,0.15)';
        });
        
        card.addEventListener('mouseleave', function() {
            this.style.transform = 'translateY(0)';
            this.style.boxShadow = '0 2px 10px rgba(0,0,0,0.1)';
        });
    });

    const statItems = document.querySelectorAll('.stat-item');
    statItems.forEach((item, index) => {
        item.style.opacity = '0';
        item.style.transform = 'translateX(-20px)';
        
        setTimeout(() => {
            item.style.transition = `opacity 0.5s ease ${index * 0.2}s, transform 0.5s ease ${index * 0.2}s`;
            item.style.opacity = '1';
            item.style.transform = 'translateX(0)';
        }, 100);
    });

    console.log('Test results page initialized');
});