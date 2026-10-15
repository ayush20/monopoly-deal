import type { Card } from "../api";

type Props = {
  card: Card | undefined;
  id: string;
  selected?: boolean;
  onClick?: () => void;
  disabled?: boolean;
};

export function CardChip({ card, id, selected = false, onClick, disabled }: Props) {
  const color = card?.colors.length === 1 ? card.colors[0] : card?.colors.length ? "multi" : "none";
  const label = card?.name ?? id;
  const className = `card${selected ? " selected" : ""}`;
  const body = (
    <>
      <small>{card?.type.replace("_", " ") ?? "card"}</small>
      <strong>{label}</strong>
      {card?.value != null && <span>{card.value}M</span>}
    </>
  );
  if (onClick === undefined) return <div className={className} data-color={color}>{body}</div>;
  return (
    <button type="button" className={className} data-color={color} aria-pressed={selected} disabled={disabled} onClick={onClick}>
      {body}
    </button>
  );
}
