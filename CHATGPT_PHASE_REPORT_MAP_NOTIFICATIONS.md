# ChatGPT Phase: Org Report Map + Notification Badge Fix

## Changes made

### Organization Dashboard Report Locations
- Replaced the static Report Locations placeholder with a Leaflet-powered map.
- Added map pins for recent organization reports that have latitude/longitude.
- Added marker popups showing:
  - report ID
  - animal type and condition
  - reporter name
  - exact location
  - status
  - reported date
- Added a searchable report location list below the map.
- Search supports reporter name, report ID, location, animal type, condition, and status.
- Reports without coordinates still appear in the list, but do not get map pins.

### Notification badge fix
- Updated notification mark-read responses to return the remaining unread count.
- Updated frontend badge handling so `Mark all as read` sets all `[data-notif-count]` badges to the returned unread count, usually `0`.
- Kept the sidebar Notifications page as the notification source of truth.

## Files modified
- `organizations/views.py`
- `templates/org_dashboard.html`
- `static/css/org_dashboard.css`
- `static/js/dashboard.js`
- `accounts/views.py`
- `core/views.py`

## Validation
The sandbox environment does not have Django installed, so Django tests could not be run here.

Syntax checks completed:
- `python -m py_compile organizations/views.py core/views.py accounts/views.py`
- `node --check static/js/dashboard.js`

After extracting locally, run:

```powershell
py manage.py check
py manage.py test
```

## Manual checks
1. Org dashboard → Reports → Report Locations shows a map.
2. Reports with coordinates appear as pins.
3. Search filters report list by reporter/location/report ID.
4. Clicking `Pin` focuses the map marker.
5. Notifications → Mark all as read updates the sidebar badge to `0` without refresh.
