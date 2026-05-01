/**
 * ============================================
 * THEME PICKER DROPDOWN WIDGET
 * (for use with libs/themePicker/themePicker.js lib)
 * ============================================
 *
 * **IMPORTANT — TO PREVENT FOUC (Flash of Unstyled Content):**
 *
 * 1. Place this script in the <head> of your HTML:
 *      <script src="path/to/this-file.js"></script>
 *
 * 2. Do NOT use `defer` or `async` attributes on the script tag.
 *
 * 3. The script applies the stored theme synchronously BEFORE the page paints,
 *    then builds the UI inside DOMContentLoaded (so DOM elements exist).
 *
 * **Why this matters:**
 *
 * If the script runs after the page paints (e.g., at end of <body> or with defer),
 * users will see a flash of the wrong theme before the correct one loads.
 *
 * ============================================
 */

// ============================================
// DROPDOWN CONFIGURATION
// ============================================

// Preview style: 'gradient' or 'dots'
const PREVIEW_STYLE = 'gradient';

// ==============================================
// THEME DEFINITIONS
// ==============================================
// - keys correspond to css classes defined for page
//   (see css/themes.css for theme rules)
// - Note: those rules are prefixed with 'theme-'
//   due to constructor setup below (classNamePrefix)
// - Note: 'previewColors' are linear-gradient colors
//   in "colored square" (or dot) in dropdown opts
//   (a <span> with linear-gradient background)
// ================================================
const THEMES = {
    light: {
        name: 'Light',
        previewColors: ['#f8f9fa', '#ffffff', '#0d6efd']
    },
    dark: {
        name: 'Dark',
        previewColors: ['#1e1e1e', '#2a2a2a', '#3d8bff']
    },
    nord: {
        name: 'Nord',
        previewColors: ['#3b4252', '#434c5e', '#88c0d0']
    },
    forest: {
        name: 'Forest',
        previewColors: ['#243029', '#2d3a32', '#6b9e7a']
    },
    sepia: {
        name: 'Sepia',
        previewColors: ['#fbf6e9', '#f5edd9', '#9b6b43']
    },
    void: {
        name: 'Void',
        previewColors: ['#0a0a0a', '#141414', '#a277ff']
    }
};

// ============================================
// INITIALIZE THEME PICKER
// ============================================

// 1. Initialize ThemePicker immediately (no DOM dependency)
const picker = new ThemePicker({
    themes: THEMES,
    classNamePrefix: 'theme-',
    storageKey: 'selectedTheme',
    storageType: 'local',
    defaultTheme: 'light',
    onThemeChange: (newTheme, oldTheme) => {
        // Update button text when theme changes (e.g., from reset or storage sync)
        const themeName = THEMES[newTheme]?.name || newTheme;
        const btn = document.getElementById('themeBtn');
        if (btn) btn.textContent = `${themeName} ▼`;
    }
});

// 2. Defer UI building until DOM is ready
document.addEventListener('DOMContentLoaded', () => {

    // ============================================
    // PREVIEW SWATCH GENERATOR
    // ============================================

    function createPreviewSwatch(colors) {
        const swatch = document.createElement('span');
        swatch.className = 'preview-swatch';

        if (PREVIEW_STYLE === 'dots') {
            swatch.classList.add('preview-dots');
            colors.forEach(color => {
                const dot = document.createElement('span');
                dot.className = 'preview-dot';
                dot.style.backgroundColor = color;
                swatch.appendChild(dot);
            });
        } else {
            // gradient (default)
            swatch.style.background = `linear-gradient(135deg, ${colors.join(', ')})`;
        }

        return swatch;
    }

    // ============================================
    // BUILD THEME MENU
    // ============================================

    const menu = document.getElementById('themeMenu');
    const btn = document.getElementById('themeBtn');

    if (menu && btn) {
        // Populate menu
        Object.entries(THEMES).forEach(([key, theme]) => {
            const option = document.createElement('div');
            option.className = 'theme-option';
            option.setAttribute('data-theme', key);
            option.setAttribute('role', 'option');

            // Preview swatch
            const swatch = createPreviewSwatch(theme.previewColors);

            // Label
            const label = document.createTextNode(theme.name);

            option.appendChild(swatch);
            option.appendChild(label);

            option.addEventListener('click', () => {
                picker.applyTheme(key);
                menu.classList.add('hidden');
                btn.textContent = `${theme.name} ▼`;
            });

            menu.appendChild(option);
        });

        // Toggle dropdown
        btn.addEventListener('click', (e) => {
            e.stopPropagation();
            menu.classList.toggle('hidden');
        });

        // Close dropdown when clicking outside
        document.addEventListener('click', (e) => {
            if (!btn.contains(e.target) && !menu.contains(e.target)) {
                menu.classList.add('hidden');
            }
        });

        // Set initial button text from current theme
        const currentKey = picker.getCurrentTheme();
        const currentTheme = THEMES[currentKey];
        if (currentTheme) {
            btn.textContent = `${currentTheme.name} ▼`;
        }
    }
});