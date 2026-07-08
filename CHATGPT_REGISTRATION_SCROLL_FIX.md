# Registration Scroll Fix

## Issue
The Rescue Organization registration form is longer than the visible browser height on desktop. The bottom fields/actions can be hard to reach because the page uses a two-panel fixed layout.

## Fix
- Kept the existing two-panel registration layout.
- Made only the right registration panel scrollable on desktop.
- Kept the left Pawsitive Connect branding panel fixed/sticky.
- Added a sticky submit section so the create-account button remains usable near the bottom of the scroll area.
- Added a CSS cache-buster for `login.css` in `register.html`.

## Files changed
- `templates/register.html`
- `static/css/login.css`

## How to verify
1. Open `/register/`.
2. Choose Rescue Organization.
3. Confirm the right-side form scrolls independently.
4. Confirm the left branding panel stays fixed.
5. Confirm the create-account/sign-in section remains reachable.
