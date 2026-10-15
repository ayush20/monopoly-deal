# Socket.IO protocol

Server: Flask-SocketIO. Every client->server event below is emitted with one JSON object
payload and an ack callback. **Every ack is either `{ "ok": true, ...extra }` or
`{ "error": "message" }`.** After any successful command the server pushes a private
`room:state` to every connected member (each gets their own projection).

Ids: player (member) ids and card ids are opaque strings. Colors:
`brown light_blue pink orange red yellow green dark_blue railroad utility`.

## Client -> server events

### Lobby / session
| Event | Payload | Ack on success |
| --- | --- | --- |
| `room:create` | `{name}` | `{ok, token, state}` (`state` = `room:state` view) |
| `room:join` | `{code, name}` | `{ok, token, state}` |
| `room:reconnect` | `{code, token}` | `{ok, token, state}` (use after refresh; store `token` per room code in localStorage) |
| `room:ready` | `{ready: boolean}` (default `true`) | `{ok}` (lobby only) |
| `room:start` | `{}` host only; needs 2-5 ready players | `{ok}` |

### Host controls (host only)
`room:pause {}`, `room:resume {}`, `room:end {}`, `room:remove {targetId}` -> `{ok}`.
A disconnect of an active player auto-pauses the room (`status: "paused"`); the host
resumes with `room:resume`. Reconnect reservation is 600 s (`players[].reservationSeconds`).
Removing a player down to one remaining ends the game with that player as winner.

### Game commands (status must be `in_progress`, caller must be the active player unless noted)
| Event | Payload | Notes |
| --- | --- | --- |
| `game:start_turn` | `{}` | Draws 2 (5 if hand empty). Required before any play. Phase `awaiting_turn_start` -> `active`. |
| `game:bank` | `{cardId}` | Money, rent, or action card to bank. Uses 1 play. |
| `game:play_property` | `{cardId, color}` | Property or wild into a set. Uses 1 play. |
| `game:move_wild` | `{cardId, color}` | Move an already-laid wild. Free. |
| `game:improve` | `{cardId, color}` | House/Hotel on a complete set. Uses 1 play. |
| `game:pass_go` | `{cardId}` | Draw 2. Uses 1 play. |
| `game:action` | `{cardId, ...params}` | See table below. Creates a pending action. |
| `game:respond` | `{response: "accept"}` or `{response: "just_say_no", cardId}` | Only the player in `pending.awaitingId`, stage `response`. Allowed even though it is not your turn. |
| `game:pay` | `{cardIds: string[]}` | Only `pending.awaitingId`, stage `payment`. Cards must be laid (bank/properties/improvements) with value; engine enforces strict-payment rules. |
| `game:discard` | `{cardIds: string[]}` | Only when hand > 7; discard down to exactly 7 (no lower). |
| `game:end_turn` | `{}` | Rejected if hand > 7 (`"Discard N card(s)..."`) or a pending action exists. |

`game:action` params by card (the server decides what the card is from `cardId`):

| Card | Params |
| --- | --- |
| `sly_deal` | `targetId, propertyId, color` (color = set the property sits in) |
| `forced_deal` | `targetId, offeredId, offeredColor, requestedId, requestedColor` |
| `deal_breaker` | `targetId, color` |
| `debt_collector` | `targetId` (5M) |
| `birthday` | none (2M from every other player) |
| rent card (`type: "rent"`) | `color` (must be on the card); `targetId` required only for the any-color rent card; two-color rent hits all opponents; optional `doubleRentCardId` (a `double_rent` card in hand; costs a 2nd play and doubles the rent) |

`just_say_no`, `house`, `hotel`, `double_rent` alone, `pass_go` etc. are rejected by
`game:action`. While `pending` exists (for anyone) all other game commands, including
`end_turn`, are rejected.

### Pending flow (no timers)
1. Active player sends `game:action`. Cards are discarded and plays spent immediately.
2. For each affected player in turn (`targets` order), `awaitingId` = that player. They
   send `game:respond accept` or `just_say_no` (their own JSN card). After a JSN,
   `awaitingId` flips to the other party (initiator), who may counter with JSN or `accept`
   (concede); this alternates. `cancelled` shows whether the effect is currently cancelled.
   When someone accepts, the effect is decided: steal/swap/deal-breaker is applied if not
   cancelled; payment kinds mark that target as liable.
3. Liable players pay in order (`stage: "payment"`, `awaitingId` = current payer, details in
   `payment`). Players with nothing laid down are auto-settled and skipped.
4. `pending` becomes `null`. A winner (3 complete sets) ends the room (`status: "ended"`).

## Server -> client events

Only one: **`room:state`** - the viewer's private projection (also returned in
create/join/reconnect acks as `state`). Emitted after create, join, reconnect, ready, start,
every game command, host control, and disconnect.

```jsonc
{
  "code": "A1B2C3",
  "status": "lobby" | "in_progress" | "paused" | "ended",
  "you": "<your player id>",
  "players": [            // in join order; game order = turn order among active players
    {
      "id": "...", "name": "Ada", "host": true, "ready": false, "active": false,
      "connected": true, "removed": false,
      "reservationSeconds": null,      // int seconds left to reconnect when disconnected
      // present only once a game has started and the player is in it:
      "bank": ["card ids"],
      "properties": { "brown": ["card ids"], ... },     // only colors ever played
      "improvements": { "green": ["house id", "hotel id"] },  // only non-empty
      "handCount": 5,
      "completedSets": 0,
      "hand": ["card ids"]             // ONLY on the viewer's own entry
    }
  ],
  "turn": null | { "playerId": "...", "phase": "awaiting_turn_start" | "active" | "complete",
                   "playsUsed": 0, "playsMax": 3 },
  "drawCount": null | 96,
  "discardTop": null | "card id",
  "discardCount": null | 0,
  "winner": null | "player id",
  "pending": null | {                  // non-null only for the initiator and affected players
    "kind": "sly_deal" | "forced_deal" | "deal_breaker" | "debt_collector" | "birthday" | "rent",
    "stage": "response" | "payment",
    "initiatorId": "...",
    "cardIds": ["cards played (action card, plus double rent)"],
    "targets": ["affected player ids"],
    "params": { "targetId": "...", "propertyId": "...", "color": "brown", ... },  // as validated, same keys as game:action
    "awaitingId": "player who must act now",
    "currentTargetId": "target being asked (response stage) or null",
    "cancelled": false,                // response stage: effect currently cancelled by JSN
    "payment": null | {                // payment stage
      "payerId": "...", "recipientId": "...", "amount": 5, "reason": "rent|birthday|debt_collector",
      "queue": [ { "payerId": "...", "amount": 2 } ]   // all remaining incl. current
    }
  },
  "cards": {                           // catalog for every card in this game ({} in lobby)
    "property-brown-1": { "id": "property-brown-1", "name": "Brown Property", "type": "property",
                          "value": 1, "colors": ["brown"], "action": null },
    "action-sly_deal-1": { "id": "...", "name": "Sly Deal", "type": "action", "value": 3,
                           "colors": [], "action": "sly_deal" }
  }
}
```

Card `type`: `money | property | property_wild | rent | action`. `value` is the bank value
(`null` for the two any-color wilds, which cannot be banked/paid). `colors` is the allowed
colors (sorted; all 10 for any-color wild/rent). `action` is one of `deal_breaker forced_deal
sly_deal just_say_no debt_collector birthday double_rent house hotel pass_go`, else `null`.
Hand cards, banks, and properties are all ids: look them up in `cards`.

Client hints: you can respond with JSN only if your hand contains an id whose catalog
`action === "just_say_no"`. Win condition: `winner` non-null and `status === "ended"`.
The deck reshuffles from the discard pile automatically when the draw pile runs out.
