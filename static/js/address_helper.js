// Address enhancement: searchable dropdowns + cascading population
// Requires TomSelect (already used elsewhere in the app)

(function() {
  function ready(fn){ if(document.readyState!=='loading'){ fn(); } else { document.addEventListener('DOMContentLoaded', fn); } }

  ready(async function() {
    const districtEl = document.getElementById('id_district');
    const talukEl = document.getElementById('id_taluk');
    const panchayatEl = document.getElementById('id_panchayat_municipality');
    const villageEl = document.getElementById('id_village_town_city');

    if (!districtEl || !talukEl || !panchayatEl) return;

    // Load dataset
    let data = {};
    try {
      // Prefer DB-backed endpoint so admins can update locations
      let res = await fetch('/address/kerala.json', {cache: 'no-store'});
      let loaded = false;
      if (res.ok) {
        try {
          const txt = await res.text();
          if (txt && txt.trim().length) { data = JSON.parse(txt); loaded = true; }
        } catch (_) { /* fall back below */ }
      }
      if (!loaded) {
        const res2 = await fetch('/static/js/kerala_address_data.json', {cache: 'no-store'});
        data = await res2.json();
      }
    } catch (e) {
      console.warn('Failed to load kerala address data; fields may be empty', e);
      data = {};
    }

    // Helper to (re)fill select options
    function setOptions(select, items, config = {}) {
      const opts = Array.isArray(items) ? items : [];
      const selectPlaceholder = select.dataset.tsPlaceholder || select.dataset.placeholder || 'Select...';
      const emptyLabel = config.emptyLabel || select.dataset.tsEmptyLabel || 'No options available';
      const previousValue = select.value;
      const shouldDisable = opts.length === 0;

      if (select.tomselect) {
        const ts = select.tomselect;
        ts.clearOptions();
        ts.addOptions(opts.map(v => ({ value: v, text: v })));
        const nextPlaceholder = shouldDisable ? emptyLabel : selectPlaceholder;
        ts.settings.placeholder = nextPlaceholder;
        if (ts.control_input) {
          ts.control_input.placeholder = nextPlaceholder;
        }
        if (shouldDisable) {
          ts.clear(true);
          ts.disable();
          select.setAttribute('disabled', 'disabled');
        } else {
          ts.enable();
          select.removeAttribute('disabled');
          if (previousValue && opts.includes(previousValue)) {
            ts.setValue(previousValue, true);
          } else {
            ts.clear(true);
          }
        }
        if (typeof ts.inputState === 'function') {
          ts.inputState();
        }
        ts.refreshOptions(false);
        return;
      }
      // Non-TomSelect fallback
      select.innerHTML = '';
      const blank = document.createElement('option');
      blank.value = '';
      blank.textContent = shouldDisable ? emptyLabel : '---------';
      select.appendChild(blank);
      opts.forEach(v => {
        const opt = document.createElement('option');
        opt.value = v; opt.textContent = v;
        select.appendChild(opt);
      });
      if (shouldDisable) {
        select.value = '';
        select.setAttribute('disabled', 'disabled');
      } else {
        select.removeAttribute('disabled');
        if (previousValue && opts.includes(previousValue)) {
          select.value = previousValue;
        }
      }
    }

    // Enhance selects with TomSelect
    function enhance(select, placeholder) {
      if (!window.TomSelect || select.tomselect) return;
      const basePlaceholder = placeholder || 'Select...';
      select.dataset.tsPlaceholder = basePlaceholder;
      const ts = new TomSelect(select, {
        create: false,
        allowEmptyOption: true,
        maxItems: 1,
        sortField: {
          field: 'text',
          direction: 'asc'
        },
        searchField: ['text'],
        placeholder: basePlaceholder,
        closeAfterSelect: true,
        selectOnTab: true,
        openOnFocus: true,
        plugins: ['dropdown_input'],
        render: {
          no_results: (data, escape) => '<div class="no-results">No matches found for "' + escape(data.input) + '"</div>'
        },
        onItemAdd: function(){
          this.close();
          this.blur();
        },
        onFocus: function() {
          this.open();
        }
      });

      ts.on('initialize', () => {
        const dropdownInput = ts.dropdown && ts.dropdown.querySelector('.dropdown-input input');
        const searchPlaceholder = basePlaceholder;
        if (dropdownInput) {
          dropdownInput.placeholder = searchPlaceholder;
          dropdownInput.setAttribute('aria-label', searchPlaceholder);
        }
      });
    }

    enhance(districtEl, 'Search district');
    enhance(talukEl, 'Search taluk');
    enhance(panchayatEl, 'Search panchayat/municipality');

    function onDistrictChanged() {
      const d = districtEl.value || districtEl.options[districtEl.selectedIndex]?.value;
      const taluks = d && data[d] ? Object.keys(data[d]) : [];
      setOptions(talukEl, taluks, { emptyLabel: 'Select a district first' });
      setOptions(panchayatEl, [], { emptyLabel: 'Select a taluk first' });
      // update composed address
      const changeEvent = new Event('change');
      talukEl.dispatchEvent(changeEvent);
    }

    function onTalukChanged() {
      const d = districtEl.value || districtEl.options[districtEl.selectedIndex]?.value;
      const t = talukEl.value || talukEl.options[talukEl.selectedIndex]?.value;
      const bodies = (d && t && data[d] && data[d][t]) ? data[d][t] : [];
      setOptions(panchayatEl, bodies, { emptyLabel: 'Select a taluk first' });
      // update composed address
      const changeEvent = new Event('change');
      panchayatEl.dispatchEvent(changeEvent);
    }

    districtEl.addEventListener('change', onDistrictChanged);
    talukEl.addEventListener('change', onTalukChanged);

    // If district already selected (edit form), seed dependent options
    if (districtEl.value) {
      onDistrictChanged();
      if (talukEl.value) onTalukChanged();
    }

    // Minimal assist: when a panchayat is chosen, suggest city text if empty
    if (villageEl) {
      panchayatEl.addEventListener('change', () => {
        if (!villageEl.value && panchayatEl.value) {
          villageEl.value = panchayatEl.value;
          villageEl.dispatchEvent(new Event('input'));
        }
      });
    }
  });
})();
