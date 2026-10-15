import { COLOR_LABEL, type RoomView, type Send } from "../api";

const LABEL: Record<string, string> = {
  sly_deal: "Sly Deal", forced_deal: "Forced Deal", deal_breaker: "Deal Breaker",
  debt_collector: "Debt Collector", birthday: "Birthday", rent: "Rent",
};

export function ResponsePanel({ room, send, onError }: { room: RoomView; send: Send; onError: (m: string) => void }) {
  const { pending } = room;
  if (pending === null) return null;
  const name = (id: string) => room.players.find((p) => p.id === id)?.name ?? "Someone";
  const title = `${name(pending.initiatorId)} played ${LABEL[pending.kind] ?? pending.kind}`;
  const me = room.players.find((p) => p.id === room.you);
  const jsn = (me?.hand ?? []).find((id) => room.cards[id]?.action === "just_say_no");
  const mineToAct = pending.awaitingId === room.you;

  if (pending.stage === "payment") {
    if (mineToAct) return null; // PaymentPanel handles it
    return <section className="panel" role="status"><h2>{title}</h2><p>Waiting for {name(pending.awaitingId)} to pay{pending.payment ? ` ${pending.payment.amount}M` : ""}.</p></section>;
  }

  async function respond(payload: Record<string, unknown>) {
    const error = await send("game:respond", payload);
    if (error !== null) onError(error);
  }
  const color = typeof pending.params.color === "string" ? ` (${COLOR_LABEL(pending.params.color)})` : "";
  return (
    <section className="panel response" aria-label="Response">
      <h2>{title}{color}</h2>
      <p>{pending.cancelled ? "Currently cancelled by Just Say No." : "The effect will apply unless cancelled."}</p>
      {mineToAct ? (
        <div className="row">
          <button type="button" onClick={() => respond({ response: "accept" })}>Accept</button>
          <button type="button" disabled={jsn === undefined} onClick={() => jsn !== undefined && respond({ response: "just_say_no", cardId: jsn })}>Just Say No</button>
        </div>
      ) : <p>Waiting for {name(pending.awaitingId)} to respond.</p>}
    </section>
  );
}
