// Form event handlers and interactions

/**
 * Initialize form handlers when DOM is loaded
 */
document.addEventListener('DOMContentLoaded', function() {
    initializeFormHandlers();
});

/**
 * Set up all form event listeners
 */
function initializeFormHandlers() {
    setupTemplateSelection();
    setupRecurringOptions();
}

/**
 * Handle template selection changes
 */
function setupTemplateSelection() {
    const templateSelect = document.getElementById('template_id');
    const customFields = document.getElementById('custom_text_fields');
    
    if (templateSelect && customFields) {
        templateSelect.addEventListener('change', function() {
            if (this.value === '') {
                customFields.style.display = 'block';
            } else {
                customFields.style.display = 'none';
            }
        });
    }
}

/**
 * Handle recurring schedule options
 */
function setupRecurringOptions() {
    const recurringCheckbox = document.getElementById('is_recurring');
    const recurringOptions = document.getElementById('recurring_options');
    const datetimeField = document.getElementById('datetime_field');
    const datetimeInput = document.getElementById('scheduled_datetime');
    
    if (recurringCheckbox && recurringOptions && datetimeField && datetimeInput) {
        recurringCheckbox.addEventListener('change', function() {
            if (this.checked) {
                recurringOptions.style.display = 'block';
                datetimeField.style.display = 'none';
                datetimeInput.removeAttribute('required');
            } else {
                recurringOptions.style.display = 'none';
                datetimeField.style.display = 'block';
                datetimeInput.setAttribute('required', 'required');
            }
        });
    }
}