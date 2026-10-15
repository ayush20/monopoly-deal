# Product decisions

## Confirmed product decisions

| Area | Decision |
| --- | --- |
| Players | 2–5 players per room. |
| Access | Browser game; private room code; no accounts or installation. |
| Identity | Player supplies a display name. The browser stores an opaque reconnect token for that room. |
| Host | The room creator remains host. Only the host starts, pauses, resumes, ends, and removes players. |
| Lobby | The host may start when at least two players are marked ready. Late joiners wait for the next round, up to five room seats. |
| Disconnect | Pause immediately. Reserve the disconnected player's seat for 10 minutes. |
| Removal | Host may remove an active player at any time; their hand, bank, and properties are discarded. One remaining active player wins. |
| Payment | Enforce classic payment: pay only from banked money and laid properties; overpayment is allowed; no change. |
| Interaction | Tap/select a card, then choose from valid actions and targets. |
| Browser support | Current Chrome, iPhone Safari, and Android Chrome. |
| Hosting | Flask + Socket.IO on AWS EC2; Cloudflare for domain, DNS, TLS/proxy, and static frontend. |
| Delivery | Git repository, organized branches, PR workflow, README, and test report. Demo video after first launch. |

## Rules source policy

The planned baseline is the official Monopoly Deal 2–5-player 110-card edition and its game guide. The official source identifies the goal as collecting three full property sets in different colours.

- Documented rules will be represented as test cases and cited here as they are implemented.
- Where official instructions are ambiguous, the ambiguity and chosen implementation will be recorded before implementation.
- Online-only controls (reconnection, pause, removal, room lifecycle) are product adaptations, not original game rules.
- The interface will use original artwork and must not reproduce proprietary logos, card art, or other protected visual assets.

## Rules-engine source record

Phase 2 uses the 110-card G0351-style package as its source. Four cards are rules/reference cards, leaving a 106-card playable deck: 28 standard properties, 11 property wilds, 13 rent cards, 34 action cards, and 20 money cards. The engine asserts this composition before any game is created.

Documented setup and turn rules now encoded in tests:

- Deal five cards to each active player.
- Start a turn by drawing two cards, or five cards when the player starts with no hand.
- A player may play at most three cards on their turn.
- A win requires three complete sets in different colours.
- Wild properties may be moved between compatible sets only during their owner's turn and do not consume a card play.
- A House requires a complete set; a Hotel requires that set's House.

Strict payment behavior encoded in tests:

- A debt may be paid only with cards already laid in a bank or property area; hand cards are excluded.
- A payer may overpay but receives no change.
- If the payer cannot cover the debt, every available non-zero-value laid card must be paid.
- The two multicolour property wild cards have no cash value and cannot settle a debt.

Wiring rules added with gameplay sockets:

- Hand limit: a player ending their turn with more than 7 cards must first `discard_to_limit` down to exactly 7.
- Draw pile reshuffle: when the draw pile is empty, the discard pile is shuffled back in; if both are empty, drawing stops quietly.
- Just Say No timing: explicit responses with no timer. Each affected player accepts or plays Just Say No, the initiator may counter, and so on. Birthday/rent targets are asked one at a time, then debts are paid in order; players with nothing laid down are skipped. See `docs/protocol.md`.
- Rent: two-colour rent cards charge all opponents; the any-colour rent card charges one chosen opponent. Double Rent is played with a rent card and costs a second play.

## Unresolved questions

None currently blocking Phase 1. During the rules-engine phase, any ambiguity found in the official guide—particularly timing and response windows—will be added here with its source and implementation decision.

## Change log

| Date | Change |
| --- | --- |
| 2026-10-13 | Recorded initial approved architecture and interview decisions. |
