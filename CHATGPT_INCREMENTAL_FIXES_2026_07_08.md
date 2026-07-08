# Incremental Fixes — July 8, 2026

## Issues addressed

### 1. Action modal text appearing in the top-right corner
- Cause: Organization dashboard used the shared action modal JavaScript, but the organization stylesheet did not define the `.action-feedback-*` modal styles.
- Fix: Added complete action feedback modal styling to `static/css/org_dashboard.css` and bumped the org CSS cache version in `templates/org_dashboard.html`.

### 2. Announcement buttons not working properly
- Cause: Active announcement cards did not include the data attributes required by the edit modal JavaScript.
- Fix: Added `data-edit-url`, `data-title`, `data-body`, and `data-type` to active announcement cards and exposed the edit/archive handlers on `window`.

### 3. Export modal staying forever
- Cause: CSV downloads do not always navigate away from the current page, so the processing modal had no follow-up state.
- Fix: Export actions now download through a hidden iframe, then automatically switch from “Preparing export” to “Export ready.”

### 4. Create account UI not optimized
- Cause: Registration page was a long single-column form with all fields stacked.
- Fix: Rebuilt the registration template into clear sections:
  - Account details
  - Personal contact
  - Rescue organization profile, only for organization accounts
  - Verification and submit
- Added responsive two-column layout, better placeholders, section headings, role badge, and improved scrolling.

### 5. Map visible while editing/responding to reports
- Cause: Leaflet map layers can use high z-index values and appear above or through overlays.
- Fix: Lowered Leaflet z-index and raised modal/action modal z-index. Also strengthened modal overlay opacity.

## Files changed
- `templates/org_dashboard.html`
- `templates/register.html`
- `static/css/org_dashboard.css`
- `static/css/login.css`
- `static/js/dashboard.js`
- `templates/dashboard.html`
- `core/forms.py`

## Validation
- `python manage.py check` — passed
- `python manage.py test` — passed, 24 tests OK
