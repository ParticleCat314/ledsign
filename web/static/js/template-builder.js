// Template builder functionality

let textItemIndex = 1;

/**
 * Initialize template builder when DOM is loaded
 */
document.addEventListener('DOMContentLoaded', function() {
    initializeTemplateBuilder();
});

/**
 * Set up template builder functionality
 */
function initializeTemplateBuilder() {
    // Initialize the first element's special fields (initially hidden)
    updateSpecialFields(0, 'static');
}

/**
 * Update special fields for a specific text item based on element type
 * @param {number} index - The index of the text item
 * @param {string} elementType - The type of element (static, scrolling, animation)
 */
function updateSpecialFields(index, elementType) {
    const specialFields = document.querySelector(`#special_fields_${index}`);
    if (specialFields) {
        specialFields.style.display = 'block';
        specialFields.innerHTML = getSpecialFields(elementType, index);
    }
}

/**
 * Add a new text item to the template builder
 */
function addTextItem() {
    const container = document.getElementById('text_items_container');
    
    if (!container) {
        console.error('Text items container not found');
        return;
    }
    
    const newItem = document.createElement('div');
    newItem.className = 'text-item';
    newItem.setAttribute('data-index', textItemIndex);
    
    newItem.innerHTML = `
        <h4>Text Item ${textItemIndex + 1} 
            <button type="button" class="remove-text-item" onclick="removeTextItem(${textItemIndex})">Remove</button>
        </h4>
        <div class="two-column">
            <div>
                <div class="form-group">
                    <label for="element_type_${textItemIndex}">Element Type:</label>
                    <select id="element_type_${textItemIndex}" name="element_type_${textItemIndex}" required onchange="updateSpecialFields(${textItemIndex}, this.value)">
                        <option value="static">Static Text</option>
                        <option value="scrolling">Scrolling Text</option>
                    </select>
                </div>
                <div class="form-group">
                    <label>Content:</label>
                    <input type="text" name="text_content_${textItemIndex}" required>
                </div>
                <div class="form-group">
                    <label>X Position:</label>
                    <input type="number" name="text_x_${textItemIndex}" value="0" min="0">
                </div>
                <div class="form-group">
                    <label>Y Position:</label>
                    <input type="number" name="text_y_${textItemIndex}" value="${(textItemIndex + 1) * 10}" min="0">
                </div>
            </div>
            <div>
                <div class="form-group">
                    <label>Color:</label>
                    <input type="color" name="text_color_${textItemIndex}" value="#ffff00">
                </div>
                <div id="special_fields_${textItemIndex}" class="template-type-fields" style="display: none;">
                    <!-- Special fields will be added here based on element type -->
                </div>
            </div>
        </div>
    `;
    
    container.appendChild(newItem);
    textItemIndex++;
}

/**
 * Remove a text item from the template builder
 * @param {number} index - The index of the text item to remove
 */
function removeTextItem(index) {
    const item = document.querySelector(`[data-index="${index}"]`);
    if (item) {
        item.remove();
    }
}