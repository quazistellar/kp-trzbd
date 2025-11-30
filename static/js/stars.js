document.addEventListener('DOMContentLoaded', () => {
  const backgroundElements = document.querySelector('.background-elements');
  const numberOfStars = 35;

  for (let i = 0; i < numberOfStars; i++) {
    const star = document.createElement('div');
    star.classList.add('star');

    const x = Math.random() * (100 - 2); 
    const y = Math.random() * 100;
    const delay = Math.random() * 30;
    const duration = 5 + Math.random() * 5;

    star.style.left = `${x}%`;
    star.style.top = `${y}%`;
    star.style.setProperty('--star-delay', `-${delay}s`);
    star.style.setProperty('--star-duration', `${duration}s`);
    star.style.setProperty('--vertical-offset', `${(Math.random() - 0.5) * 50}px`);

    backgroundElements.appendChild(star);
  }

  const numberOfFallingStars = 5;
  for (let i = 0; i < numberOfFallingStars; i++) {
    const fallingStar = document.createElement('div');
    fallingStar.classList.add('falling-star');

    const startX = Math.random() * (100 - 2); 
    const delay = Math.random() * 5;
    const horizontalOffset = (Math.random() - 0.5) * 20;

    fallingStar.style.left = `${startX}%`;
    fallingStar.style.setProperty('--star-delay', `-${delay}s`);
    fallingStar.style.setProperty('--horizontal-offset', `${horizontalOffset}px`); 

    backgroundElements.appendChild(fallingStar);
  }
});