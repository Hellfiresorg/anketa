# Анкета — Design System

**Анкета** (Anketa, *"questionnaire"*) is a Russian-language voice-survey tool used by reception managers to gather pre-visit information from clients. A manager generates a personal link and sends it to the client; the client opens it in their browser, answers each question by voice (or types), and submits. Audio is automatically transcribed via Groq Whisper. Managers review and export the results from an admin panel.

Two end-user surfaces ship today:

- **Client survey form** (`/s/:invitationId`) — mobile-first, no login, one-screen-per-question flow, microphone-driven.
- **Admin panel** — desktop-first, JWT-authenticated, table of invitations + per-invitation detail view with audio players, transcriptions, export, and retranscribe actions.

The product is internal-facing, Russian-only, serving ~4 managers and up to 50 surveys/month.

---

## Sources

This design system was derived from:

- **Local codebase** (`anketa/` via File System Access API)
  - `anketa/frontend-client/` — Vite + React + Tailwind client app
  - `anketa/frontend-admin/` — Vite + React + Tailwind admin app
  - `anketa/backend/` — FastAPI (not used for visual design, only for domain model)
  - `anketa/README.md`, `anketa/DOC.md`, `anketa/.omc/prd.json` — product spec + API docs

No Figma, no external brand docs, no design-system definition. Everything below is reconstructed from the Tailwind configs, `index.css` utility layers, JSX of five client screens and five admin pages, and the sole SVG asset: a square placeholder logo reading "LOGO" in white on `#102f6e`.

---

## Index

Root files:

- `README.md` — this file
- `SKILL.md` — agent-skill entry point
- `colors_and_type.css` — CSS custom properties: palette, type scale, spacing, radii, shadows, semantic element styles
- `fonts/` — web fonts (none bundled; using system stack)
- `assets/` — logos and brand marks
- `preview/` — small HTML cards that populate the Design System tab
- `ui_kits/client/` — recreation of the public client survey flow
- `ui_kits/admin/` — recreation of the manager admin panel

---

## Content fundamentals

### Language

- **Russian only.** Every string in the app is Cyrillic. No English copy is shown to end users. The product name is "Голосовые анкеты" / "Анкеты" in the admin nav.
- Keep copy in Russian when generating new designs. If you need placeholder names, use Russian first names (Иван, Анна, Ольга).

### Voice and tone

The writing is **plain, direct, administrative, and deferential**. No marketing voice, no jokes, no metaphors. Think "hotel reception paperwork" rather than "friendly SaaS onboarding." Concrete examples from the codebase:

- `"Добро пожаловать, {name}!"` — survey welcome (formal-warm)
- `"Вам предстоит ответить на 10 вопросов."` — literal, uses the formal "you" (`Вам`)
- `"Нажмите на вопрос, чтобы отредактировать ответ."` — instructional, imperative, polite
- `"Ваша анкета успешно отправлена. Мы свяжемся с вами в ближайшее время."` — thank-you screen, passive and professional
- `"Анкета уже заполнена"` / `"Редактирование недоступно. Ниже — ваши ответы."` — read-only state, matter-of-fact

### Pronouns & register

- **Client-facing copy uses formal "Вы"/"Вам"/"Ваши"** (capitalized when addressing the user directly, consistent with Russian formal convention).
- **Admin copy addresses the manager in imperative verbs** — `"Войти"`, `"Создать анкету"`, `"Экспорт"`, `"Удалить"`, `"Перетранскрибировать"`. No pronouns needed.
- Avoid first-person plural ("мы") except in the thank-you line ("Мы свяжемся с вами") where it reads as the business promising a callback.

### Casing

- **Russian sentence case** for every label, heading, and button. No Title Case, no ALL CAPS, no smallcaps. "Создать анкету" not "Создать Анкету".
- Badges/status chips also use sentence case: `Ожидает`, `Заполняется`, `Заполнено`, `Готово`, `Ошибка`.

### Length

- Headings are 1–4 words. Body copy sticks to one short sentence per paragraph. Error messages are a single sentence, no periods dropped.
- Hints under questions are italicized and short ("подсказка под вопросом").

### Punctuation specifics

- Dashes: em-dashes are used as a fallback for empty cells in tables (`—`). Not hyphens.
- Long-dash sentences follow Russian convention ("Редактирование недоступно. Ниже — ваши ответы.").
- Ellipses appear on loading states: `"Отправляем анкету..."`, `"Вход..."`, `"Создание..."`.

### Emoji

- Emoji **are** used, sparingly, as single-glyph accents — never as icons in a component library sense.
- Observed usage, reproduce as-is:
  - `🎤` inside the voice-input button
  - `✅` on the thank-you screen and the "invitation created" success card
  - `←` / `→` for back-links and pagination ("← Назад", "Далее →")
  - `▾` on the Export dropdown toggle
  - `✓` as the post-copy confirmation ("✓ Скопировано")
  - `+` as part of button labels ("+ Создать анкету")
- Do **not** introduce new decorative emoji when extending the system. If iconography is needed, add proper SVG icons and document them under `ICONOGRAPHY`.

### Vibe

Russian administrative web: competent, quiet, respectful of the user's time. Think "госуслуги" or a reception-desk workflow, stripped of ornament.

---

## Visual foundations

### Palette

The entire product rides on **one brand color**: deep navy `#102f6e` (a.k.a. `primary-800` in the Tailwind scale). Everything else is neutral grays plus four tiny semantic chips.

- **Primary** — `#102f6e`. Used for: primary buttons, key headings (`.text-primary`), logo fill, focus rings, active pagination. The full ramp `primary-50`…`primary-900` exists in Tailwind but in practice only `DEFAULT` (=800), `700`, and `50` are used.
- **Neutrals** — Tailwind's default `gray` scale. `gray-50` for app background, `gray-100` for subtle progress-bar track, `gray-200` for borders on cards and tables, `gray-300` for form borders, `gray-400`/`500` for secondary text, `gray-600`/`700` for labels and secondary headings, `gray-800`/`900` for primary text.
- **Canvas** — Surveys sit on pure white (`#ffffff`); the admin app sits on `gray-50` (`#f9fafb`) so cards can float as white.
- **Semantic chips** — only appear as small badges with matching bg/text pairs:
  - `yellow-100 / yellow-800` — pending
  - `blue-100 / blue-800` — in progress
  - `green-100 / green-800` — completed / done / success banner
  - `red-100 / red-800` — failed
  - `amber-50 / amber-200 / amber-600 / amber-800` — the read-only informational banner
  - `red-500` — destructive actions ("Удалить"), microphone-recording pulse dot
- **No gradients.** Nowhere in the codebase. The brand is flat color on flat color.
- **No dark mode.** Light-only.

### Typography

- **Font stack:** system UI. Exactly: `system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif`. No custom webfont is loaded; no `@font-face` declarations exist.
- **Weights used:** 400 (body), 500 (form labels, table headers), 600 (question headings, section titles), 700 (page headlines — via `font-bold`).
- **Size scale** (observed Tailwind classes): `text-xs` (12px), `text-sm` (14px), `text-base` (16px), `text-lg` (18px), `text-xl` (20px), `text-2xl` (24px), `text-3xl` (30px). No fluid type, no clamp().
- **Leading:** default, with `leading-relaxed` on transcription text and the voice-input textarea.
- **No letter-spacing adjustments, no italic display type.** Italic is used only for hints and client notes (`italic text-gray-500`/`400`).

### Spacing

- Tailwind's default 4px grid. Cards typically pad `p-4` to `p-6`; page wrappers use `px-6 py-6` to `py-8`.
- Vertical rhythm between form fields: `space-y-4`.
- Between cards in a list: `space-y-4`.
- Nav bars: `px-6 py-3`.

### Radii

- **Buttons:** `rounded-2xl` (16px) on the client survey, `rounded-lg` (8px) on admin. Two distinct button languages for two distinct surfaces.
- **Inputs:** `rounded-lg` everywhere.
- **Cards:** `rounded-xl` (12px) for content cards; `rounded-2xl` only on the login card.
- **Badges / pills:** `rounded-full`.
- **Record button & mic button:** `rounded-full`.
- **Progress bar track & fill:** unrounded `h-1.5` strip (full width, flush to the edge of the viewport).

### Borders

- Single-line, 1px, solid. Colors: `border-gray-100`, `border-gray-200`, `border-gray-300`. That's it.
- Focus ring pattern: `focus:outline-none focus:ring-2 focus:ring-primary` (sometimes with `focus:border-transparent`).
- No double-borders, no inset rings, no colored left-border accents.

### Shadows

- Extremely restrained. `shadow-sm` on the login card. `shadow-lg` on the export dropdown menu. `shadow` (default) on the floating mic button. **That is the entire shadow vocabulary.**
- No inner shadows. No elevation system beyond those three steps.

### Backgrounds / imagery

- **No imagery.** No photos, no illustrations, no hand-drawn marks, no repeating patterns, no textures, no background images. The product is 100% flat UI on white or `gray-50`.
- The only "visual" is the logo square on the welcome and login screens.

### Layout rules

- **Client app** is mobile-first, single-column, `max-w-lg mx-auto` (512px) centered with `px-6` gutters. One question per screen.
- **Admin app** is desktop-first, `max-w-6xl` / `max-w-3xl` / `max-w-lg` depending on the route. Top navbar is sticky-looking but not actually sticky (`bg-white border-b`).
- Content is never full-bleed. Everything lives inside a max-width wrapper.
- Fixed elements: none. No floating FABs, no sticky action bars.

### Motion

- Everything uses Tailwind's default `transition-all duration-150` on buttons and hover states — a single cohesive 150ms ease.
- The progress bar uses `duration-300` for the width animation.
- **Animations used:**
  - `animate-spin` for loading spinners (a 4px ring in `primary` color with a transparent top).
  - `animate-pulse` for three distinct states: the red microphone dot during recording, the red dot indicator while recognition is active, and the "Отправляем анкету..." submit copy.
- **No entrance animations, no staggered reveals, no scroll-triggered effects, no bounces, no springs.**
- Press state: `active:scale-95` on every button — a small shrink, no color change on press.
- Hover states: on primary buttons, darken one step (`hover:bg-primary-700`). On secondary buttons and table rows, lighten the background (`hover:bg-gray-50`, `hover:bg-primary-50`). On text-only links, change color (`hover:text-primary`, `hover:text-red-500`). Opacity is **not** used as a hover treatment.

### Transparency & blur

- None. No frosted glass, no `backdrop-blur`, no semi-transparent overlays. The single exception: `hover:bg-primary/90` on the mic button — a 10% transparency darken on hover.
- No modal overlays in the current code; delete-confirmation is inline, not a dim sheet.

### Card anatomy

A card in this system is: white background, `rounded-xl`, `border border-gray-200`, optional `shadow-sm`, padded `p-4` to `p-6`. Inside: heading (`font-semibold text-gray-800` or `-900`), optional subtitle (`text-sm text-gray-500`), body content. Never more than one level of card nesting.

### Accent treatments

- **Primary text** is reserved for: the `Анкеты` brand wordmark in the nav, page H1s on the login screen and survey welcome, and inline links ("Перейти к анкете", "Перетранскрибировать").
- **Destructive treatment** is red-500 text + red-300 border on the outline button; becomes solid `bg-red-500 text-white` on the confirm button.
- **Success state** is a soft `bg-green-50 text-green-700 rounded-lg` panel or a `badge-completed` chip.
- **Informational / warning panel** is `bg-amber-50 border border-amber-200 rounded-xl` with amber-800/600 text — used on the read-only survey notice.

---

## Iconography

### Approach

The codebase **has no icon system.** There is no icon font, no SVG sprite, no icon component, no Lucide/Heroicons/Feather/Tabler import. When a glyph is needed, the team reaches for three things, in order:

1. **A unicode character or emoji** used as a single glyph inside a button (🎤 on the voice-input control, ▾ on the export dropdown, ← → for navigation, ✓/✅ for confirmations, `+` for create actions).
2. **Plain text** labels — "Экспорт", "Удалить", "Перетранскрибировать" — instead of icons whenever the control is large enough to hold a word.
3. **A hand-rolled SVG** only for the logo.

There are no iconified nav rails, no button-with-icon combos, no illustrative icons on empty states.

### Where to find assets

- `assets/logo.svg` — the brand mark as shipped in both frontend apps (copied verbatim).
- `assets/logo-placeholder.svg` — duplicate placeholder from the codebase (the team has not yet commissioned a real logo; both filenames point at the same square with "LOGO" centered).
- `assets/favicon.svg` — a 32×32 derivative of the logo for tab icons.

### Recommendation when extending

If you add UI that genuinely needs icons (toolbar controls, empty-state illustrations, status markers beyond the current four chips), use **Lucide** at 1.5px stroke weight via CDN — closest match to the plain, administrative tone of the existing product. Document every addition here. Do **not** mix icon libraries.

**CDN fallback currently in use:** none. Substitution flagged: Lucide is a recommendation, not shipped.

### Emoji policy

Emoji usage in the current product is intentional and minimal: they act as inline glyphs (🎤 on a record button), not as standalone icons or decorative flourishes. Preserve this restraint. Don't sprinkle emoji into new designs.

---

## Caveats

- **Logo is a placeholder.** The `logo.svg` in both frontends is a navy square reading "LOGO" in Arial. There is no real brand mark yet.
- **No webfont.** The product runs on the system font stack. If brand guidelines later specify a typeface (e.g. Inter, Manrope, or a Cyrillic-friendly serif), swap `--font-sans` in `colors_and_type.css` and ship the font file under `fonts/`.
- **No dark theme.** Adding one would require revisiting the entire gray ramp and the amber/green/red chips for contrast.
- **No icon set.** Any mock that needs non-trivial iconography will have to pull in Lucide (or similar) and document the decision.
