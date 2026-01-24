// Alpine.js components and utilities for EOS Tracker

// Confirmation dialogs
function confirmDelete(message = 'Are you sure?') {
    return confirm(message);
}

// Export utilities to window
window.confirmDelete = confirmDelete;
