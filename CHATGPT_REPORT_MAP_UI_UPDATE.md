# Report Map + Dashboard Search UI Update

## Changes made

### Organization dashboard
- Removed the top-right decorative search box from the topbar.
- Removed the duplicate search input inside the Report Locations card.
- Reworked the Report Locations card into a cleaner responsive layout:
  - Left side: Leaflet report map.
  - Right side: recent report location list.
  - Mobile: map and list stack vertically.
- Increased the map height and made it responsive so Leaflet has a real visible container.
- Added a map hint below the map.
- Kept reports without coordinates in the list only.
- Kept the Pin button for reports with coordinates so the org can focus the map marker.

### User dashboard
- Removed the top-right decorative search box from the topbar.
- Kept the actual animal search/filter inside the Browse Animals tab.

### Leaflet fix
- The org map no longer initializes while hidden on page load.
- The map initializes when the Reports tab is shown.
- `map.invalidateSize()` is called after the Reports tab opens so the gray/half-loaded Leaflet tile issue is fixed.
- Added guards to prevent duplicate Leaflet initialization.

## Files modified
- `templates/org_dashboard.html`
- `templates/user_dashboard.html`
- `static/css/org_dashboard.css`

## How to test after extracting
```powershell
py manage.py check
py manage.py test
py manage.py runserver
```

Then open the organization dashboard:
1. Click **Reports**.
2. The Report Locations card should show a real Leaflet map on the left.
3. Recent locations should show in the list on the right.
4. Click **Pin** on a list item to focus the matching marker.
5. Confirm the top-right searchbar is gone in both user and org dashboards.

## Note
I could not run Django checks/tests in the sandbox because Django is not installed in this environment. The files were edited directly and basic syntax/file checks were performed.
