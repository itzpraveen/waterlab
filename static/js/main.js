// static/js/main.js

if (typeof window.M === 'undefined') {
    window.M = {
        FormSelect: { init: () => {}, getInstance: () => null },
        Tooltip: { init: () => {} },
        Dropdown: { init: () => {} },
        Collapsible: { init: () => {} },
        textareaAutoResize: () => {},
        updateTextFields: () => {},
        toast: () => {}
    };
}

const WaterLab = {
    config: {
        debug: true,
        defaultDebounceTime: 250,
    },

    log(...args) {
        if (this.config.debug) {
            console.log('WaterLab:', ...args);
        }
    },

    init() {
        this.log('Initialising WaterLab helpers');
        this.initBootstrapHelpers();
        this.initTableFilters();
        this.initAddressDropdowns();
        this.initServiceWorker();
    },

    initBootstrapHelpers() {
        if (typeof bootstrap === 'undefined') {
            return;
        }
        document.querySelectorAll('[data-bs-toggle="tooltip"]').forEach((el) => {
            new bootstrap.Tooltip(el);
        });
    },

    initTableFilters() {
        const filterInputs = document.querySelectorAll('[data-table-search]');
        filterInputs.forEach((input) => {
            const tableSelector = input.getAttribute('data-table-search');
            const table = document.querySelector(tableSelector);
            if (!table) {
                return;
            }
            const rows = Array.from(table.querySelectorAll('tbody tr'));
            const statusSelectSelector = input.getAttribute('data-status-filter');
            const statusSelect = statusSelectSelector ? document.querySelector(statusSelectSelector) : null;
            const emptyStateSelector = input.getAttribute('data-empty-state');
            const emptyState = emptyStateSelector ? document.querySelector(emptyStateSelector) : null;
            const tableWrapper = table.closest('[data-table-wrapper]');

            const applyFilter = () => {
                const searchValue = input.value.trim().toLowerCase();
                const statusValue = statusSelect ? statusSelect.value : '';
                let visibleCount = 0;

                rows.forEach((row) => {
                    const textMatch = !searchValue || row.textContent.toLowerCase().includes(searchValue);
                    const statusMatch = !statusValue || row.dataset.status === statusValue;
                    const isVisible = textMatch && statusMatch;
                    row.style.display = isVisible ? '' : 'none';
                    if (isVisible) {
                        visibleCount += 1;
                    }
                });

                if (emptyState) {
                    const showEmpty = visibleCount === 0;
                    emptyState.classList.toggle('d-none', !showEmpty);
                    if (tableWrapper) {
                        tableWrapper.classList.toggle('d-none', showEmpty);
                    }
                }
            };

            const debouncedFilter = this.debounce(applyFilter.bind(this), this.config.defaultDebounceTime);
            input.addEventListener('input', debouncedFilter);
            if (statusSelect) {
                statusSelect.addEventListener('change', debouncedFilter);
            }
            applyFilter();
        });
    },

    // Address dropdown logic -------------------------------------------------
    _keralaAddressData: null,

    async loadAddressData() {
        if (this._keralaAddressData) {
            return this._keralaAddressData;
        }
        try {
            const response = await fetch('/static/js/kerala_address_data.json');
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}`);
            }
            this._keralaAddressData = await response.json();
            return this._keralaAddressData;
        } catch (error) {
            this.log('Failed to load Kerala address data', error);
            return null;
        }
    },

    populateDropdown(selectElement, options, placeholder = '---------') {
        if (!selectElement) {
            return;
        }
        const currentValue = selectElement.value;
        selectElement.innerHTML = '';

        const defaultOption = document.createElement('option');
        defaultOption.value = '';
        defaultOption.textContent = placeholder;
        selectElement.appendChild(defaultOption);

        if (Array.isArray(options)) {
            options.forEach((option) => {
                const opt = document.createElement('option');
                opt.value = option;
                opt.textContent = option;
                selectElement.appendChild(opt);
            });
        }

        if (options && options.includes(currentValue)) {
            selectElement.value = currentValue;
        }
    },

    async updateTalukDropdown(districtId = 'id_district', talukId = 'id_taluk', panchayatId = 'id_panchayat_municipality') {
        const districtSelect = document.getElementById(districtId);
        const talukSelect = document.getElementById(talukId);
        const panchayatSelect = document.getElementById(panchayatId);
        if (!districtSelect || !talukSelect || !panchayatSelect) {
            return;
        }

        const district = districtSelect.value;
        const data = await this.loadAddressData();
        if (!data || !district || !data[district]) {
            this.populateDropdown(talukSelect, []);
            this.populateDropdown(panchayatSelect, []);
            talukSelect.disabled = !district;
            panchayatSelect.disabled = true;
            return;
        }

        const taluks = Object.keys(data[district]);
        this.populateDropdown(talukSelect, taluks, 'Select Taluk');
        talukSelect.disabled = false;

        if (talukSelect.value) {
            await this.updatePanchayatDropdown(districtId, talukId, panchayatId, true);
        } else {
            this.populateDropdown(panchayatSelect, []);
            panchayatSelect.disabled = true;
        }
    },

    async updatePanchayatDropdown(districtId = 'id_district', talukId = 'id_taluk', panchayatId = 'id_panchayat_municipality', isChained = false) {
        const districtSelect = document.getElementById(districtId);
        const talukSelect = document.getElementById(talukId);
        const panchayatSelect = document.getElementById(panchayatId);
        if (!districtSelect || !talukSelect || !panchayatSelect) {
            return;
        }
        const district = districtSelect.value;
        const taluk = talukSelect.value;
        const data = await this.loadAddressData();
        if (!data || !district || !taluk || !data[district] || !data[district][taluk]) {
            this.populateDropdown(panchayatSelect, []);
            panchayatSelect.disabled = true;
            return;
        }

        const options = data[district][taluk] || [];
        this.populateDropdown(panchayatSelect, options, 'Select Panchayat / Municipality');
        panchayatSelect.disabled = options.length === 0;

        if (isChained && options.includes(panchayatSelect.dataset.initialValue)) {
            panchayatSelect.value = panchayatSelect.dataset.initialValue;
        }
    },

    initAddressDropdowns() {
        const districtSelect = document.getElementById('id_district');
        const talukSelect = document.getElementById('id_taluk');
        const panchayatSelect = document.getElementById('id_panchayat_municipality');
        if (!districtSelect || !talukSelect || !panchayatSelect) {
            return;
        }
        panchayatSelect.dataset.initialValue = panchayatSelect.value;

        districtSelect.addEventListener('change', () => {
            this.updateTalukDropdown();
        });

        talukSelect.addEventListener('change', () => {
            this.updatePanchayatDropdown();
        });

        this.updateTalukDropdown();
    },

    debounce(fn, delay) {
        let timer;
        return function (...args) {
            clearTimeout(timer);
            timer = setTimeout(() => fn.apply(this, args), delay);
        };
    },

    initServiceWorker() {
        if ('serviceWorker' in navigator) {
            navigator.serviceWorker.register('/sw.js').catch((error) => {
                this.log('Service worker registration failed', error);
            });
        }
    },
};

document.addEventListener('DOMContentLoaded', () => {
    WaterLab.init();
});
