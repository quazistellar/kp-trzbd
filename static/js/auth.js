document.addEventListener('DOMContentLoaded', () => {
    const inputs = document.querySelectorAll('.auth-field input');
    inputs.forEach(input => {
        input.addEventListener('focus', () => {
            input.parentElement.classList.add('focused');
        });
        input.addEventListener('blur', () => {
            if (!input.value) {
                input.parentElement.classList.remove('focused');
            }
        });
    });

    const background = document.querySelector('.background-elements');
    if (background) {
        for (let i = 0; i < 50; i++) { 
            const star = document.createElement('div');
            star.classList.add('star');
            star.style.top = `${Math.random() * 100}%`;
            star.style.left = `${Math.random() * 100}%`;
            star.style.animationDelay = `${Math.random() * 2}s`;
            background.appendChild(star);
        }

        for (let i = 0; i < 10; i++) { 
            const fallingStar = document.createElement('div');
            fallingStar.classList.add('falling-star');
            fallingStar.style.left = `${Math.random() * 100}%`;
            fallingStar.style.animationDelay = `${Math.random() * 5}s`;
            background.appendChild(fallingStar);
        }
    }
});