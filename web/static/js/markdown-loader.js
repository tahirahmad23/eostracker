document.addEventListener('DOMContentLoaded', function () {
    const contentContainer = document.getElementById('device-md-container');
    const dbDescription = document.getElementById('db-description');

    if (!contentContainer) return;

    const slug = contentContainer.getAttribute('data-slug');
    if (!slug) return;

    const mdPath = `/static/device_posts/${slug}.md`;

    console.log(`[SYS] Attempting to fetch documentation: ${mdPath}`);

    fetch(mdPath)
        .then(response => {
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            return response.text();
        })
        .then(text => {
            console.log(`[SYS] Documentation found. Rendering.`);
            // Using marked from global scope (CDN)
            if (window.marked) {
                contentContainer.innerHTML = marked.parse(text);
                // Hide fallback DB description if we successfully loaded rich content
                if (dbDescription) {
                    dbDescription.style.display = 'none';
                }
                contentContainer.classList.remove('hidden');
            } else {
                console.error('[ERR] marked.js library not loaded.');
                contentContainer.innerText = text; // Fallback to raw text
            }
        })
        .catch(e => {
            console.log(`[SYS] No rich documentation found. Using standard DB records.`);
            // Keep DB description visible, maybe show a small log
            // contentContainer.innerHTML = '<p class="text-secondary mono text-sm">[No extended documentation file found]</p>';
        });
});
