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
    const navChapPrev = document.getElementById('nav-chap-prev');
    const navChapNext = document.getElementById('nav-chap-next');

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
    let prevSectionKey = null;
    let nextSectionKey = null;

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
        if (!SECTION_CONTENT) {
            console.warn(`Missing DOM element SECTION_CONTENT (should be written by cli.py to section.js)`);
            return;
        }

        if (!SECTION_CONTENT[sectionKey]) {
            console.warn(`No content found for section key: ${sectionKey}`);
            return;
        }

        const tocHtml = SECTION_CONTENT[sectionKey]?.toc;
        if (!tocHtml || tocHtml.trim() === '') {
            console.warn(`section key (${sectionKey}) present but no TOC data (this is normal if no intra-page navigation, e.g. home page)`);
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
     * Update inter-chapter prev/next button disabled states based on currentTargetIndex
     */
    function updateChapterNavButtons() {
        if (!navChapPrev || !navChapNext) return;

        const hasPrev = prevSectionKey != null;
        const hasNext = nextSectionKey != null;

        navChapPrev.disabled = !hasPrev;
        navChapNext.disabled = !hasNext;

        // Update ARIA attributes for accessibility
        navChapPrev.setAttribute('aria-disabled', (!hasPrev).toString());
        navChapNext.setAttribute('aria-disabled', (!hasNext).toString());
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
     * Switch the active section content with a fade transition based on a key.
     *
     * This function accepts a "section key" (typically the href attr of a link).
     * It looks up the corresponding HTML content from the SECTION_CONTENT global
     * object (created via cli.py) and replaces the container's content. The
     * transition uses opacity fading to avoid abrupt visual changes.
     *
     * The function prevents default anchor behavior to avoid browser fragment navigation.
     *
     * @param {Event} event - The click event from the anchor element.
     */
    function switchDocument(sectionKey) {

        // Do nothing if already displaying this section
        if (sectionKey === currentSectionKey) {
            return;
        }

        // Look up the HTML content for this section
        const newContentData = SECTION_CONTENT[sectionKey];

        // Exit silently if section key doesn't exist (defensive programming)
        if (!newContentData) {
            console.warn(`No content found for section key: ${sectionKey}`);
            return;
        }

        // get next and prev chapters + HTML content
        const newContent = newContentData?.content;
        const prevKey = newContentData?.prev;
        const nextKey = newContentData?.next;

        if (!newContent) {
            console.warn(`Section key found, but no "content" key in its value: ${sectionKey} (did cli.py update how its constructing the dictionaries?)`);
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

        // Update keys for navigation
        currentSectionKey = sectionKey;
        nextSectionKey = nextKey;
        prevSectionKey = prevKey;

        // Update page TOC for the new section
        updatePageToc(sectionKey);

        // Fade out, swap content, then fade in
        container.style.opacity = '0';
        setTimeout(() => {
            container.innerHTML = newContent;

            // Rebuild navigation targets for the new content
            navTargets = buildNavTargets();
            currentTargetIndex = navTargets.length > 0 ? 0 : -1;
            updateNavButtons();
            updateChapterNavButtons();

            // Scroll to top after content is swapped but before fade in
            topAnchor.scrollIntoView({
                behavior: 'smooth',
                block: 'start'
            });

            container.style.opacity = '1';
        }, 150); // 150ms matches CSS transition on #main-content; if you change here change there

        // Update TOC styling
        updateTocStyling(sectionKey);
    }

    /**
     * Find the TOC anchor element that corresponds to a given section key.
     *
     * @param {string} sectionKey - The section identifier (e.g., "65945")
     * @returns {HTMLElement|null} The matching anchor element, or null if not found
     */
    function getChapterAnchor(sectionKey) {
        return document.querySelector(`.toc-list .chap-link a[href="#${sectionKey}"]`);
    }

    /**
     * Update TOC link styling to highlight the currently active section.
     *
     * Removes 'selected' class from all TOC anchors, then adds 'selected'
     * to the anchor matching the given section key (if it exists).
     *
     * @param {string} sectionKey - The section identifier (e.g., "65945")
     */
    function updateTocStyling(sectionKey) {
        // remove selected from the other anchors
        document.querySelectorAll('.toc-list a').forEach(a => {
            a.classList.remove('selected');
        });

        // Find chapter link (if any) and mark as selected so it will stay in a hover state
        const matchingAnchor = getChapterAnchor(sectionKey);
        if (matchingAnchor) {
            matchingAnchor.classList.add('selected');
        }
    }

    /**
     * Extracts the section key from a TOC anchor element's href attribute.
     *
     * @param {HTMLElement} anchor - The anchor element (e.g., <a href="#65945">)
     * @returns {string|null} The section key with the leading '#' removed, or null if invalid
     */
    function getSectionKey(anchor) {
        if (!anchor) return null;
        // Extract section key from href attribute (remove the leading '#')
        const href = anchor.getAttribute('href');
        if (!href || !href.startsWith('#')) return null; // Remove the '#'
        return href.substring(1);
    }

    /**
     * Handles click events on TOC links.
     *
     * @param {Event} event - The click event from the anchor element
     */
    function handleTocClick(event) {

        // Prevent default anchor behavior (browser jumping to #fragment)
        event.preventDefault();

        // Get the clicked anchor element
        const anchor = event.currentTarget;

        // Get section key
        const sectionKey = getSectionKey(anchor);

        // Update document
        if (sectionKey) {
            switchDocument(sectionKey);
        }
    }

    /**
     * Handles click events on home page links.
     *
     * @param {Event} event - The click event from the anchor element
     */
    function handleHomeClick(event) {
        // Prevent default anchor behavior (browser jumping to #fragment)
        event.preventDefault();
        switchDocument("start"); // "start" should be name of key in SECTION_CONTENT holding home page HTML
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
        document.querySelectorAll('.toc-list a').forEach(anchor => {
            anchor.addEventListener('click', handleTocClick);
        });

        // Opening home page
        document.querySelectorAll('.site-title a').forEach(anchor => {
            anchor.addEventListener('click', handleHomeClick)
        });

        // start button on basic home page
        // Note: use event delegation as the button will be removed
        // from DOM when navigating to new content.
        document.addEventListener('click', (event) => {
            const startButton = event.target.closest('#splash-start');
            if (startButton) {
                // "first"  is special section key made by cli.py for first chapter info
                switchDocument("first");
            }
        });

        // Navigation buttons
        if (navPrev) {
            navPrev.addEventListener('click', goToPrevTarget);
        }
        if (navNext) {
            navNext.addEventListener('click', goToNextTarget);
        }
        // Inter-chapter Navigation buttons
        if (navChapPrev) {
            navChapPrev.addEventListener('click', () => switchDocument(prevSectionKey));
        }
        if (navChapNext) {
            navChapNext.addEventListener('click', () => switchDocument(nextSectionKey));
        }

        // Wrap tables after content loads
        wrapTables();

        // Initial page TOC update (splash page has no TOC)
        updatePageToc(currentSectionKey);

        // Initialize navigation targets for initial content
        navTargets = buildNavTargets();
        currentTargetIndex = navTargets.length > 0 ? 0 : -1;
        updateNavButtons();
        updateChapterNavButtons();
    }

    // Run when DOM is ready
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }
})();