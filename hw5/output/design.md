# Dashboard design: The Handsome Dan Desk

The board lives in `frontend/` (React, Vite, TypeScript). It calls the back end at `http://localhost:8000` and starts with `npm run dev`. This note says what I chose and why.

## The look: Yale, and nothing else

- **Colors.** Yale blue `#00356b` is the ground for everything that matters: the balance card, the field, the resolved stamp. The page behind it is a cool pale blue-grey so white cards read as paper. Light blue (`#63aaff`) is only for focus rings and small highlights.
- **One warm accent.** Tennis-ball yellow-green (`#dff23d`) is the only warm color in the interface, and it is used only for the thing being thrown: the ball, the "Throw it" button, and the "Dan is on it" chip. Because nothing else is yellow, your eye follows the work.
- **Type.** Libre Baskerville for headings, the balance and the boss's words, because it has the bookish weight of a Yale serif. Source Sans 3 for everything you read quickly. IBM Plex Mono for tool names and ticket asks, because those are machine words.
- **No Yale logo.** I used the colors, a serif and a plain "Y" on the bandana. The bulldogs are my own cartoons (adapted from the course starter's mascot), not an official mark.

## The cast: each agent reads differently

Handsome Dan is the boss. Each specialist is its own bulldog so you can tell the agents apart without reading a label.

| Agent | Bandana | Prop | Why that |
|---|---|---|---|
| Handsome Dan (boss) | Yale blue | none, he carries the ball | He is the only one who sees the whole ticket. |
| Inventory Dan | green | clipboard | Counting things. |
| Accounting Dan | gold | abacus | Money, with a color that says "careful". |
| Facilities Dan | orange | key | The shop's door and lease. |
| Service Dan | teal | headset | Talks to customers. |

The same color follows each agent everywhere: the bandana, the name tag, the left edge of its summary card and of its lines in the play-by-play. The words differ too. The boss speaks in italic serif, like a headmaster. The pups speak in small monospace bubbles, like a log, and show the tool they just used. When a pup is not needed on a ticket, its card stays on screen, dimmed and dashed, so "Facilities was not called" is a visible decision and not a missing box.

## A ticket going out: the tennis ball

1. You pick a ticket and press **Throw it to Handsome Dan**. The ticket leaves the desk as a tennis ball with its number on it. Handsome Dan sprints out, grabs it, and trots home.
2. When the boss sends a task to a specialist, he throws the ball to that pup's spot on the field. The pup gallops to it and starts working, with a bubble showing what it is doing.
3. When the specialist reports back, the ball flies back to the boss, who catches it with a yellow flash, and the pup gets a green check.

There is more than one dog because there is more than one agent. Two pups can be out fetching at the same time, which is what happens when the boss sends independent tasks together. The motion comes from the real events of the run (the back end's `/api/live` feed), not from a timer, so what you see is what is actually happening. Pups that finished keep their check marks, and if you reload the page mid-run the field replays to where the run is.

## Resolved tickets

A resolved ticket changes in several places at once, so it cannot be missed. The card turns pale Yale blue with a thick blue edge, the chip turns solid blue with a check, and a **RESOLVED** stamp drops onto the card. The boss says "Ticket #N is closed. Good dog." Until then, a ticket is yellow-green while Dan works, amber when it is waiting for you, and plain blue-outlined when it is open. Amber was chosen because it means "your turn" without looking like an error.

A ticket never resolves on its own. The agents prepare, and the **Needs your approval** card, which looks like a paper form, holds everything a person decides: the payment, the drafted reply (shown in full and marked "not sent"), and a close button that stays disabled until the money is dealt with.

## Cash flow

- The balance sits on a Yale-blue card in large serif numerals, with a "Checking, as of" date.
- When a payment is approved the number counts down to its new value, gold coins drop off the card, and a yellow "−$840.00" floats up, so the money visibly leaves.
- Under the balance, a line chart steps through the balance after each payment and **redraws itself** every time one is approved. Below it, a short ledger says who got paid and for which ticket. Both come from the real `payments` table, so a reload shows the same story.
- Before any payment, the card says "Money only moves when you approve it", which doubles as the safety rule.

## Why these choices

- A board that only prints text feels like a log file. A dog fetching a ball tells you in half a second who is working and who is done, and the ball makes delegation, the main idea of the system, something you can see.
- The fun is kept out of the way of the serious parts. Amounts, payees, the draft reply and the approver name are plain, large, and never animated.
- The agents' words stay readable. Everything that scrolls or updates has text, so a screen reader or someone who reduces motion still gets the full story: updates use `aria-live`, controls have visible focus rings, and with "reduce motion" on, the dogs, ball, coins and chart appear without travel.
- The balance never lies: it always comes from the database, never from the page's own arithmetic.
