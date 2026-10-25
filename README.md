# TAPAS Group website

Read START-HERE.md for the local browser editor and Mac launch instructions.

The homepage contains TAPAS branding, Muni’s profile, an illustrated research introduction, nine project cards, and a green joining/contact section. Team uses three-column portrait cards with expandable profiles, automatically alphabetized by surname including the PI; mobile layouts use fewer columns. Missing photos use initials. Publications are a continuous list ordered newest first with full author lists. Essential Numerical Methods has been removed from Other Teaching.

Run `python3 editor/server.py` for a local form editor and static preview. Run `python3 render.py` to rebuild the static site manually. All required Python modules are in the standard library. No Node installation is needed for local editing.

Content: content.json, publications-source.json, teaching.json. Presentation: render.py and dist/assets/site.css. Homepage and general-page decorative simulation crops remain unchanged; research-topic headers use the selected topic image. The shared image library supports batch/drop upload, thumbnail browsing, search, reuse, and byte-preserving originals. Project covers default to contain and optionally use a CSS-only crop with adjustable object position; project figures always retain their full aspect ratio. The editor stores automatic JSON backups locally and exports portable ZIP files. Backups and credentials are excluded from exports.

Local editing does not deploy. The existing private Sites preview and WordPress domain remain independent until an explicit publishing step. Only munizhou/munizhou.github.io is authorized for any future GitHub migration; entity-toolkit is out of scope.

## Project media

No content migration is required. Existing JSON records and artwork remain valid. In `content.json`, each object inside `areas[].projects[]` may have:

```json
{
  "cover": {
    "image": "kinetic.png",
    "alt": "Descriptive alternative text",
    "fit": "contain",
    "position": {"x": 50, "y": 50}
  },
  "figures": [
    {"image": "kinetic.png", "caption": "Visible caption", "alt": "Descriptive alternative text"}
  ]
}
```

`cover.fit` is `contain` (default) or `cover`; position values are percentages from 0 to 100. Covers override the corresponding homepage card's existing `art` and appear in the project detail section. Removing a cover restores the original homepage artwork. `figures` order is the displayed order; each caption is independent even when reusing an image. Captions are escaped plain text and retain line breaks. No image pixels are cropped, resized, recompressed, or overwritten. Clicking a scientific figure opens its untouched original; repeated visible original-file links are omitted.

Images remain in `dist/assets/`. Uploads use a content hash and sanitized original filename; identical bytes reuse an existing asset. `/api/images` returns records with `name`, `size`, `modified`, and `kind`. New uploads accept PNG, JPEG, and WebP (20 MB each), plus MP4 (100 MB). Existing SVG assets remain browsable. MP4 is available for project covers and detail figures, with native video controls in project details and muted looping playback on homepage cards. Topic backgrounds and portraits remain image-only. Files copied directly into `dist/assets/` appear when opening the picker or clicking its refresh button. Uploading adds an original immediately; content references are only committed by Save. Undo changes the content references, retaining originals for reuse and restoration. Export includes originals and the editor's JS/CSS; backups are excluded. Development snapshots are in `local-backups/development/`, outside the content-undo history.

## Local verification

Run `python3 -m unittest discover -s tests -v`. The integration tests copy the project to a temporary folder and exercise legacy compatibility, media validation, upload deduplication and original bytes, covers and figure rendering, export, save/undo, and rollback after a failed build. They do not change the live content or connect to external services. The editor still requires only Python's standard library.

## Local preview updates

Each successful build writes a shared revision to the generated pages and publishes `dist/assets/preview-version.json` last. On loopback HTTP addresses only, `site.js` checks that revision and refreshes open previews after Save or Undo, preserving the current page and project anchor. Hidden tabs check when revisited; hosted websites do not poll. Revisioned CSS/JS URLs and fresh local-server responses avoid stale browser caches. Existing preview tabs need one manual refresh to load this behavior. Downloaded ZIP files remain snapshots and must be exported again after further saves.

Theme pages place the title, question, description and project links over a translucent theme image. This decorative background uses a display-only cover crop and white overlay for readability; the original file is retained. It uses areas[].image, falling back to overview_visual.image. Individual project text and covers remain side by side on desktop and stack on phones.

Optional developer checks for local-preview behavior: `node --test tests/preview-refresh.test.cjs` (Node is not required for normal editing).

Public pages omit breadcrumbs, decorative credits, project numbering/status labels, duplicate eyebrow labels, and repeated contact prompts. The footer Explore links and topic keyword/caption fields are also hidden. Saved content and project figure captions are retained.

The public layout uses a compact, centered main column with a theme sidebar on Research pages. The Research overview is a continuous page of themes with a sticky left theme sidebar linking to individual theme pages, text beside uncropped figures, and expandable Projects and Key references lists; project covers sit beside their descriptions on desktop and stack on mobile. Section spacing and media sizes are kept compact across Home, Research, Team, Publications, and Teaching. Content JSON is unchanged by layout work.

Editor ordering: Research topics and per-topic projects have up/down controls. Homepage highlights have independent ordering controls under 首页 → 首页项目卡片. Reordering only moves whole records; IDs, media, and publication references remain unchanged. Save/Undo use the existing content backups. Open disclosure panels follow moved records.

Research navigation opens the first theme in content order directly (currently Magnetogenesis). The /research/ route redirects to that theme; there is no separate overview page. The theme sidebar remains available on all theme pages.
