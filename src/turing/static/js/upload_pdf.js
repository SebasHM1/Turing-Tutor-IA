document.addEventListener('DOMContentLoaded', function () {
    const fileInput = document.querySelector('.file-input');
    const uploadArea = document.getElementById('upload-area');

    if (!fileInput || !uploadArea) return;

    const uploadLabel = uploadArea.querySelector('.upload-label');
    const uploadText = uploadArea.querySelector('.upload-text');
    const fileSelected = uploadArea.querySelector('.file-selected');
    const fileName = uploadArea.querySelector('.file-name');

    // Actualizar UI cuando se selecciona un archivo
    fileInput.addEventListener('change', function (e) {
        if (this.files && this.files[0]) {
            const file = this.files[0];
            fileName.textContent = file.name;
            uploadText.style.display = 'none';
            fileSelected.style.display = 'flex';
            uploadArea.classList.add('has-file');
        }
    });

    // Drag and drop
    ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
        uploadArea.addEventListener(eventName, preventDefaults, false);
    });

    function preventDefaults(e) {
        e.preventDefault();
        e.stopPropagation();
    }

    ['dragenter', 'dragover'].forEach(eventName => {
        uploadArea.addEventListener(eventName, () => {
            uploadArea.classList.add('drag-over');
        }, false);
    });

    ['dragleave', 'drop'].forEach(eventName => {
        uploadArea.addEventListener(eventName, () => {
            uploadArea.classList.remove('drag-over');
        }, false);
    });

    uploadArea.addEventListener('drop', function (e) {
        const dt = e.dataTransfer;
        const files = dt.files;

        if (files.length > 0 && files[0].type === 'application/pdf') {
            fileInput.files = files;
            const event = new Event('change', { bubbles: true });
            fileInput.dispatchEvent(event);
        }
    }, false);
});