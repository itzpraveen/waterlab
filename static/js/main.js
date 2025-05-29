// static/js/main.js

const WaterLab = {
    config: {
        debug: true, // Set to false in production
        defaultDebounceTime: 300,
        smoothScrollOffset: 60, // Offset for fixed header
    },

    log: function(...args) {
        if (this.config.debug) {
            console.log("WaterLab:", ...args);
        }
    },

    init: function() {
        this.log("Initializing WaterLab JS...");
        this.initMaterializeComponents();
        this.initSmoothScroll();
        this.initPageTransitions();
        this.initFormEnhancements();
        this.initTableEnhancements();
        this.initAccessibilityImprovements();
        this.initAlerts();
        this.initServiceWorker(); // PWA feature
        
        // Defer address dropdown initialization slightly to ensure Materialize components are fully ready
        setTimeout(() => {
            this.initAddressDropdowns();
        }, 0);
        this.log("WaterLab JS Initialized (core init complete, address dropdowns deferred).");
    },

    // --- Start: Kerala Address Dropdown Logic ---
    _keralaAddressData: null,

    loadAddressData: async function() {
        if (this._keralaAddressData) {
            return this._keralaAddressData;
        }
        try {
            const response = await fetch('/static/js/kerala_address_data.json');
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            this._keralaAddressData = await response.json();
            this.log("Kerala address data loaded:", this._keralaAddressData);
            return this._keralaAddressData;
        } catch (error) {
            this.log("Error loading Kerala address data:", error);
            M.toast({html: 'Could not load address options. Please try refreshing.', classes: 'red darken-1'});
            return null;
        }
    },

    populateDropdown: function(selectElement, optionsArray, defaultOptionText = '---------', isLoading = false) {
        if (!selectElement) return;

        const previouslySelectedValue = selectElement.value;
        const existingInstance = M.FormSelect.getInstance(selectElement);
        if (existingInstance) {
            existingInstance.destroy();
        }

        selectElement.innerHTML = ''; // Clear existing options

        if (isLoading) {
            const loadingOption = document.createElement('option');
            loadingOption.value = "";
            loadingOption.textContent = "Loading...";
            selectElement.appendChild(loadingOption);
            selectElement.disabled = true;
        } else {
            const defaultOption = document.createElement('option');
            defaultOption.value = "";
            defaultOption.textContent = defaultOptionText;
            selectElement.appendChild(defaultOption);

            if (optionsArray && optionsArray.length > 0) {
                optionsArray.forEach(option => {
                    const optionElement = document.createElement('option');
                    optionElement.value = option;
                    optionElement.textContent = option;
                    selectElement.appendChild(optionElement);
                });
                selectElement.disabled = false;
                // Try to reselect the previous value if it's still valid
                if (optionsArray.includes(previouslySelectedValue)) {
                    selectElement.value = previouslySelectedValue;
                } else {
                    selectElement.value = ""; // Reset to default if previous value is no longer valid
                }
            } else {
                // No options, keep disabled unless it's the primary dropdown (district)
                selectElement.disabled = selectElement.id !== 'id_district';
                 selectElement.value = ""; // Reset to default
            }
        }
        M.FormSelect.init(selectElement);
    },

    updateTalukDropdown: async function(districtSelectId = 'id_district', talukSelectId = 'id_taluk', panchayatSelectId = 'id_panchayat_municipality') {
        const districtSelect = document.getElementById(districtSelectId);
        const talukSelect = document.getElementById(talukSelectId);
        const panchayatSelect = document.getElementById(panchayatSelectId);

        if (!districtSelect || !talukSelect || !panchayatSelect) return;

        const selectedDistrict = districtSelect.value;
        this.log(`updateTalukDropdown: Called. Selected district value: "${selectedDistrict}"`);

        this.populateDropdown(talukSelect, [], 'Select Taluk', true); 
        this.populateDropdown(panchayatSelect, [], 'Select Panchayat/Municipality', false);
        panchayatSelect.disabled = true;
        M.FormSelect.init(panchayatSelect);

        const data = await this.loadAddressData();
        if (!data) {
            this.log("updateTalukDropdown: Failed to load address data.");
            this.populateDropdown(talukSelect, [], 'Error loading data');
            return;
        }
        this.log("updateTalukDropdown: Address data object:", data);


        if (selectedDistrict && data.hasOwnProperty(selectedDistrict)) {
            this.log(`updateTalukDropdown: District "${selectedDistrict}" found in data.`);
            const taluksObject = data[selectedDistrict];
            this.log(`updateTalukDropdown: Taluks object for "${selectedDistrict}":`, JSON.stringify(taluksObject)); // Added detailed log
            if (typeof taluksObject !== 'object' || taluksObject === null) {
                this.log(`updateTalukDropdown: ERROR - taluksObject is not a valid object for district "${selectedDistrict}".`);
                this.populateDropdown(talukSelect, [], 'Error: Invalid taluk data');
                return;
            }
            const taluks = Object.keys(taluksObject);
            this.log(`updateTalukDropdown: Taluks for "${selectedDistrict}":`, taluks);
            this.populateDropdown(talukSelect, taluks, 'Select Taluk');
            
            if (talukSelect.value) { // If a taluk is now selected (either pre-filled or first in list)
                this.log(`updateTalukDropdown: Taluk "${talukSelect.value}" is selected, updating panchayats.`);
                await this.updatePanchayatDropdown(districtSelectId, talukSelectId, panchayatSelectId, true);
            } else {
                 this.log(`updateTalukDropdown: No taluk selected for "${selectedDistrict}", clearing panchayats.`);
                 this.populateDropdown(panchayatSelect, [], 'Select Panchayat/Municipality');
                 panchayatSelect.disabled = true;
                 M.FormSelect.init(panchayatSelect);
            }
        } else {
            this.log(`updateTalukDropdown: District "${selectedDistrict}" not found in data or data is null. Clearing taluks.`);
            this.populateDropdown(talukSelect, [], 'Select Taluk');
        }
    },

    updatePanchayatDropdown: async function(districtSelectId = 'id_district', talukSelectId = 'id_taluk', panchayatSelectId = 'id_panchayat_municipality', isChainedCall = false) {
        const districtSelect = document.getElementById(districtSelectId);
        const talukSelect = document.getElementById(talukSelectId);
        const panchayatSelect = document.getElementById(panchayatSelectId);

        if (!districtSelect || !talukSelect || !panchayatSelect) {
            this.log("updatePanchayatDropdown: One or more select elements not found.");
            return;
        }

        const selectedDistrict = districtSelect.value;
        const selectedTaluk = talukSelect.value;
        this.log(`updatePanchayatDropdown: Called. District: "${selectedDistrict}", Taluk: "${selectedTaluk}"`);

        if (!isChainedCall) {
            this.populateDropdown(panchayatSelect, [], 'Select Panchayat/Municipality', true);
        }

        const data = await this.loadAddressData();
        if (!data) {
            this.log("updatePanchayatDropdown: Failed to load address data.");
            this.populateDropdown(panchayatSelect, [], 'Error loading data');
            return;
        }
        this.log("updatePanchayatDropdown: Address data object:", data);

        if (selectedDistrict && selectedTaluk && data.hasOwnProperty(selectedDistrict) && data[selectedDistrict].hasOwnProperty(selectedTaluk)) {
            this.log(`updatePanchayatDropdown: District "${selectedDistrict}" and Taluk "${selectedTaluk}" found.`);
            const panchayats = data[selectedDistrict][selectedTaluk];
            this.log(`updatePanchayatDropdown: Panchayats for "${selectedTaluk}":`, panchayats);
            this.populateDropdown(panchayatSelect, panchayats, 'Select Panchayat/Municipality');
        } else {
            this.log(`updatePanchayatDropdown: District "${selectedDistrict}" or Taluk "${selectedTaluk}" not found, or no panchayats. Clearing panchayats.`);
            this.populateDropdown(panchayatSelect, [], 'Select Panchayat/Municipality');
        }
    },

    initAddressDropdowns: async function() {
        this.log("Initializing address dropdowns...");
        const districtSelect = document.getElementById('id_district');
        const talukSelect = document.getElementById('id_taluk');
        const panchayatSelect = document.getElementById('id_panchayat_municipality');

        if (!districtSelect || !talukSelect || !panchayatSelect) {
            this.log("Address dropdowns not found, skipping initialization.");
            return;
        }
        
        await this.loadAddressData(); // Pre-load data

        // Initial state: taluk and panchayat should be disabled if no district is selected
        const initialDistrict = districtSelect.value;
        const initialTaluk = talukSelect.value; // Uncommented: Keep track of pre-filled value for edit forms

        if (initialDistrict) {
            this.log("Initial district found on page load:", initialDistrict);
            await this.updateTalukDropdown(); // This will populate taluks and potentially panchayats if taluk is also pre-filled
            // If taluk was pre-filled and is valid for the district, updatePanchayatDropdown would have been called by updateTalukDropdown
        } else {
            this.populateDropdown(talukSelect, [], 'Select Taluk');
            talukSelect.disabled = true;
            M.FormSelect.init(talukSelect);
            this.populateDropdown(panchayatSelect, [], 'Select Panchayat/Municipality');
            panchayatSelect.disabled = true;
            M.FormSelect.init(panchayatSelect);
        }
        
        districtSelect.addEventListener('change', async () => {
            this.log("District dropdown 'change' event triggered. New value:", districtSelect.value);
            await this.updateTalukDropdown();
        });

        talukSelect.addEventListener('change', async () => {
            this.log("Taluk dropdown 'change' event triggered. New value:", talukSelect.value);
            await this.updatePanchayatDropdown();
        });
        this.log("Address dropdowns initialized and event listeners attached.");
    },
    // --- End: Kerala Address Dropdown Logic ---

    initMaterializeComponents: function() {
        this.log("Initializing Materialize components...");
        M.Sidenav.init(document.querySelectorAll('.sidenav'), { edge: 'left' });
        M.Dropdown.init(document.querySelectorAll('.dropdown-trigger'), {
            constrainWidth: false,
            coverTrigger: false,
            alignment: 'right',
            hover: false
        });
        M.Collapsible.init(document.querySelectorAll('.collapsible'), { accordion: true });
        M.Modal.init(document.querySelectorAll('.modal'), { 
            dismissible: true,
            onOpenStart: (modalEl) => {
                // Trap focus within modal
                this._currentModal = modalEl;
                modalEl.focus(); // Focus the modal itself first
                this.trapFocus(modalEl);
            },
            onCloseEnd: () => {
                this.releaseFocus();
                this._currentModal = null;
            }
        });
        M.Tabs.init(document.querySelectorAll('.tabs'), { swipeable: true, responsiveThreshold: Infinity });
        M.FormSelect.init(document.querySelectorAll('select'));
        M.Tooltip.init(document.querySelectorAll('.tooltipped'), { enterDelay: 300, exitDelay: 50, outDuration: 150 });
        
        const datepickerOptions = {
            format: 'yyyy-mm-dd',
            autoClose: true,
            showClearBtn: true,
            container: document.body // Prevents issues with modals/drawers
        };
        M.Datepicker.init(document.querySelectorAll('.datepicker'), datepickerOptions);
        
        const timepickerOptions = {
            autoClose: true,
            twelveHour: false, // 24-hour format
            showClearBtn: true,
            container: document.body
        };
        M.Timepicker.init(document.querySelectorAll('.timepicker'), timepickerOptions);
        
        M.CharacterCounter.init(document.querySelectorAll('input[data-length], textarea[data-length]'));
        M.updateTextFields(); // Important for pre-filled forms
    },

    initSmoothScroll: function() {
        document.querySelectorAll('a[href^="#"]').forEach(anchor => {
            anchor.addEventListener('click', function (e) {
                const href = this.getAttribute('href');
                if (href.length > 1) { // Ensure it's not just "#"
                    try {
                        const targetElement = document.querySelector(href);
                        if (targetElement) {
                            e.preventDefault();
                            const offsetPosition = targetElement.getBoundingClientRect().top + window.pageYOffset - WaterLab.config.smoothScrollOffset;
                            window.scrollTo({
                                top: offsetPosition,
                                behavior: 'smooth'
                            });
                            // Optionally update URL hash without jump
                            // history.pushState(null, null, href); 
                        }
                    } catch (error) {
                        WaterLab.log("Smooth scroll target not found or invalid selector:", href, error);
                    }
                }
            });
        });
    },

    initPageTransitions: function() {
        document.body.style.opacity = 0;
        window.addEventListener('load', () => {
            document.body.style.transition = 'opacity 0.4s ease-in-out';
            document.body.style.opacity = 1;
        });
        // More complex transitions (e.g., on link click) can be added using libraries or more involved logic
    },

    initFormEnhancements: function() {
        document.querySelectorAll('form.validate-form').forEach(form => { // Add class 'validate-form' to forms needing this
            this.initFormValidationListeners(form); // Changed to initFormValidationListeners
            form.addEventListener('submit', (event) => {
                if (!this.validateForm(form)) {
                    event.preventDefault();
                    this.log("Form validation failed.");
                    const firstInvalid = form.querySelector('[aria-invalid="true"], .invalid');
                    if (firstInvalid) {
                        firstInvalid.focus();
                        M.toast({html: 'Please correct the highlighted errors.', classes: 'red darken-1'});
                    }
                } else {
                    // Handle AJAX submission or allow native submission
                    const submitButton = form.querySelector('button[type="submit"]');
                    if (submitButton && form.classList.contains('ajax-submit')) { // Add 'ajax-submit' for AJAX forms
                        event.preventDefault();
                        this.handleAjaxFormSubmit(form, submitButton);
                    } else if (submitButton) {
                         this.toggleButtonLoadingState(submitButton, true, { text: 'Submitting...' });
                         // Native submission will proceed, button state will reset on page load
                    }
                }
            });
        });
    },

    validateForm: function(form) {
        let isValid = true;
        form.querySelectorAll('input, select, textarea').forEach(field => {
            if (!this.validateField(field)) {
                isValid = false;
            }
        });
        return isValid;
    },

    initFormValidationListeners: function(form) {
        this.log("Initializing form validation listeners for", form.id || "form");
        form.querySelectorAll('input, select, textarea').forEach(field => {
            // Example: Validate on blur
            // field.addEventListener('blur', () => this.validateField(field));
            // For select elements, 'change' event is more appropriate
            if (field.tagName === 'SELECT') {
                field.addEventListener('change', () => this.validateField(field));
            } else {
                field.addEventListener('blur', () => this.validateField(field));
                // Optionally, validate on input for immediate feedback for some fields
                // if (field.type === 'text' || field.type === 'email' || field.type === 'password') {
                //    field.addEventListener('input', this.debounce(() => this.validateField(field), 500));
                // }
            }
        });
    },
    
    validateField: function(field) {
        let isValid = true;
        const fieldType = field.type;
        const value = field.value.trim();
        let errorMessage = '';

        // Clear previous errors
        this.clearFieldError(field);

        if (field.hasAttribute('required') && !value && fieldType !== 'checkbox' && fieldType !== 'radio') {
            isValid = false;
            errorMessage = field.dataset.errorMessageRequired || 'This field is required.';
        } else if (fieldType === 'checkbox' && field.hasAttribute('required') && !field.checked) {
            isValid = false;
            errorMessage = field.dataset.errorMessageRequired || 'This checkbox must be checked.';
        }
        // Add more validation rules (pattern, min, max, email, url etc.)
        if (isValid && field.hasAttribute('pattern')) {
            const pattern = new RegExp(field.getAttribute('pattern'));
            if (!pattern.test(value)) {
                isValid = false;
                errorMessage = field.dataset.errorMessagePattern || 'Invalid format.';
            }
        }
        if (isValid && fieldType === 'email' && value && !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(value)) {
             isValid = false;
             errorMessage = field.dataset.errorMessageEmail || 'Please enter a valid email address.';
        }
        
        // PIN Code validation
        if (isValid && field.id === 'id_pincode' && value) {
            if (!/^\d{6}$/.test(value)) {
                isValid = false;
                errorMessage = 'PIN code must be 6 digits.';
            } else {
                const pinNum = parseInt(value, 10);
                if (pinNum < 670001 || pinNum > 695615) {
                    isValid = false;
                    errorMessage = 'PIN code is not in the valid Kerala range (670001-695615).';
                }
            }
        }
        
        // Required validation for select elements (District, Taluk, Panchayat)
        if (isValid && field.tagName === 'SELECT' && field.hasAttribute('required') && !value) {
            // Check if it's one of our address dropdowns that might be dynamically populated
            if (['id_district', 'id_taluk', 'id_panchayat_municipality'].includes(field.id)) {
                 if (!field.disabled) { // Only validate if not disabled
                    isValid = false;
                    errorMessage = field.dataset.errorMessageRequired || 'This field is required.';
                 }
            } else { // For other required selects
                isValid = false;
                errorMessage = field.dataset.errorMessageRequired || 'This field is required.';
            }
        }


        if (!isValid) {
            this.setFieldError(field, errorMessage);
        }
        return isValid;
    },

    setFieldError: function(field, message) {
        field.classList.add('invalid');
        field.setAttribute('aria-invalid', 'true');
        let helperTextElement = field.parentElement.querySelector('.helper-text');
        if (!helperTextElement) {
            helperTextElement = document.createElement('span');
            helperTextElement.classList.add('helper-text');
            field.parentElement.appendChild(helperTextElement);
        }
        helperTextElement.setAttribute('data-error', message);
        helperTextElement.style.display = 'block'; // Ensure it's visible
        // For select, Materialize wraps it, so target parent
        if (field.tagName === 'SELECT') {
            const parentWrapper = field.closest('.input-field');
            if (parentWrapper) parentWrapper.classList.add('invalid-select');
        }
    },

    clearFieldError: function(field) {
        field.classList.remove('invalid');
        field.removeAttribute('aria-invalid');
        let helperTextElement = field.parentElement.querySelector('.helper-text');
        if (helperTextElement) {
            helperTextElement.removeAttribute('data-error');
            // helperTextElement.style.display = 'none'; // Or remove if dynamically added
        }
        if (field.tagName === 'SELECT') {
            const parentWrapper = field.closest('.input-field');
            if (parentWrapper) parentWrapper.classList.remove('invalid-select');
        }
    },
    
    handleAjaxFormSubmit: async function(form, submitButton) {
        const originalButtonText = submitButton.innerHTML;
        this.toggleButtonLoadingState(submitButton, true, {text: 'Processing...'});

        try {
            const formData = new FormData(form);
            const response = await fetch(form.action, {
                method: form.method,
                body: formData,
                headers: {
                    'X-Requested-With': 'XMLHttpRequest', // For Django is_ajax
                    // Add CSRF token if not included in FormData by Django's {% csrf_token %}
                }
            });

            const data = await response.json(); // Assuming JSON response

            if (response.ok) {
                M.toast({html: data.message || 'Success!', classes: 'green darken-1'});
                if (data.redirect_url) {
                    window.location.href = data.redirect_url;
                } else {
                    form.reset(); // Or update parts of the page
                    M.updateTextFields(); // Update labels after reset
                }
            } else {
                M.toast({html: data.error || 'An error occurred.', classes: 'red darken-1'});
                if (data.errors) { // Field-specific errors
                    for (const fieldName in data.errors) {
                        const field = form.querySelector(`[name="${fieldName}"]`);
                        if (field) this.setFieldError(field, data.errors[fieldName].join(', '));
                    }
                }
            }
        } catch (error) {
            this.log("AJAX submission error:", error);
            M.toast({html: 'A network error occurred. Please try again.', classes: 'red darken-1'});
        } finally {
            this.toggleButtonLoadingState(submitButton, false, { originalHtml: originalButtonText });
        }
    },

    toggleButtonLoadingState: function(button, isLoading, options = {}) {
        if (!button) return;
        const { text = 'Loading...', originalHtml = button.innerHTML, spinnerSize = 'small' } = options;

        if (isLoading) {
            button.disabled = true;
            button.dataset.originalHtml = originalHtml; // Store original content
            button.innerHTML = `
                <div class="preloader-wrapper ${spinnerSize} active" style="display: inline-block; vertical-align: middle; width: 20px; height: 20px; margin-right: 8px;">
                    <div class="spinner-layer spinner-white-only"> <!-- Assuming button text is light on dark bg -->
                        <div class="circle-clipper left"><div class="circle"></div></div>
                        <div class="gap-patch"><div class="circle"></div></div>
                        <div class="circle-clipper right"><div class="circle"></div></div>
                    </div>
                </div>
                <span>${text}</span>`;
        } else {
            button.disabled = false;
            button.innerHTML = button.dataset.originalHtml || originalHtml;
            delete button.dataset.originalHtml;
        }
    },
    
    debounce: function(func, delay) {
        let timeout;
        return function(...args) {
            clearTimeout(timeout);
            timeout = setTimeout(() => func.apply(this, args), delay);
        };
    },
    
    initTableEnhancements: function() {
        // Dynamically add data-label for mobile tables if not server-rendered
        document.querySelectorAll('.mobile-table-card table').forEach(table => {
            const headers = Array.from(table.querySelectorAll('thead th')).map(th => th.textContent.trim());
            table.querySelectorAll('tbody tr').forEach(tr => {
                tr.querySelectorAll('td').forEach((td, index) => {
                    if (!td.getAttribute('data-label') && headers[index]) {
                        td.setAttribute('data-label', headers[index] + ': ');
                    }
                });
            });
        });

        // Generic table search and filter initialization
        // Example: For a table with id 'my-table', search input 'my-search', and filter select 'my-filter'
        // this.initTableSearchAndFilter({
        //     tableId: 'sample-table', // As seen in sample_list.html
        //     searchInputId: 'sample-search',
        //     filterConfigs: [
        //         { selectId: 'status-filter', dataAttribute: 'data-status' }
        //         // Add more filter configs if needed
        //     ]
        // });
        // Note: The sample_list.html already has specific JS. This is a generic alternative.
    },

    initTableSearchAndFilter: function(options) {
        const table = document.getElementById(options.tableId);
        if (!table) {
            this.log(`Table with ID ${options.tableId} not found.`);
            return;
        }
        const tableBody = table.querySelector('tbody');
        if (!tableBody) {
            this.log(`Tbody not found in table ${options.tableId}.`);
            return;
        }
        const allRows = Array.from(tableBody.querySelectorAll('tr'));
        let searchInput, filterSelects = [];

        if (options.searchInputId) {
            searchInput = document.getElementById(options.searchInputId);
            if (!searchInput) this.log(`Search input ${options.searchInputId} not found.`);
        }

        if (options.filterConfigs) {
            options.filterConfigs.forEach(config => {
                const select = document.getElementById(config.selectId);
                if (select) {
                    filterSelects.push({element: select, attribute: config.dataAttribute});
                } else {
                    this.log(`Filter select ${config.selectId} not found.`);
                }
            });
        }
        
        const noResultsMessageId = options.noResultsMessageId || `${options.tableId}-no-results`;
        let noResultsMessageEl = document.getElementById(noResultsMessageId);
        if (!noResultsMessageEl && table.parentNode) { // Create if not exists
            noResultsMessageEl = document.createElement('div');
            noResultsMessageEl.id = noResultsMessageId;
            noResultsMessageEl.className = 'center-align p-4 text-muted';
            noResultsMessageEl.style.display = 'none';
            noResultsMessageEl.innerHTML = `<i class="material-icons large grey-text">search_off</i><p>No items match your criteria.</p>`;
            table.parentNode.insertBefore(noResultsMessageEl, table.nextSibling);
        }


        const performFiltering = () => {
            const searchTerm = searchInput ? searchInput.value.toLowerCase() : '';
            const activeFilters = filterSelects.map(f => ({ value: f.element.value, attribute: f.attribute }));
            let visibleRows = 0;

            allRows.forEach(row => {
                let matchesSearch = true;
                if (searchTerm) {
                    matchesSearch = row.textContent.toLowerCase().includes(searchTerm);
                }

                let matchesFilters = true;
                activeFilters.forEach(filter => {
                    if (filter.value && row.getAttribute(filter.attribute) !== filter.value) {
                        matchesFilters = false;
                    }
                });

                if (matchesSearch && matchesFilters) {
                    row.style.display = '';
                    visibleRows++;
                } else {
                    row.style.display = 'none';
                }
            });
            
            if (noResultsMessageEl) {
                noResultsMessageEl.style.display = visibleRows === 0 && allRows.length > 0 ? 'block' : 'none';
                table.style.display = visibleRows > 0 || allRows.length === 0 ? '' : 'none';
            }
        };

        if (searchInput) {
            searchInput.addEventListener('keyup', this.debounce(performFiltering, this.config.defaultDebounceTime));
        }
        filterSelects.forEach(f => f.element.addEventListener('change', performFiltering));
        
        performFiltering(); // Initial filter
    },

    initAccessibilityImprovements: function() {
        // Skip to content link
        const skipLink = document.querySelector('a.skip-link');
        if (skipLink) {
            skipLink.addEventListener('click', function(e) {
                e.preventDefault();
                const targetId = this.getAttribute('href').substring(1);
                const targetElement = document.getElementById(targetId);
                if (targetElement) {
                    targetElement.setAttribute('tabindex', '-1'); // Make it focusable
                    targetElement.focus();
                    // Optional: Remove tabindex after blur to keep tabbing natural
                    // targetElement.addEventListener('blur', () => targetElement.removeAttribute('tabindex'), { once: true });
                }
            });
        }
        
        // Add role="alert" to dynamic message containers (e.g., Django messages)
        document.querySelectorAll('.messages .alert, .card-panel.alert').forEach(alertEl => {
            alertEl.setAttribute('role', 'alert');
            alertEl.setAttribute('aria-live', 'polite'); // Or 'assertive' for very important alerts
        });
    },
    
    _focusableElements: null,
    _currentModal: null,
    _firstFocusableElement: null,
    _lastFocusableElement: null,
    _boundKeyDownHandler: null,

    trapFocus: function(element) {
        this._focusableElements = element.querySelectorAll(
            'a[href], button, textarea, input[type="text"], input[type="radio"], input[type="checkbox"], input[type="submit"], input[type="button"], select, [tabindex]:not([tabindex="-1"])'
        );
        if (this._focusableElements.length === 0) return;

        this._firstFocusableElement = this._focusableElements[0];
        this._lastFocusableElement = this._focusableElements[this._focusableElements.length - 1];
        
        // Focus the first focusable element if it's not the element itself
        if (element !== this._firstFocusableElement && this._firstFocusableElement) {
             // Small delay to ensure modal is fully rendered and focusable
            setTimeout(() => this._firstFocusableElement.focus(), 50);
        }


        this._boundKeyDownHandler = this._handleTrapFocusKeyDown.bind(this);
        element.addEventListener('keydown', this._boundKeyDownHandler);
    },

    releaseFocus: function() {
        if (this._currentModal && this._boundKeyDownHandler) {
            this._currentModal.removeEventListener('keydown', this._boundKeyDownHandler);
        }
    },

    _handleTrapFocusKeyDown: function(e) {
        if (e.key !== 'Tab') return;

        if (e.shiftKey) { // Shift + Tab
            if (document.activeElement === this._firstFocusableElement) {
                this._lastFocusableElement.focus();
                e.preventDefault();
            }
        } else { // Tab
            if (document.activeElement === this._lastFocusableElement) {
                this._firstFocusableElement.focus();
                e.preventDefault();
            }
        }
    },

    initServiceWorker: function() {
        if ('serviceWorker' in navigator) {
            window.addEventListener('load', () => {
                navigator.serviceWorker.register('/sw.js') // Ensure sw.js is in the root directory
                    .then(registration => {
                        this.log('ServiceWorker registration successful with scope: ', registration.scope);
                    })
                    .catch(error => {
                        this.log('ServiceWorker registration failed: ', error);
                    });
            });
        }
    },
    
    initAlerts: function() {
        // Auto-dismiss alerts
        document.querySelectorAll('.alert[data-auto-dismiss]').forEach(alert => {
            const dismissTime = parseInt(alert.getAttribute('data-auto-dismiss'), 10);
            if (!isNaN(dismissTime)) {
                setTimeout(() => this.dismissAlert(alert), dismissTime);
            }
        });

        // Manual close for alerts
        // Use event delegation for dynamically added alerts
        document.body.addEventListener('click', (event) => {
            const closeButton = event.target.closest('.alert .close-alert');
            if (closeButton) {
                event.preventDefault();
                this.dismissAlert(closeButton.closest('.alert'));
            }
        });
    },

    dismissAlert: function(alertElement) {
        if (!alertElement || alertElement.classList.contains('dismissing')) return;
        
        alertElement.classList.add('dismissing');
        alertElement.style.transition = 'opacity 0.3s ease, transform 0.3s ease, margin-bottom 0.3s ease, padding-top 0.3s ease, padding-bottom 0.3s ease, max-height 0.3s ease';
        alertElement.style.opacity = '0';
        alertElement.style.transform = 'scaleY(0.9)';
        alertElement.style.marginTop = '0'; // For alerts that might have margin-top
        alertElement.style.marginBottom = '0';
        alertElement.style.paddingTop = '0';
        alertElement.style.paddingBottom = '0';
        alertElement.style.maxHeight = '0px'; // Animate height collapse
        alertElement.style.overflow = 'hidden';


        setTimeout(() => {
            alertElement.remove();
        }, 300); // Match transition duration
    }
};

// Initialize everything on DOMContentLoaded
document.addEventListener('DOMContentLoaded', () => {
    WaterLab.init();
});
