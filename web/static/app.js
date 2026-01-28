/**
 * EOS Tracker - Client-side JavaScript
 * Utilities and components for the application
 * Enhanced for mobile responsiveness
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

// Initialize on DOM ready
document.addEventListener('DOMContentLoaded', function() {
    console.log('EOS Tracker initialized');
    
    // Mobile-specific initializations
    initMobileEnhancements();
    initTableScrollDetection();
    initViewportHeightFix();
});

/**
 * Mobile-specific enhancements
 */
function initMobileEnhancements() {
    // Detect if on mobile
    const isMobile = window.innerWidth < 768;
    
    if (isMobile) {
        // Add mobile class to body
        document.body.classList.add('is-mobile');
        
        // Enhanced touch feedback
        addTouchFeedback();
        
        // Prevent double-tap zoom on buttons
        preventDoubleTapZoom();
    }
}

/**
 * Table scroll detection for visual indicators
 */
function initTableScrollDetection() {
    const tableWrappers = document.querySelectorAll('.table-wrapper');
    
    tableWrappers.forEach(wrapper => {
        const table = wrapper.querySelector('.data-table');
        
        if (!table) return;
        
        // Check if table is scrollable
        const checkScroll = () => {
            if (wrapper.scrollWidth > wrapper.clientWidth) {
                wrapper.classList.add('is-scrollable');
            } else {
                wrapper.classList.remove('is-scrollable');
            }
            
            // Add scrolled class when scrolled
            if (wrapper.scrollLeft > 0) {
                wrapper.classList.add('scrolled');
            } else {
                wrapper.classList.remove('scrolled');
            }
        };
        
        // Check on load
        checkScroll();
        
        // Check on scroll
        wrapper.addEventListener('scroll', checkScroll);
        
        // Check on resize
        window.addEventListener('resize', checkScroll);
    });
}

/**
 * Fix viewport height on mobile (iOS Safari issue)
 */
function initViewportHeightFix() {
    // First we get the viewport height and multiply it by 1% to get a value for a vh unit
    let vh = window.innerHeight * 0.01;
    // Then we set the value in the --vh custom property to the root of the document
    document.documentElement.style.setProperty('--vh', `${vh}px`);
    
    // We listen to the resize event
    window.addEventListener('resize', () => {
        // We execute the same script as before
        let vh = window.innerHeight * 0.01;
        document.documentElement.style.setProperty('--vh', `${vh}px`);
    });
}

/**
 * Add touch feedback to interactive elements
 */
function addTouchFeedback() {
    const interactiveElements = document.querySelectorAll('a, button, .btn, input[type="submit"]');
    
    interactiveElements.forEach(element => {
        element.addEventListener('touchstart', function() {
            this.style.opacity = '0.7';
        });
        
        element.addEventListener('touchend', function() {
            this.style.opacity = '1';
        });
        
        element.addEventListener('touchcancel', function() {
            this.style.opacity = '1';
        });
    });
}

/**
 * Prevent double-tap zoom on buttons
 */
function preventDoubleTapZoom() {
    let lastTouchEnd = 0;
    
    document.addEventListener('touchend', function(event) {
        const now = Date.now();
        if (now - lastTouchEnd <= 300) {
            event.preventDefault();
        }
        lastTouchEnd = now;
    }, false);
}

/**
 * Smooth scroll to element (utility)
 */
function smoothScrollTo(elementId) {
    const element = document.getElementById(elementId);
    if (element) {
        element.scrollIntoView({
            behavior: 'smooth',
            block: 'start'
        });
    }
}

// Export to global scope
window.smoothScrollTo = smoothScrollTo;
