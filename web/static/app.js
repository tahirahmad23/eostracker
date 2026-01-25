/**
 * EOS Tracker - Client-side JavaScript
 * Utilities and components for the application
 */

// Confirmation dialogs with custom messages
function confirmDelete(message = 'Are you sure you want to delete this?') {
    return confirm(message);
}

// Confirmation for removing devices
function confirmRemove(deviceName) {
    return confirm(`Are you sure you want to remove "${deviceName}" from tracking?`);
}

// Export utilities to global scope
window.confirmDelete = confirmDelete;
window.confirmRemove = confirmRemove;

// Initialize tooltips if needed (for future enhancement)
document.addEventListener('DOMContentLoaded', function() {
    // Add any initialization code here
    console.log('EOS Tracker initialized');
});
