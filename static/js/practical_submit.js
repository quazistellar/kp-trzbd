document.addEventListener('DOMContentLoaded', function() {
    const fileInput = document.getElementById('submission_files');
    const fileUploadArea = document.getElementById('fileUploadArea');
    const filesList = document.getElementById('filesList');
    const submitBtn = document.getElementById('submitBtn');
    const submitForm = document.getElementById('submitForm');
    const MAX_FILE_SIZE = 50 * 1024 * 1024; 
    const ALLOWED_EXTENSIONS = ['.pdf', '.doc', '.docx', '.zip'];

    function formatFileSize(bytes) {
        if (bytes === 0) return '0 Bytes';
        const k = 1024;
        const sizes = ['Bytes', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
    }

    function isValidFileType(fileName) {
        const extension = fileName.toLowerCase().substring(fileName.lastIndexOf('.'));
        return ALLOWED_EXTENSIONS.includes(extension);
    }

    function displayFiles(files) {
        filesList.innerHTML = '';
        
        Array.from(files).forEach((file, index) => {
            const fileItem = document.createElement('div');
            fileItem.className = 'file-item';
            
            const fileInfo = document.createElement('div');
            fileInfo.className = 'file-info';
            
            const fileName = document.createElement('span');
            fileName.className = 'file-name';
            fileName.textContent = file.name;
            
            const fileSize = document.createElement('span');
            fileSize.className = 'file-size';
            fileSize.textContent = formatFileSize(file.size);
            
            const removeBtn = document.createElement('button');
            removeBtn.type = 'button';
            removeBtn.className = 'remove-file';
            removeBtn.innerHTML = '×';
            removeBtn.onclick = function() {
                removeFile(index);
            };
            
            fileInfo.appendChild(fileName);
            fileInfo.appendChild(fileSize);
            fileItem.appendChild(fileInfo);
            fileItem.appendChild(removeBtn);
            filesList.appendChild(fileItem);
        });
    }

    function removeFile(index) {
        const dt = new DataTransfer();
        const files = Array.from(fileInput.files);
        files.splice(index, 1);
        
        files.forEach(file => dt.items.add(file));
        fileInput.files = dt.files;
        displayFiles(fileInput.files);
    }

    fileInput.addEventListener('change', function(e) {
        const files = Array.from(e.target.files);
        let validFiles = [];
        let hasErrors = false;

        files.forEach(file => {
            if (file.size > MAX_FILE_SIZE) {
                alert(`Файл "${file.name}" слишком большой. Максимальный размер: 50 МБ`);
                hasErrors = true;
                return;
            }
            
            if (!isValidFileType(file.name)) {
                alert(`Файл "${file.name}" имеет неподдерживаемый формат. Разрешены: PDF, DOC, DOCX, ZIP`);
                hasErrors = true;
                return;
            }
            
            validFiles.push(file);
        });

        if (hasErrors) {
            const dt = new DataTransfer();
            validFiles.forEach(file => dt.items.add(file));
            fileInput.files = dt.files;
        }
        
        displayFiles(fileInput.files);
    });

    ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
        fileUploadArea.addEventListener(eventName, preventDefaults, false);
    });

    function preventDefaults(e) {
        e.preventDefault();
        e.stopPropagation();
    }

    ['dragenter', 'dragover'].forEach(eventName => {
        fileUploadArea.addEventListener(eventName, highlight, false);
    });

    ['dragleave', 'drop'].forEach(eventName => {
        fileUploadArea.addEventListener(eventName, unhighlight, false);
    });

    function highlight() {
        fileUploadArea.classList.add('highlight');
    }

    function unhighlight() {
        fileUploadArea.classList.remove('highlight');
    }

    fileUploadArea.addEventListener('drop', handleDrop, false);

    function handleDrop(e) {
        const dt = e.dataTransfer;
        const files = dt.files;
        fileInput.files = files;
        fileInput.dispatchEvent(new Event('change'));
    }

    submitForm.addEventListener('submit', function(e) {
        const files = fileInput.files;
        
        if (files.length === 0) {
            e.preventDefault();
            alert('Пожалуйста, прикрепите хотя бы один файл');
            return;
        }
        
        submitBtn.disabled = true;
        submitBtn.innerHTML = '<span class="loading-spinner"></span> Отправка...';
    });
});