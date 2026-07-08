# Phase 3.4 Polish Fixes

## Changes made

### 1. Adoption inquiry list/thread behavior
- Added user-side adoption inquiry list + selected thread layout.
- Only the selected inquiry conversation is visible at a time.
- Added click handling for user inquiry list items.
- Strengthened existing org inquiry list/thread behavior by preserving the selected-panel structure.

### 2. User Browse Animals filtering
- User Browse Animals now excludes unassigned/demo animals.
- The public browse page only shows animals linked to an actual rescue organization and excludes adopted animals.
- Adoption inquiry dropdown remains limited to animals actually open for adoption.

### 3. Organization registration coordinates
- Added organization latitude and longitude fields to the rescue organization registration form.
- Saved latitude/longitude to `RescueOrganization` on signup.
- Added a “Use my current location” button that fills coordinates using browser geolocation when available.

### 4. Animal card layout consistency
- Animal cards now use a flex layout so action buttons align at the bottom.
- Animal details are listed line-by-line inside a scrollable content area.
- Status badges are centered above the animal name instead of sitting over the photo.
- Applied to both User and Organization dashboard animal cards.

### 5. Landing page stats
- Replaced hardcoded landing stats with database-driven counts:
  - total reports
  - rescued reports
  - adoptable animals
- Stats update when the role selection page is refreshed/reopened.

## Validation
- Python syntax check passed:
  - `python -m py_compile core/views.py core/forms.py accounts/views.py organizations/views.py`
- JavaScript syntax check passed:
  - `node --check static/js/dashboard.js`

## Notes
- These are dynamic-on-load stats, not WebSocket real-time stats. Refreshing/reopening the landing page shows updated database values.
