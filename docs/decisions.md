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

## Unresolved questions

None currently blocking Phase 1. During the rules-engine phase, any ambiguity found in the official guide—particularly timing and response windows—will be added here with its source and implementation decision.

## Change log

| Date | Change |
| --- | --- |
| 2026-10-13 | Recorded initial approved architecture and interview decisions. |
