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

    // Navigation buttons
    const navPrev = document.getElementById('nav-prev');
    const navNext = document.getElementById('nav-next');

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

    // Intra-document navigation state
    let navTargets = [];
    let currentTargetIndex = -1;

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
     * ===============================================
     * INTRA-PAGE NAVIGATION
     * ==============================================
     */

    /**
     * Build array of navigation targets from current DOM
     * Targets are elements with class 'nav-target'
     * @returns {Array<{id: string, element: HTMLElement, index: number}>}
     */
    function buildNavTargets() {
        const container = document.getElementById('main-content');
        if (!container) return [];

        const targets = Array.from(container.querySelectorAll('.nav-target'));
        return targets.map((el, index) => ({
            id: el.id || `temp-${index}`,
            element: el,
            index: index
        }));
    }

    /**
     * Update prev/next button disabled states based on currentTargetIndex
     */
    function updateNavButtons() {
        if (!navPrev || !navNext) return;

        const hasPrev = currentTargetIndex > 0;
        const hasNext = currentTargetIndex < navTargets.length - 1 && currentTargetIndex !== -1;

        navPrev.disabled = !hasPrev;
        navNext.disabled = !hasNext;

        // Update ARIA attributes for accessibility
        navPrev.setAttribute('aria-disabled', (!hasPrev).toString());
        navNext.setAttribute('aria-disabled', (!hasNext).toString());
    }

    /**
     * Scroll to a specific element
     * @param {HTMLElement} element - The element to scroll to
     */
    function scrollToElement(element) {
        if (!element) return;

        // Close any open panels
        if (isTocOpen.value) closeToc();
        if (isPageTocOpen.value) closePageToc();

        element.scrollIntoView({
            behavior: 'smooth',
            block: 'start'
        });
    }

    /**
     * Navigate to previous target (if exists)
     */
    function goToPrevTarget() {
        if (currentTargetIndex <= 0) return;

        currentTargetIndex--;
        const target = navTargets[currentTargetIndex];
        if (target && target.element) {
            scrollToElement(target.element);
        }
        updateNavButtons();
    }

    /**
     * Navigate to next target (if exists)
     */
    function goToNextTarget() {
        if (currentTargetIndex === -1 || currentTargetIndex >= navTargets.length - 1) return;

        currentTargetIndex++;
        const target = navTargets[currentTargetIndex];
        if (target && target.element) {
            scrollToElement(target.element);
        }
        updateNavButtons();
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

            // Rebuild navigation targets for the new content
            navTargets = buildNavTargets();
            currentTargetIndex = navTargets.length > 0 ? 0 : -1;
            updateNavButtons();

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

        // Gradual open and smooth scroll for TOC links
        document.querySelectorAll('.toc-list a, .site-title a').forEach(anchor => {
            anchor.addEventListener('click', switchDocument);
        });

        // Navigation buttons
        if (navPrev) {
            navPrev.addEventListener('click', goToPrevTarget);
        }
        if (navNext) {
            navNext.addEventListener('click', goToNextTarget);
        }

        // Wrap tables after content loads
        wrapTables();

        // Initial page TOC update (splash page has no TOC)
        updatePageToc(currentSectionKey);

        // Initialize navigation targets for initial content
        navTargets = buildNavTargets();
        currentTargetIndex = navTargets.length > 0 ? 0 : -1;
        updateNavButtons();
    }

    // Run when DOM is ready
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }
})();
