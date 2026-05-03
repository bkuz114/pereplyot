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

    // Page TOC elements
    const pageTocToggle = document.getElementById('page-toc-toggle');
    const pageTocPanel = document.getElementById('page-toc-panel');
    const pageTocClose = document.getElementById('page-toc-close');
    const pageTocContent = document.getElementById('page-toc-content');

    // State (using objects for pass-by-reference to generalized functions)
    let isTocOpen = {
        value: false
    };
    let isPageTocOpen = {
        value: false
    };
    // key in SECTION_CONTENT dictionary (which is created by
    // python and saved to sections.js in the dist/ dir) that
    // is present on page load. Note: these keys are created
    // by python.
    // SECTION_CONTENT is NOT in the source code -
    // it is generated dynamically by python and saved to dist/!
    let currentSectionKey = 'start';

    // =========================================================================
    // Generalized Panel Controls
    // =========================================================================

    /**
     * Open a panel
     */
    function openPanel(panelEl, overlayEl, toggleBtnEl, state) {
        if (!panelEl) return;
        panelEl.classList.add('open');
        if (overlayEl) overlayEl.classList.add('active');
        if (toggleBtnEl) toggleBtnEl.setAttribute('aria-expanded', 'true');
        state.value = true;
        document.body.style.overflow = 'hidden';
    }

    /**
     * Close a panel
     */
    function closePanel(panelEl, overlayEl, toggleBtnEl, state) {
        if (!panelEl) return;
        panelEl.classList.remove('open');
        if (overlayEl) overlayEl.classList.remove('active');
        if (toggleBtnEl) toggleBtnEl.setAttribute('aria-expanded', 'false');
        state.value = false;
        document.body.style.overflow = '';
    }

    /**
     * Open the main TOC panel
     */
    function openToc() {
        if (isPageTocOpen.value) closePageToc();
        openPanel(tocPanel, tocOverlay, tocToggle, isTocOpen);
    }

    /**
     * Close the main TOC panel
     */
    function closeToc() {
        closePanel(tocPanel, tocOverlay, tocToggle, isTocOpen);
    }

    /**
     * Toggle the main TOC panel
     */
    function toggleToc() {
        if (isTocOpen.value) {
            closeToc();
        } else {
            openToc();
        }
    }

    /**
     * Open the page TOC panel
     */
    function openPageToc() {
        if (isTocOpen.value) closeToc();
        openPanel(pageTocPanel, tocOverlay, pageTocToggle, isPageTocOpen);
    }

    /**
     * Close the page TOC panel
     */
    function closePageToc() {
        closePanel(pageTocPanel, tocOverlay, pageTocToggle, isPageTocOpen);
    }

    /**
     * Toggle the page TOC panel
     */
    function togglePageToc() {
        if (isPageTocOpen.value) {
            closePageToc();
        } else {
            openPageToc();
        }
    }

    /**
     * Update the page TOC for the currently loaded section
     */
    function updatePageToc(sectionKey) {
        if (typeof SECTION_TOC === 'undefined' || !SECTION_TOC[sectionKey]) {
            if (pageTocToggle) pageTocToggle.classList.add('hidden');
            if (pageTocContent) pageTocContent.innerHTML = '';
            return;
        }

        const tocHtml = SECTION_TOC[sectionKey];
        if (!tocHtml || tocHtml.trim() === '') {
            if (pageTocToggle) pageTocToggle.classList.add('hidden');
            if (pageTocContent) pageTocContent.innerHTML = '';
            return;
        }

        if (pageTocToggle) pageTocToggle.classList.remove('hidden');
        if (pageTocContent) {
            pageTocContent.innerHTML = tocHtml;

            const pageLinks = pageTocContent.querySelectorAll('a');
            pageLinks.forEach(link => {
                link.addEventListener('click', handlePageTocLinkClick);
            });
        }
    }

    /**
     * Handle clicks on page TOC links
     */
    function handlePageTocLinkClick(event) {
        event.preventDefault();
        const anchor = event.currentTarget;
        const href = anchor.getAttribute('href');

        if (href && href.startsWith('#')) {
            const targetId = href.substring(1);
            const targetElement = document.getElementById(targetId);
            if (targetElement) {
                const allLinks = pageTocContent.querySelectorAll('a');
                allLinks.forEach(link => link.classList.remove('selected'));
                anchor.classList.add('selected');
                closePageToc();
                targetElement.scrollIntoView({
                    behavior: 'smooth',
                    block: 'start'
                });
            }
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
            closePageToc();
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

        // close TOC panels
        closeToc();
        closePageToc();

        // Update current section key before the transition
        currentSectionKey = sectionKey;

        // Update page TOC for the new section
        updatePageToc(sectionKey);

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

        // Page TOC events
        if (pageTocToggle) {
            pageTocToggle.addEventListener('click', togglePageToc);
        }
        if (pageTocClose) {
            pageTocClose.addEventListener('click', closePageToc);
        }

        // Overlay click
        if (tocOverlay) {
            tocOverlay.addEventListener('click', () => {
                if (isTocOpen.value) closeToc();
                if (isPageTocOpen.value) closePageToc();
            });
        }

        // Escape key closes either panel
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape') {
                if (isTocOpen.value) closeToc();
                if (isPageTocOpen.value) closePageToc();
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

        // Initial page TOC update (splash page has no TOC)
        updatePageToc(currentSectionKey);
    }

    // Run when DOM is ready
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }
})();