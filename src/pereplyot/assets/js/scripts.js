/**
 * Cleaning Guide UI Interactions
 * Handles TOC toggle, slide animations, and accessibility
 */

(function() {
    'use strict';

    // DOM elements
    const tocToggle = document.getElementById('toc-toggle');
    const tocPanel = document.getElementById('toc-panel');
    const tocClose = document.getElementById('toc-close');
    const tocOverlay = document.getElementById('toc-overlay');
    const topAnchor = document.getElementById('top');

    // State
    let isTocOpen = false;
    // key in SECTION_CONTENT dictionary (which is created by
    // python and saved to sections.js in the dist/ dir) that
    // is present on page load. Note: these keys are created
    // by python.
    // SECTION_CONTENT is NOT in the source code -
    // it is generated dynamically by python and saved to dist/!
    let currentSectionKey = 'start';

    /**
     * Open the TOC panel
     */
    function openToc() {
        if (!tocPanel) return;
        tocPanel.classList.add('open');
        if (tocOverlay) tocOverlay.classList.add('active');
        if (tocToggle) tocToggle.setAttribute('aria-expanded', 'true');
        isTocOpen = true;
        document.body.style.overflow = 'hidden';
    }

    /**
     * Close the TOC panel
     */
    function closeToc() {
        if (!tocPanel) return;
        tocPanel.classList.remove('open');
        if (tocOverlay) tocOverlay.classList.remove('active');
        if (tocToggle) tocToggle.setAttribute('aria-expanded', 'false');
        isTocOpen = false;
        document.body.style.overflow = '';
    }

    /**
     * Toggle the TOC panel
     */
    function toggleToc() {
        if (isTocOpen) {
            closeToc();
        } else {
            openToc();
        }
    }

    /**
     * Wrap tables in responsive container
     */
    function wrapTables() {
        const tables = document.querySelectorAll('#main-content table');
        tables.forEach(table => {
            // Avoid double-wrapping
            if (table.parentElement && !table.parentElement.classList.contains('table-responsive')) {
                const wrapper = document.createElement('div');
                wrapper.className = 'table-responsive';
                table.parentNode.insertBefore(wrapper, table);
                wrapper.appendChild(table);
            }
        });
    }

    /**
     * Smooth scroll to an anchor link
     */
    function smoothScroll(e) {
        e.preventDefault();
        const targetId = this.getAttribute('href').substring(1);
        const targetElement = document.getElementById(targetId);
        if (targetElement) {
            closeToc();
            targetElement.scrollIntoView({
                behavior: 'smooth',
                block: 'start'
            });
        }
    }

    /**
     * Switch the active section content with a fade transition.
     *
     * This function is called when a TOC link is clicked. It reads the section
     * key from the anchor's href attribute (e.g., "#1234"), looks up the
     * corresponding HTML content from the SECTION_CONTENT global object, and
     * replaces the container's content. The transition uses opacity fading
     * to avoid abrupt visual changes.
     *
     * The container element must have an id of "main-content". The function
     * prevents default anchor behavior to avoid browser fragment navigation.
     *
     * Usage:
     *   document.querySelectorAll('.toc-list a.chap-link').forEach(anchor => {
     *       anchor.addEventListener('click', switchDocument);
     *   });
     *
     * @param {Event} event - The click event from the anchor element.
     */
    function switchDocument(event) {
        // Prevent default anchor behavior (browser jumping to #fragment)
        event.preventDefault();

        // Get the clicked anchor element
        const anchor = event.currentTarget;

        // Extract section key from href attribute (remove the leading '#')
        const href = anchor.getAttribute('href');
        const sectionKey = href.substring(1); // Remove the '#'

        // Do nothing if already displaying this section
        if (sectionKey === currentSectionKey) {
            return;
        }

        // Look up the HTML content for this section
        const newContent = SECTION_CONTENT[sectionKey];

        // Exit silently if section key doesn't exist (defensive programming)
        if (!newContent) {
            console.warn(`No content found for section key: ${sectionKey}`);
            return;
        }

        // Get the container element
        const container = document.getElementById('main-content');
        if (!container) {
            console.error('Section container (#main-content) not found');
            return;
        }

        // close TOC panel
        closeToc();

        // Update current section key before the transition
        currentSectionKey = sectionKey;

        // remove selected from the other anchors
        document.querySelectorAll('.toc-list a').forEach(a => {
            a.classList.remove('selected');
        });

        // set selected on newly clicked anchor so it will stay in a hover state
        anchor.classList.add("selected");

        // Fade out, swap content, then fade in
        container.style.opacity = '0';
        setTimeout(() => {
            container.innerHTML = newContent;

            // Scroll to top after content is swapped but before fade in
            topAnchor.scrollIntoView({
                behavior: 'smooth',
                block: 'start'
            });

            container.style.opacity = '1';
        }, 150); // 150ms matches CSS transition on #main-content; if you change here change there
    }

    /**
     * Initialize event listeners
     */
    function init() {
        // Toggle button
        if (tocToggle) {
            tocToggle.addEventListener('click', toggleToc);
        }

        // Close button
        if (tocClose) {
            tocClose.addEventListener('click', closeToc);
        }

        // Overlay click
        if (tocOverlay) {
            tocOverlay.addEventListener('click', closeToc);
        }

        // Escape key closes TOC
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape' && isTocOpen) {
                closeToc();
            }
        });

        // Smooth scroll to top when clicking header
        document.querySelectorAll('.site-title a').forEach(anchor => {
            anchor.addEventListener('click', smoothScroll);
        });

        // Gradual open and smooth scroll for TOC links
        document.querySelectorAll('.toc-list a').forEach(anchor => {
            anchor.addEventListener('click', switchDocument);
        });

        // Wrap tables after content loads
        wrapTables();
    }

    // Run when DOM is ready
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }
})();