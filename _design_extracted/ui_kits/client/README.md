# Client UI kit

Recreation of the public client-facing survey flow from `anketa/frontend-client/src/pages/Survey.tsx`.

## Screens

- **welcome** — logo, "Добро пожаловать, {Имя}!", question count, "Начать" CTA
- **answering** — one question per screen, textarea + mic button, progress bar at top
- **review** — list of Q/A, click to edit, "Отправить анкету" CTA
- **submitting** — pulsing "Отправляем анкету..."
- **done** — ✅ "Спасибо!" + callback promise
- **readonly** — amber banner + read-only answers when survey is already completed

## Components

| File | Exports |
|---|---|
| `WelcomeScreen.jsx` | `<WelcomeScreen>` |
| `ProgressBar.jsx` | `<ProgressBar>` |
| `QuestionScreen.jsx` | `<QuestionScreen>` (with fake mic animation) |
| `ReviewScreen.jsx` | `<ReviewScreen>` |
| `StatusScreens.jsx` | `<ThankYouScreen> <SubmittingScreen> <ReadonlyScreen>` |

## Notes

- Mic button fakes recognition by delaying and inserting a stock Russian sentence — enough for a visual prototype.
- Phone frame is purely cosmetic; real app is responsive mobile-first, `max-w-lg` centered.
- All copy is Russian. All buttons are `rounded-2xl`.
