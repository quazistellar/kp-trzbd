function truncateDescriptions() {
    const descriptions = document.querySelectorAll('.course-description');
    descriptions.forEach(description => {
        const container = description.parentNode;
        const maxHeight = container.offsetHeight;
        let text = description.dataset.fulltext || description.textContent;

        description.textContent = text;

        if (description.scrollHeight > maxHeight) {
            let truncated = '';
            const words = text.split(' ');
            for (let i = 0; i < words.length; i++) {
                const testText = words.slice(0, i + 1).join(' ');
                description.textContent = testText;
                if (description.scrollHeight > maxHeight) {
                    description.textContent = truncated + '...';
                    break;
                }
                truncated = testText;
            }
        }
    });
}

document.addEventListener('DOMContentLoaded', truncateDescriptions);
window.addEventListener('resize', truncateDescriptions);