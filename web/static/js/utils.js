// Utility functions

/**
 * Convert color picker value to RGB array
 * @param {string} hex - Hex color value (e.g., "#ff0000")
 * @returns {number[]} RGB array [r, g, b]
 */
function colorToRgb(hex) {
    const result = /^#?([a-f\d]{2})([a-f\d]{2})([a-f\d]{2})$/i.exec(hex);
    return result ? [
        parseInt(result[1], 16),
        parseInt(result[2], 16),
        parseInt(result[3], 16)
    ] : [255, 255, 0];
}

/**
 * Get special fields HTML based on template type
 * @param {string} templateType - Type of template (static, scrolling, animation)
 * @param {number} index - Index for field naming
 * @returns {string} HTML string for special fields
 */
function getSpecialFields(templateType, index) {
    if (templateType === 'scrolling') {
        return `
            <div class="form-group">
                <label>Speed:</label>
                <input type="number" name="text_speed_${index}" value="50" min="1" max="200">
            </div>
            <div class="form-group">
                <label>Direction:</label>
                <select name="text_direction_${index}">
                    <option value="left">Left</option>
                    <option value="right">Right</option>
                </select>
            </div>
        `;
    } else if (templateType === 'animation') {
        return `
            <div class="form-group">
                <label>Effect:</label>
                <select name="text_effect_${index}">
                    <option value="blink">Blink</option>
                    <option value="fade">Fade</option>
                    <option value="rainbow">Rainbow</option>
                </select>
            </div>
            <div class="form-group">
                <label>Duration (seconds):</label>
                <input type="number" name="text_duration_${index}" value="5" min="1" max="60">
            </div>
        `;
    }
    return '';
}