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
      if (!res.ok) {
        // Fallback to bundled static data
        res = await fetch('/static/js/kerala_address_data.json', {cache: 'no-store'});
      }
      data = await res.json();
    } catch (e) {
      console.warn('Failed to load kerala_address_data.json', e);
    }

    // Helper to (re)fill select options
    function setOptions(select, items) {
      const isTom = !!select.tomselect;
      if (isTom) select.tomselect.clearOptions();
      select.innerHTML = '';
      const blank = document.createElement('option');
      blank.value = ''; blank.textContent = '---------';
      select.appendChild(blank);
      (items||[]).forEach(v => {
        const opt = document.createElement('option');
        opt.value = v; opt.textContent = v;
        select.appendChild(opt);
      });
      if (isTom) {
        (items||[]).forEach(v => select.tomselect.addOption({value:v, text:v}));
        select.tomselect.refreshOptions(false);
      }
    }

    // Enhance selects with TomSelect
    function enhance(select, placeholder) {
      if (!window.TomSelect || select.tomselect) return;
      new TomSelect(select, {
        create: false,
        allowEmptyOption: true,
        maxItems: 1,
        placeholder: placeholder || 'Select...',
        closeAfterSelect: true,
        selectOnTab: true,
        onItemAdd: function(){ this.close(); this.blur(); }
      });
    }

    enhance(districtEl, 'Search district');
    enhance(talukEl, 'Search taluk');
    enhance(panchayatEl, 'Search panchayat/municipality');

    function onDistrictChanged() {
      const d = districtEl.value || districtEl.options[districtEl.selectedIndex]?.value;
      const taluks = d && data[d] ? Object.keys(data[d]) : [];
      setOptions(talukEl, taluks);
      setOptions(panchayatEl, []);
      if (talukEl.tomselect) talukEl.tomselect.clear(true);
      if (panchayatEl.tomselect) panchayatEl.tomselect.clear(true);
      // update composed address
      const changeEvent = new Event('change');
      talukEl.dispatchEvent(changeEvent);
    }

    function onTalukChanged() {
      const d = districtEl.value || districtEl.options[districtEl.selectedIndex]?.value;
      const t = talukEl.value || talukEl.options[talukEl.selectedIndex]?.value;
      const bodies = (d && t && data[d] && data[d][t]) ? data[d][t] : [];
      setOptions(panchayatEl, bodies);
      if (panchayatEl.tomselect) panchayatEl.tomselect.clear(true);
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
