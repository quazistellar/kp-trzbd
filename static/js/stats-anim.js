document.addEventListener('DOMContentLoaded', function() {
    initializeStats();
    loadPlatformStats();
});

function loadPlatformStats() {
    showLoadingState();
    
    fetch('/api/platform-stats/stats/')
        .then(response => {
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            return response.json();
        })
        .then(data => {
            let stats = null;
            
            if (data && data.data && typeof data.data === 'object') {
                stats = data.data;
            }
            else if (data && typeof data === 'object') {
                stats = data;
            }
            
            if (stats) {
                const students = parseStatValue(stats.students);
                const courses = parseStatValue(stats.courses);
                
                if (students !== null && courses !== null) {
                    updateStatsCounter('students-count', students);
                    updateStatsCounter('courses-count', courses);
                    return;
                }
            }
            
            showErrorState();
        })
        .catch(error => {
            console.error('Ошибка при загрузке статистики:', error);
            showErrorState();
        });
}

function parseStatValue(value) {
    if (value === null || value === undefined) {
        return null;
    }
    
    if (typeof value === 'number') {
        return value >= 0 ? value : null;
    }
    
    if (typeof value === 'string') {
        const cleaned = value.trim().replace(/\s/g, '');
        const parsed = parseInt(cleaned);
        return !isNaN(parsed) && parsed >= 0 ? parsed : null;
    }
    
    return null;
}

function showLoadingState() {
    setStaticValue('students-count', '...');
    setStaticValue('courses-count', '...');
}

function showErrorState() {
    setStaticValue('students-count', '—');
    setStaticValue('courses-count', '—');
}

function setStaticValue(elementId, value) {
    const element = document.getElementById(elementId);
    if (element) {
        element.textContent = value;
    }
}

function updateStatsCounter(elementId, newValue) {
    const element = document.getElementById(elementId);
    if (element) {
        element.textContent = newValue.toLocaleString('ru-RU');
    }
}

function initializeStats() {
    setStaticValue('students-count', '0');
    setStaticValue('courses-count', '0');
}