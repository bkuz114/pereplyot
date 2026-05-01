/**
 * ThemePicker - Vanilla JS multi-theme management
 *
 * Manages theme state, persistence, and events for CSS variable-based theming.
 * Toggles a prefixed class on <html> (e.g., 'theme-ocean') based on user preference.
 *
 * You provide:
 *   - Theme definitions (keys + display names)
 *   - Your own UI (dropdown, buttons, etc.) that calls applyTheme()
 *   - CSS rules for each theme class
 *
 * The class handles:
 *   - Applying themes via class toggling
 *   - Persisting preference to localStorage/sessionStorage
 *   - Callbacks when theme changes
 *   - Validation and fallbacks
 *
 * @example
 * const picker = new ThemePicker({
 *   themes: {
 *     ocean: { name: 'Ocean' },
 *     sunset: { name: 'Sunset' }
 *   },
 *   defaultTheme: 'ocean',
 *   onThemeChange: (newTheme, oldTheme) => {
 *     console.log(`${oldTheme} → ${newTheme}`);
 *   }
 * });
 *
 * // In your UI:
 * button.addEventListener('click', () => picker.applyTheme('sunset'));
 */

class ThemePicker {
    /**
     * Creates a new ThemePicker instance.
     * Automatically loads stored preference or falls back to defaultTheme,
     * then applies the theme and fires onThemeChange if applicable.
     *
     * @param {Object} config - Configuration object
     * @param {Object} config.themes - Theme definitions. Keys are theme IDs.
     *   Each value must have a `name` property (string). May include additional
     *   metadata (e.g., previewColors) which is ignored by this class.
     *   Example: { ocean: { name: 'Ocean' }, sunset: { name: 'Sunset' } }
     * @param {string} [config.classNamePrefix='theme-'] - Prefix for CSS classes.
     *   Final class becomes `${prefix}${themeKey}` (e.g., 'theme-ocean').
     *   Recommend including a separator like 'theme-' for readability.
     * @param {string} [config.storageKey='selectedTheme'] - Key for storage.
     * @param {string} [config.storageType='local'] - Storage backend: 'local',
     *   'session', or 'none' (no persistence).
     * @param {string} [config.defaultTheme] - Default theme key. Must exist in
     *   `themes`. If not provided, uses the first key in `themes`.
     * @param {Function} [config.onThemeChange] - Callback fired when theme changes.
     *   Receives (newThemeKey, oldThemeKey).
     *
     * @throws {Error} If themes is missing, empty, or a theme lacks a `name`.
     * @throws {Error} If defaultTheme is provided but not found in themes
     *   (after fallback attempt).
     */
    constructor(config) {
        // --- Validation -------------------------------------------------
        if (!config.themes || typeof config.themes !== 'object') {
            throw new Error('ThemePicker: "themes" object is required.');
        }

        const themeKeys = Object.keys(config.themes);
        if (themeKeys.length === 0) {
            throw new Error('ThemePicker: "themes" object cannot be empty.');
        }

        // Validate each theme has a name
        for (const [key, theme] of Object.entries(config.themes)) {
            if (!theme.name || typeof theme.name !== 'string') {
                throw new Error(`ThemePicker: Theme "${key}" missing required "name" property.`);
            }
        }

        // --- Store config ------------------------------------------------
        this.config = {
            themes: config.themes,
            classNamePrefix: config.classNamePrefix || 'theme-',
            storageKey: config.storageKey || 'selectedTheme',
            storageType: config.storageType || 'local',
            onThemeChange: config.onThemeChange || null
        };

        // --- Resolve default theme ---------------------------------------
        let defaultTheme = config.defaultTheme || themeKeys[0];

        if (!this.config.themes[defaultTheme]) {
            console.warn(
                `ThemePicker: defaultTheme "${defaultTheme}" not found in themes. ` +
                `Falling back to "${themeKeys[0]}".`
            );
            defaultTheme = themeKeys[0];
        }
        this.defaultTheme = defaultTheme;

        // --- Current theme (internal state) ------------------------------
        this._currentTheme = null;

        // --- Initialize --------------------------------------------------
        this._init();
    }

    /**
     * Returns the storage backend based on storageType.
     * @returns {Storage|null} localStorage, sessionStorage, or null if disabled.
     * @private
     */
    _getStorage() {
        if (this.config.storageType === 'none') return null;
        return this.config.storageType === 'local' ? localStorage : sessionStorage;
    }

    /**
     * Retrieves stored theme preference.
     * @returns {string|null} Theme key or null if none/storage disabled.
     * @private
     */
    _getStoredTheme() {
        const storage = this._getStorage();
        if (!storage) return null;
        return storage.getItem(this.config.storageKey);
    }

    /**
     * Saves theme preference to storage.
     * @param {string} theme - Theme key to save.
     * @private
     */
    _setStoredTheme(theme) {
        const storage = this._getStorage();
        if (!storage) return;
        storage.setItem(this.config.storageKey, theme);
    }

    /**
     * Applies theme class to <html> element.
     * Removes any existing class with the same prefix first.
     * @param {string} theme - Theme key to apply.
     * @private
     */
    _applyClass(theme) {
        const prefix = this.config.classNamePrefix;
        const html = document.documentElement;

        // Remove any existing theme class (starts with prefix)
        const existing = Array.from(html.classList).filter(c => c.startsWith(prefix));
        html.classList.remove(...existing);

        // Add new theme class
        html.classList.add(`${prefix}${theme}`);
    }

    /**
     * Initializes the picker: loads stored preference or default,
     * applies theme, and saves to storage.
     * @private
     */
    _init() {
        const stored = this._getStoredTheme();
        let initialTheme = null;

        if (stored && this.config.themes[stored]) {
            initialTheme = stored;
        } else if (stored && !this.config.themes[stored]) {
            // Stored theme no longer exists in config
            console.warn(`ThemePicker: Stored theme "${stored}" not found in themes. Using default.`);
        }

        if (!initialTheme) {
            initialTheme = this.defaultTheme;
        }

        // Apply without triggering callback (no previous theme)
        this._applyClass(initialTheme);
        this._currentTheme = initialTheme;
        this._setStoredTheme(initialTheme);
    }

    // ============================================
    // Public API
    // ============================================

    /**
     * Applies a theme by key.
     * Validates that the theme exists in config.themes.
     *
     * @param {string} theme - Theme key (e.g., 'ocean', 'sunset')
     * @returns {boolean} - True if theme was applied, false if invalid.
     */
    applyTheme(theme) {
        if (!this.config.themes[theme]) {
            console.warn(`ThemePicker: Theme "${theme}" not found in themes. No change applied.`);
            return false;
        }

        if (this._currentTheme === theme) {
            return true; // Already active, no change needed
        }

        const oldTheme = this._currentTheme;
        this._applyClass(theme);
        this._currentTheme = theme;
        this._setStoredTheme(theme);

        // Fire callback if provided
        if (this.config.onThemeChange) {
            this.config.onThemeChange(theme, oldTheme);
        }

        return true;
    }

    /**
     * Returns the currently active theme key.
     * @returns {string}
     */
    getCurrentTheme() {
        return this._currentTheme;
    }

    /**
     * Resets to the default theme (as defined in config.defaultTheme).
     * Equivalent to calling applyTheme(defaultTheme).
     */
    resetToDefault() {
        this.applyTheme(this.defaultTheme);
    }

    /**
     * Cleans up event listeners.
     * Currently a no-op (reserved for future features like cross-tab sync).
     * Call this if you're removing the ThemePicker instance from an SPA.
     */
    destroy() {
        // Reserved for future cleanup (e.g., storage event listener)
        // No-op in v1.0.0
    }
}

// Optional: Expose globally (for non-module environments)
if (typeof window !== 'undefined') {
    window.ThemePicker = ThemePicker;
}