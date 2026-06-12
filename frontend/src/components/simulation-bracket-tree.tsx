import React, { useEffect, useRef, useState } from "react";

export interface SimulationMatch {
  match_number: number;
  home_team: string | null;
  away_team: string | null;
  home_flag?: string | null;
  away_flag?: string | null;
  home_score?: number | null;
  away_score?: number | null;
  kickoff_at?: string | null;
  phase: string;
  winner?: string | null;
  is_finished?: boolean;
}

interface Props {
  matches: SimulationMatch[];
  onMatchClick?: (matchNum: number, phase: string) => void;
}

const BOX_W = 220;
const BOX_H = 82;
const COL_GAP = 96;
const UNIT = 96;
const COL_W = BOX_W + COL_GAP;
const TREE_W = BOX_W * 5 + COL_GAP * 4;
const TREE_H = UNIT * 16;

const PHASES = ["R32", "R16", "QF", "SF", "Final"];
const PHASE_LABELS: Record<string, string> = {
  R32: "Dieciseisavos",
  R16: "Octavos",
  QF: "Cuartos",
  SF: "Semifinales",
  Final: "Final",
};

function cX(k: number) {
  return k * COL_W;
}

function cY(idx: number, k: number) {
  return (idx + 0.5) * UNIT * 2 ** k - BOX_H / 2;
}

function formatKickoff(value?: string | null) {
  if (!value) return "";
  const safeValue = String(value);
  const datePart = safeValue.split("T")[0];
  const timePart = safeValue.includes("T") ? safeValue.split("T")[1]?.slice(0, 5) : "";
  const parsed = new Date(`${datePart}T12:00:00`);
  if (Number.isNaN(parsed.getTime())) return timePart ? `${datePart} ${timePart}` : datePart;
  const dateLabel = new Intl.DateTimeFormat("es-GT", {
    day: "2-digit",
    month: "short",
  }).format(parsed);
  return timePart ? `${dateLabel} ${timePart}` : dateLabel;
}

function TeamFlag({ src, name }: { src?: string | null; name?: string | null }) {
  if (!src) {
    return (
      <span className="bracket-flag fallback" aria-hidden="true">
        {name?.slice(0, 2).toUpperCase() || "?"}
      </span>
    );
  }

  return <img className="bracket-flag" src={src} alt="" loading="lazy" />;
}

function TeamRow({
  team,
  flag,
  score,
  winner,
}: {
  team: string | null;
  flag?: string | null;
  score?: number | null;
  winner?: string | null;
}) {
  const isWinner = Boolean(team && winner && team === winner);

  return (
    <div className={isWinner ? "bracket-team winner" : "bracket-team"}>
      <div>
        <TeamFlag src={flag} name={team} />
        <strong>{team || "Por definir"}</strong>
      </div>
      {score !== null && score !== undefined && <span>{score}</span>}
    </div>
  );
}

function MatchBox({
  match,
  tone,
  onMatchClick,
}: {
  match: SimulationMatch;
  tone?: "gold" | "bronze";
  onMatchClick?: (matchNum: number, phase: string) => void;
}) {
  const clickable = Boolean(onMatchClick);

  return (
    <button
      className={`simulation-bracket-box ${tone || ""}`}
      type="button"
      disabled={!clickable}
      onClick={() => onMatchClick?.(match.match_number, match.phase)}
    >
      <div className="simulation-bracket-meta">
        <span>{match.phase === "Final" ? "Final" : `M${match.match_number}`}</span>
        <span>{formatKickoff(match.kickoff_at) || PHASE_LABELS[match.phase] || match.phase}</span>
      </div>

      <TeamRow
        team={match.home_team}
        flag={match.home_flag}
        score={match.home_score}
        winner={match.winner}
      />
      <TeamRow
        team={match.away_team}
        flag={match.away_flag}
        score={match.away_score}
        winner={match.winner}
      />
    </button>
  );
}

export default function SimulationBracketTree({ matches, onMatchClick }: Props) {
  const scrollRef = useRef<HTMLDivElement | null>(null);
  const [scrollPercent, setScrollPercent] = useState(0);
  const [maxScroll, setMaxScroll] = useState(0);
  const byPhase = new Map<string, SimulationMatch[]>();
  PHASES.forEach((phase) => byPhase.set(phase, []));

  let thirdPlace: SimulationMatch | undefined;
  matches.forEach((match) => {
    if (match.phase === "ThirdPlace") {
      thirdPlace = match;
      return;
    }
    if (!byPhase.has(match.phase)) byPhase.set(match.phase, []);
    byPhase.get(match.phase)?.push(match);
  });

  PHASES.forEach((phase) => {
    byPhase.get(phase)?.sort((a, b) => a.match_number - b.match_number);
  });

  const connectors = PHASES.slice(0, -1).flatMap((phase, k) => {
    const current = byPhase.get(phase) || [];
    const next = byPhase.get(PHASES[k + 1]) || [];

    return current
      .map((match, idx) => {
        if (!next[Math.floor(idx / 2)]) return null;
        const sx = cX(k) + BOX_W;
        const sy = cY(idx, k) + BOX_H / 2;
        const ex = cX(k + 1);
        const ey = cY(Math.floor(idx / 2), k + 1) + BOX_H / 2;
        const mx = sx + (ex - sx) / 2;

        return {
          id: `${match.match_number}-${PHASES[k + 1]}-${Math.floor(idx / 2)}`,
          d: `M ${sx} ${sy} H ${mx} V ${ey} H ${ex}`,
        };
      })
      .filter(Boolean);
  });

  function syncScrollState() {
    const element = scrollRef.current;
    if (!element) return;
    const nextMax = Math.max(0, element.scrollWidth - element.clientWidth);
    setMaxScroll(nextMax);
    setScrollPercent(nextMax ? Math.round((element.scrollLeft / nextMax) * 100) : 0);
  }

  function handleSliderChange(event: React.ChangeEvent<HTMLInputElement>) {
    const value = Number(event.target.value);
    setScrollPercent(value);
    const element = scrollRef.current;
    if (!element) return;
    const nextMax = Math.max(0, element.scrollWidth - element.clientWidth);
    element.scrollLeft = (nextMax * value) / 100;
  }

  useEffect(() => {
    syncScrollState();
    window.addEventListener("resize", syncScrollState);
    return () => window.removeEventListener("resize", syncScrollState);
  }, [matches.length]);

  return (
    <div className="simulation-bracket-shell">
      <div className="bracket-slider-row">
        <span>R32</span>
        <input
          aria-label="Desplazar bracket"
          disabled={maxScroll <= 0}
          max="100"
          min="0"
          onChange={handleSliderChange}
          type="range"
          value={scrollPercent}
        />
        <span>Final</span>
      </div>

      <div className="simulation-bracket-scroll" ref={scrollRef} onScroll={syncScrollState}>
        <div className="simulation-bracket-tree" style={{ width: TREE_W, height: TREE_H }}>
          <svg
            className="simulation-bracket-connectors"
            width={TREE_W}
            height={TREE_H}
            viewBox={`0 0 ${TREE_W} ${TREE_H}`}
            aria-hidden="true"
          >
            {connectors.map((connector) => (
              <path key={connector!.id} d={connector!.d} />
            ))}
          </svg>

          {PHASES.map((phase, k) => (
            <React.Fragment key={phase}>
              <div className="simulation-bracket-phase-label" style={{ left: cX(k), top: 0 }}>
                {PHASE_LABELS[phase]}
              </div>
              {(byPhase.get(phase) || []).map((match, idx) => (
                <div
                  className="simulation-bracket-node"
                  key={`${phase}-${match.match_number}`}
                  style={{ left: cX(k), top: cY(idx, k) + 30 }}
                >
                  <MatchBox
                    match={match}
                    tone={phase === "Final" ? "gold" : undefined}
                    onMatchClick={onMatchClick}
                  />
                </div>
              ))}
            </React.Fragment>
          ))}
        </div>

        {thirdPlace && (
          <div className="third-place-row" style={{ width: TREE_W }}>
            <div className="third-place-spacer" style={{ width: cX(4) }} />
            <div className="third-place-card">
              <p>Partido por 3er lugar</p>
              <MatchBox match={thirdPlace} tone="bronze" onMatchClick={onMatchClick} />
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
