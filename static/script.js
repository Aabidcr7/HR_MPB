// HR Management System JavaScript

document.addEventListener('DOMContentLoaded', function() {
    // Initialize tooltips
    var tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    var tooltipList = tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });

    // File upload validation
    const fileInputs = document.querySelectorAll('input[type="file"]');
    fileInputs.forEach(input => {
        input.addEventListener('change', function(e) {
            const file = e.target.files[0];
            if (file) {
                const maxSize = 10 * 1024 * 1024; // 10MB
                const allowedTypes = ['application/pdf', 'application/msword', 
                                    'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
                                    'text/csv'];
                
                if (file.size > maxSize) {
                    alert('File size must be less than 10MB');
                    e.target.value = '';
                    return;
                }
                
                if (input.accept && !allowedTypes.some(type => file.type === type)) {
                    alert('Please select a valid file type');
                    e.target.value = '';
                    return;
                }
                
                // Show file name
                const fileName = file.name;
                const fileNameSpan = input.parentNode.querySelector('.file-name');
                if (fileNameSpan) {
                    fileNameSpan.textContent = fileName;
                } else {
                    const span = document.createElement('small');
                    span.className = 'file-name text-muted d-block mt-1';
                    span.textContent = fileName;
                    input.parentNode.appendChild(span);
                }
            }
        });
    });

    // Form validation
    const forms = document.querySelectorAll('form');
    forms.forEach(form => {
        form.addEventListener('submit', function(e) {
            if (!form.checkValidity()) {
                e.preventDefault();
                e.stopPropagation();
            }
            form.classList.add('was-validated');
        });
    });

    // Auto-calculate overall score in screening/interview forms
    const scoreInputs = document.querySelectorAll('input[name$="_score"]:not([name="overall_score"])');
    const overallScoreInput = document.querySelector('input[name="overall_score"]');
    
    if (scoreInputs.length > 0 && overallScoreInput) {
        scoreInputs.forEach(input => {
            input.addEventListener('input', function() {
                let total = 0;
                let count = 0;
                
                scoreInputs.forEach(scoreInput => {
                    const value = parseFloat(scoreInput.value);
                    if (!isNaN(value)) {
                        total += value;
                        count++;
                    }
                });
                
                if (count > 0) {
                    const average = (total / count).toFixed(1);
                    overallScoreInput.value = average;
                }
            });
        });
    }

    // Confirm dialogs for destructive actions
    const dangerButtons = document.querySelectorAll('.btn-danger, .btn-outline-danger');
    dangerButtons.forEach(button => {
        if (!button.hasAttribute('onclick')) {
            button.addEventListener('click', function(e) {
                if (!confirm('Are you sure you want to perform this action?')) {
                    e.preventDefault();
                }
            });
        }
    });

    // Auto-dismiss alerts after 5 seconds
    const alerts = document.querySelectorAll('.alert:not(.alert-info):not(.alert-warning)');
    alerts.forEach(alert => {
        setTimeout(() => {
            const bsAlert = new bootstrap.Alert(alert);
            bsAlert.close();
        }, 5000);
    });

    // Dynamic form field dependencies
    const reasonSelect = document.querySelector('select[name="reason"]');
    if (reasonSelect) {
        reasonSelect.addEventListener('change', function() {
            const otherReasonGroup = document.querySelector('.other-reason-group');
            if (this.value === 'Other') {
                if (!otherReasonGroup) {
                    const div = document.createElement('div');
                    div.className = 'mb-3 other-reason-group';
                    div.innerHTML = `
                        <label class="form-label">Please specify:</label>
                        <input type="text" class="form-control" name="other_reason" required>
                    `;
                    this.parentNode.insertAdjacentElement('afterend', div);
                }
            } else if (otherReasonGroup) {
                otherReasonGroup.remove();
            }
        });
    }

    // Progress bar animation
    const progressBars = document.querySelectorAll('.progress-bar');
    progressBars.forEach(bar => {
        const width = bar.style.width;
        bar.style.width = '0%';
        setTimeout(() => {
            bar.style.width = width;
            bar.style.transition = 'width 1s ease-in-out';
        }, 100);
    });

    // Enhanced table sorting (simple implementation)
    const tableHeaders = document.querySelectorAll('th[data-sort]');
    tableHeaders.forEach(header => {
        header.style.cursor = 'pointer';
        header.addEventListener('click', function() {
            const table = this.closest('table');
            const tbody = table.querySelector('tbody');
            const rows = Array.from(tbody.querySelectorAll('tr'));
            const column = this.dataset.sort;
            const isAscending = !this.classList.contains('sort-asc');
            
            // Remove existing sort classes
            tableHeaders.forEach(h => h.classList.remove('sort-asc', 'sort-desc'));
            
            // Add current sort class
            this.classList.add(isAscending ? 'sort-asc' : 'sort-desc');
            
            // Sort rows
            rows.sort((a, b) => {
                const aVal = a.querySelector(`td:nth-child(${this.cellIndex + 1})`).textContent.trim();
                const bVal = b.querySelector(`td:nth-child(${this.cellIndex + 1})`).textContent.trim();
                
                if (isAscending) {
                    return aVal.localeCompare(bVal, undefined, {numeric: true});
                } else {
                    return bVal.localeCompare(aVal, undefined, {numeric: true});
                }
            });
            
            // Append sorted rows
            rows.forEach(row => tbody.appendChild(row));
        });
    });

    // Keyboard shortcuts
    document.addEventListener('keydown', function(e) {
        // Ctrl+N for new requisition
        if (e.ctrlKey && e.key === 'n') {
            e.preventDefault();
            const newReqButton = document.querySelector('[data-bs-target="#createRequisitionModal"]');
            if (newReqButton) {
                newReqButton.click();
            }
        }
        
        // Escape to close modals
        if (e.key === 'Escape') {
            const openModals = document.querySelectorAll('.modal.show');
            openModals.forEach(modal => {
                const bsModal = bootstrap.Modal.getInstance(modal);
                if (bsModal) {
                    bsModal.hide();
                }
            });
        }
    });

    // Auto-save form data to localStorage (for longer forms)
    const longForms = document.querySelectorAll('form[data-autosave]');
    longForms.forEach(form => {
        const formId = form.dataset.autosave;
        
        // Load saved data
        const savedData = localStorage.getItem(`form_${formId}`);
        if (savedData) {
            const data = JSON.parse(savedData);
            Object.keys(data).forEach(key => {
                const input = form.querySelector(`[name="${key}"]`);
                if (input) {
                    input.value = data[key];
                }
            });
        }
        
        // Save data on input
        form.addEventListener('input', function() {
            const formData = new FormData(form);
            const data = {};
            for (let [key, value] of formData.entries()) {
                data[key] = value;
            }
            localStorage.setItem(`form_${formId}`, JSON.stringify(data));
        });
        
        // Clear saved data on submit
        form.addEventListener('submit', function() {
            localStorage.removeItem(`form_${formId}`);
        });
    });
});

// Utility functions
function showLoading(element) {
    const originalText = element.textContent;
    element.textContent = 'Loading...';
    element.disabled = true;
    return () => {
        element.textContent = originalText;
        element.disabled = false;
    };
}

function formatDate(dateString) {
    return new Date(dateString).toLocaleDateString();
}

function formatCurrency(amount) {
    return new Intl.NumberFormat('en-US', {
        style: 'currency',
        currency: 'USD'
    }).format(amount);
}

// Export for use in other scripts
window.HRSystem = {
    showLoading,
    formatDate,
    formatCurrency
};
