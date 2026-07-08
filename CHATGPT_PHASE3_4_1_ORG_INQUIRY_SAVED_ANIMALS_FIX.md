# Phase 3.4.1 — Org Inquiry Switching + Saved Animals Card Alignment

## Changes made

### Organization dashboard adoption inquiries
- Added a named `openOrgInquiryThread(event, inquiryId)` function.
- Added direct `onclick` support to each inquiry list item.
- Kept delegated click handling as a fallback.
- Only the selected inquiry thread is visible.
- The clicked inquiry is highlighted.
- On mobile, the selected thread scrolls into view after tapping an inquiry.

### User dashboard saved animals
- Applied the same consistent animal card layout used in Browse Animals.
- Moved status badge above the animal name.
- Added scrollable detail content for sex/species/age, assigned organization, location, and vaccination.
- Removed duplicate image status overlay in saved animal cards.
- Buttons now stay aligned at the bottom of the card.

## Notes
- No backend model or migration changes were required.
- This is a frontend/template stability patch.
