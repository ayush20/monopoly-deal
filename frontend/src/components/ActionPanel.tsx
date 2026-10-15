import { useState } from "react";

import { COLOR_LABEL, SET_SIZE, type Color, type PlayerView, type RoomView, type Send } from "../api";

type Props = {
  room: RoomView;
  cardId: string;
  send: Send;
  onError: (message: string) => void;
  onDone: () => void;
  canPlay: boolean;
};

type Laid = { id: string; color: Color };

function laid(player: PlayerView | undefined): Laid[] {
  return Object.entries(player?.properties ?? {}).flatMap(([color, ids]) => (ids ?? []).map((id) => ({ id, color: color as Color })));
}

function Select<T extends string>({ label, value, onChange, options }: {
  label: string; value: T | ""; onChange: (v: T) => void; options: { value: T; text: string }[];
}) {
  return (
    <label className="field">{label}
      <select value={value} onChange={(e) => onChange(e.target.value as T)}>
        <option value="">Choose…</option>
        {options.map((o) => <option key={o.value} value={o.value}>{o.text}</option>)}
      </select>
    </label>
  );
}

export function ActionPanel({ room, cardId, send, onError, onDone, canPlay }: Props) {
  const card = room.cards[cardId];
  const me = room.players.find((p) => p.id === room.you);
  const opponents = room.players.filter((p) => p.id !== room.you && p.active && !p.removed && p.bank !== undefined);
  const [color, setColor] = useState<Color | "">("");
  const [targetId, setTargetId] = useState("");
  const [propertyId, setPropertyId] = useState("");
  const [offeredId, setOfferedId] = useState("");
  const [doubleId, setDoubleId] = useState("");

  if (card === undefined) return null;
  const target = opponents.find((p) => p.id === targetId);
  const targetLaid = laid(target);
  const myLaid = laid(me);
  const doubles = (me?.hand ?? []).filter((id) => room.cards[id]?.action === "double_rent");
  const playsLeft = room.turn !== null && room.turn.playsUsed < room.turn.playsMax;
  const enabled = canPlay && playsLeft;
  const needsSecondPlay = room.turn !== null && room.turn.playsUsed + 2 <= room.turn.playsMax;

  async function run(event: string, payload: Record<string, unknown>) {
    const error = await send(event, { cardId, ...payload });
    if (error !== null) onError(error);
    else onDone();
  }

  const targetOptions = opponents.map((p) => ({ value: p.id, text: p.name }));
  const colorOptions = (colors: Color[]) => colors.map((c) => ({ value: c, text: COLOR_LABEL(c) }));
  const propOptions = (list: Laid[]) => list.map((l) => ({ value: l.id, text: `${room.cards[l.id]?.name ?? l.id} (${COLOR_LABEL(l.color)})` }));
  const colorOf = (list: Laid[], id: string) => list.find((l) => l.id === id)?.color;

  const buttons: React.ReactNode[] = [];
  const bankable = card.value !== null && card.type !== "property" && card.type !== "property_wild";
  if (bankable) buttons.push(<button key="bank" type="button" disabled={!enabled} onClick={() => run("game:bank", {})}>Bank</button>);

  if (card.type === "property" || card.type === "property_wild") {
    const choices = card.colors;
    buttons.push(
      <span key="prop" className="row">
        {choices.length > 1 && <Select label="Color" value={color} onChange={setColor} options={colorOptions(choices)} />}
        <button type="button" disabled={!enabled || (choices.length > 1 && color === "")} onClick={() => run("game:play_property", { color: choices.length === 1 ? choices[0] : color })}>Play as property</button>
      </span>,
    );
  }

  if (card.action === "house" || card.action === "hotel") {
    const completed = (Object.keys(me?.properties ?? {}) as Color[]).filter((c) => c !== "railroad" && c !== "utility" && (me?.properties?.[c]?.length ?? 0) >= SET_SIZE[c]);
    buttons.push(
      <span key="imp" className="row">
        <Select label="Complete set" value={color} onChange={setColor} options={colorOptions(completed)} />
        <button type="button" disabled={!enabled || color === ""} onClick={() => run("game:improve", { color })}>Improve set</button>
      </span>,
    );
  }

  if (card.action === "pass_go") buttons.push(<button key="go" type="button" disabled={!enabled} onClick={() => run("game:pass_go", {})}>Pass Go</button>);

  const targetPicker = <Select key="t" label="Target player" value={targetId} onChange={(v) => { setTargetId(v); setPropertyId(""); setColor(""); }} options={targetOptions} />;

  if (card.action === "sly_deal") {
    buttons.push(
      <span key="sly" className="row">
        {targetPicker}
        <Select label="Property to take" value={propertyId} onChange={setPropertyId} options={propOptions(targetLaid)} />
        <button type="button" disabled={!enabled || targetId === "" || propertyId === ""} onClick={() => run("game:action", { targetId, propertyId, color: colorOf(targetLaid, propertyId) })}>Play Sly Deal</button>
      </span>,
    );
  }
  if (card.action === "forced_deal") {
    buttons.push(
      <span key="forced" className="row">
        {targetPicker}
        <Select label="Property to take" value={propertyId} onChange={setPropertyId} options={propOptions(targetLaid)} />
        <Select label="Property to give" value={offeredId} onChange={setOfferedId} options={propOptions(myLaid)} />
        <button type="button" disabled={!enabled || targetId === "" || propertyId === "" || offeredId === ""} onClick={() => run("game:action", { targetId, requestedId: propertyId, requestedColor: colorOf(targetLaid, propertyId), offeredId, offeredColor: colorOf(myLaid, offeredId) })}>Play Forced Deal</button>
      </span>,
    );
  }
  if (card.action === "deal_breaker") {
    const sets = [...new Set(targetLaid.map((l) => l.color))].filter((c) => (target?.properties?.[c]?.length ?? 0) >= SET_SIZE[c]);
    buttons.push(
      <span key="db" className="row">
        {targetPicker}
        <Select label="Complete set" value={color} onChange={setColor} options={colorOptions(sets)} />
        <button type="button" disabled={!enabled || targetId === "" || color === ""} onClick={() => run("game:action", { targetId, color })}>Play Deal Breaker</button>
      </span>,
    );
  }
  if (card.action === "debt_collector") {
    buttons.push(
      <span key="debt" className="row">
        {targetPicker}
        <button type="button" disabled={!enabled || targetId === ""} onClick={() => run("game:action", { targetId })}>Collect 5M</button>
      </span>,
    );
  }
  if (card.action === "birthday") buttons.push(<button key="bd" type="button" disabled={!enabled} onClick={() => run("game:action", {})}>Play Birthday</button>);

  if (card.type === "rent") {
    const anyColor = card.colors.length === 10;
    const rentColors = (Object.keys(me?.properties ?? {}) as Color[]).filter((c) => card.colors.includes(c) && (me?.properties?.[c]?.length ?? 0) > 0);
    const payload: Record<string, unknown> = { color };
    if (anyColor) payload.targetId = targetId;
    if (doubleId !== "") payload.doubleRentCardId = doubleId;
    buttons.push(
      <span key="rent" className="row">
        <Select label="Rent color" value={color} onChange={setColor} options={colorOptions(rentColors)} />
        {anyColor && targetPicker}
        {doubles.length > 0 && (
          <label className="field">
            <input type="checkbox" disabled={!needsSecondPlay} checked={doubleId !== ""} onChange={(e) => setDoubleId(e.target.checked ? doubles[0] : "")} /> Double the rent (uses 2 plays)
          </label>
        )}
        <button type="button" disabled={!enabled || color === "" || (anyColor && targetId === "")} onClick={() => run("game:action", payload)}>Play rent</button>
      </span>,
    );
  }

  return (
    <div className="actions" role="group" aria-label={`Actions for ${card.name}`}>
      <h3>{card.name}</h3>
      {!canPlay && <p className="muted">You can play cards once it is your turn and you have drawn.</p>}
      {buttons.length === 0 && <p className="muted">This card has no direct play. It can only be used as a response.</p>}
      {buttons}
    </div>
  );
}
