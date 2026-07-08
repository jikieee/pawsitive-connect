# Phase 3 Mobile Incremental Fixes

## Issues addressed

1. **Registration mobile scrolling**
   - Fixed the mobile registration layout so long User and Rescue Organization signup forms can scroll properly.
   - Left branding panel remains hidden on mobile; the form panel now scrolls naturally.

2. **Adoption inquiry reply input**
   - Replaced the small one-line organization reply input with a taller textarea.
   - Added mobile-friendly sizing for the inquiry reply form.

3. **Archived announcements on mobile**
   - Forced the announcements layout to stack into one column on mobile.
   - Keeps Post New Announcement visible, followed by Active and Archived announcements.
   - Restore/Edit/Archive buttons are now easier to reach on phone screens.

4. **Map bleeding through mobile modals**
   - Added stronger z-index rules for modal overlays and Leaflet map layers.
   - Prevents the report map from appearing above success/respond modals.

5. **Report viewing vs responding**
   - The report modal now supports a real View mode and Respond mode.
   - View mode displays report details: animal, condition, reporter, status, date, location, description, notes, and photo when available.
   - Respond mode still shows status/notes controls for organization actions.

6. **Track Rescue timeline uses real status data**
   - Updated report timeline logic so steps only appear after the relevant status has actually happened.
   - Pending reports now show only submitted + waiting for organization review.
   - Later steps appear as the report status changes.
   - Added lightweight auto-refresh every 30 seconds while the tracking tab is open.

7. **Images instead of icons when uploaded**
   - User avatars, organization logos, rescued animal photos, saved animal photos, report photos, and inquiry avatars now display uploaded images when available.
   - Emoji/icons remain as fallback only when no uploaded image exists.

## Files modified

- `reports/models.py`
- `accounts/views.py`
- `organizations/views.py`
- `templates/user_dashboard.html`
- `templates/org_dashboard.html`
- `static/css/login.css`
- `static/css/phase3_mobile.css`
- `static/css/org_dashboard.css`
- `static/js/dashboard.js`

## Validation

Commands run:

```powershell
python manage.py check
python manage.py test
```

Result:

```text
System check identified no issues.
Ran 24 tests — OK
```
