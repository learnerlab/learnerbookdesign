import type { SectionKey } from "@/lib/instrument";

// The Learner Shape (§7.3, §14): a textbook-figure radar — thin ink axes, a
// small tick scale, one filled triangle, one handwritten annotation.

const CX = 190;
const CY = 185;
const R = 118;

// growth top, stress bottom-right, actions bottom-left.
const AXES: { key: SectionKey; angle: number }[] = [
  { key: "growth", angle: -90 },
  { key: "stress", angle: 30 },
  { key: "actions", angle: 150 },
];

function point(angleDeg: number, r: number): [number, number] {
  const rad = (angleDeg * Math.PI) / 180;
  return [CX + r * Math.cos(rad), CY + r * Math.sin(rad)];
}

function polygonPoints(fraction: number): string {
  return AXES.map(({ angle }) => point(angle, R * fraction).join(",")).join(" ");
}

const LABEL_PLACEMENT: Record<
  SectionKey,
  { dx: number; dy: number; anchor: "start" | "middle" | "end" }
> = {
  growth: { dx: 0, dy: -14, anchor: "middle" },
  stress: { dx: 10, dy: 18, anchor: "middle" },
  actions: { dx: -10, dy: 18, anchor: "middle" },
};

// Kept clear of the axis labels: upper-right for growth/stress, upper-left
// for actions, with the dashed arrow reaching into the shape.
const ANNOTATION_PLACEMENT: Record<
  SectionKey,
  { x: number; y: number; anchor: "start" | "end" }
> = {
  growth: { x: 374, y: 124, anchor: "end" },
  stress: { x: 374, y: 92, anchor: "end" },
  actions: { x: 6, y: 92, anchor: "start" },
};

export function LearnerShape({
  scores,
  labels,
  weakest,
  annotation = "your biggest opportunity",
}: {
  scores: Record<SectionKey, number>;
  labels: Record<SectionKey, string>;
  weakest: SectionKey;
  annotation?: string;
}) {
  const shapePoints = AXES.map(({ key, angle }) =>
    point(angle, (R * Math.max(0, Math.min(100, scores[key]))) / 100).join(","),
  ).join(" ");

  const weakVertex = point(
    AXES.find((a) => a.key === weakest)!.angle,
    R * 0.55,
  );
  const note = ANNOTATION_PLACEMENT[weakest];

  return (
    <figure className="shape-reveal">
      <svg
        viewBox="0 0 380 330"
        role="img"
        aria-label={`Learner Shape: ${AXES.map(
          ({ key }) => `${labels[key]} ${Math.round(scores[key])}`,
        ).join(", ")} out of 100.`}
        className="mx-auto w-full max-w-md"
      >
        {/* tick-scale grid */}
        {[0.25, 0.5, 0.75, 1].map((f) => (
          <polygon
            key={f}
            points={polygonPoints(f)}
            fill="none"
            stroke="currentColor"
            className="text-rule"
            strokeWidth={f === 1 ? 1 : 0.5}
          />
        ))}
        {/* axes */}
        {AXES.map(({ key, angle }) => {
          const [x, y] = point(angle, R);
          return (
            <line
              key={key}
              x1={CX}
              y1={CY}
              x2={x}
              y2={y}
              stroke="currentColor"
              className="text-ink-muted"
              strokeWidth={0.6}
            />
          );
        })}
        {/* tick marks on the top axis, every 25 points */}
        {[0.25, 0.5, 0.75].map((f) => {
          const [x, y] = point(-90, R * f);
          return (
            <line
              key={f}
              x1={x - 4}
              y1={y}
              x2={x + 4}
              y2={y}
              stroke="currentColor"
              className="text-ink-muted"
              strokeWidth={0.6}
            />
          );
        })}
        {/* the shape */}
        <polygon
          points={shapePoints}
          className="fill-yellow/40 stroke-ink"
          strokeWidth={1.5}
          strokeLinejoin="round"
        />
        {AXES.map(({ key, angle }) => {
          const [x, y] = point(angle, (R * scores[key]) / 100);
          return <circle key={key} cx={x} cy={y} r={2.5} className="fill-ink" />;
        })}
        {/* axis labels with scores, outside the corners */}
        {AXES.map(({ key, angle }) => {
          const [x, y] = point(angle, R);
          const placement = LABEL_PLACEMENT[key];
          return (
            <text
              key={key}
              x={x + placement.dx}
              y={y + placement.dy}
              textAnchor={placement.anchor}
              className="fill-ink font-body"
              fontSize={13}
            >
              {labels[key]}{" "}
              <tspan fontWeight={600}>{Math.round(scores[key])}</tspan>
            </text>
          );
        })}
        {/* one handwritten annotation pointing at the weakest axis */}
        <path
          d={(() => {
            const startX = note.anchor === "end" ? note.x - 60 : note.x + 60;
            const startY = note.y + 6;
            const controlX = (startX + weakVertex[0]) / 2;
            const controlY = (startY + weakVertex[1]) / 2 + 18;
            return `M ${startX} ${startY} Q ${controlX} ${controlY} ${weakVertex[0]} ${weakVertex[1]}`;
          })()}
          fill="none"
          stroke="currentColor"
          className="text-ink-muted"
          strokeWidth={0.8}
          strokeDasharray="3 3"
        />
        <text
          x={note.x}
          y={note.y}
          textAnchor={note.anchor}
          className="fill-ink font-hand"
          fontSize={18}
        >
          {annotation}
        </text>
      </svg>
      <figcaption className="mt-2 text-center text-sm italic text-ink-muted">
        Fig. 1 — Your Learner Shape: three measures, 0–100.
      </figcaption>
    </figure>
  );
}
