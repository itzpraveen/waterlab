# UI Refresh Coverage

Summary of templates aligned with the new WaterLab look and remaining legacy layouts.

## Completed
- `core/base.html`
- `core/dashboards/*.html`
- `core/sample_detail.html`
- `core/sample_list.html`
- `core/test_result_entry.html`
- `core/test_result_list.html`
- `core/setup_test_parameters.html`
- `core/test_parameter_form.html`
- `registration/login.html`

## Legacy (needs update)
- `core/customer_detail.html`
- `core/customer_form.html`
- `core/customer_list.html`
- `core/sample_form.html`
- `core/dashboard.html`
- `core/test_result_detail.html`
- `core/consultant_review.html`
- and other legacy Materialize-driven templates.

## Next Steps
- Prioritise forms (`customer_form`, `sample_form`) to match the new design tokens.
- Replace remaining Materialize helper classes with shared `form-control` styles.
- Revise `core/dashboard.html` fallback and any `collection` style lists.
