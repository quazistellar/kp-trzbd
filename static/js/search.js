document.addEventListener('DOMContentLoaded', function() {
    const searchInput = document.getElementById('search-input');
    const searchButton = document.getElementById('search-button');
    const searchResultsContainer = document.getElementById('search-results-desktop');

    searchInput.addEventListener('input', function() {
        const query = this.value.trim();
        if (query.length >= 2) { 
            fetchSearchResults(query);
        } else {
            clearSearchResults();
        }
    });

    searchButton.addEventListener('click', function() {
        const query = searchInput.value.trim();
         if (query.length >= 2) { 
            fetchSearchResults(query);
        } else {
            clearSearchResults();
        }
    });

    function fetchSearchResults(query) {
        fetch(`/search/?q=${query}`) 
            .then(response => response.json())
            .then(data => {
                displaySearchResults(data);
            })
            .catch(error => {
                console.error('Error fetching search results:', error);
                searchResultsContainer.innerHTML = '<p>Ошибка при поиске.</p>';
                searchResultsContainer.classList.add('active');
            });
    }

    function displaySearchResults(results) {
        searchResultsContainer.innerHTML = ''; 
        if (results.length > 0) {
            results.forEach(result => {
                const resultItem = document.createElement('div');
                resultItem.classList.add('search-result-item');
                resultItem.innerHTML = `
                    <img src="${result.image}" alt="${result.name}" style="width: 50px; height: 50px; margin-right: 10px; border-radius: 5px;">
                    <span>${result.name}</span>
                `;
                resultItem.addEventListener('click', function() {
                    window.location.href = result.url; 
                });
                searchResultsContainer.appendChild(resultItem);
            });
            searchResultsContainer.classList.add('active');
        } else {
            searchResultsContainer.innerHTML = '<p>Ничего не найдено.</p>';
            searchResultsContainer.classList.add('active');
        }
    }

    function clearSearchResults() {
        searchResultsContainer.innerHTML = '';
        searchResultsContainer.classList.remove('active');
    }
});