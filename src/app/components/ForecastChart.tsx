"use client";

import React, { useMemo } from "react";

/**
 * SVG-based line chart that renders:
 *   • 30-day historical carbon intensity (blue)
 *   • 7-day TFT forecast with 80% confidence band (green + shaded)
 */

interface HistoryPoint {
  date: string;
  carbon_intensity: number;
}

interface ForecastPoint {
  date: string;
  predicted: number;
  lower_80: number;
  upper_80: number;
  lower_50?: number;
  upper_50?: number;
}

interface ForecastSummary {
  forecast_avg_gCO2: number;
  recent_avg_gCO2: number;
  trend: "increasing" | "decreasing" | "stable";
  prediction_days: number;
  unit: string;
}

export interface ForecastData {
  provider: string;
  region: string;
  history: HistoryPoint[];
  forecast: ForecastPoint[];
  summary: ForecastSummary;
  error?: string;
}

interface ForecastChartProps {
  data: ForecastData | null;
  onClose?: () => void;
}

const CHART_W = 1200;
const CHART_H = 500;
const PAD = { top: 40, right: 40, bottom: 60, left: 80 };
const INNER_W = CHART_W - PAD.left - PAD.right;
const INNER_H = CHART_H - PAD.top - PAD.bottom;

const trendIcon: Record<string, string> = {
  increasing: "↑",
  decreasing: "↓",
  stable: "→",
};
const trendColor: Record<string, string> = {
  increasing: "#ef4444",
  decreasing: "#22c55e",
  stable: "#eab308",
};

export default function ForecastChart({ data, onClose }: ForecastChartProps) {
  if (!data || data.error) return null;

  const { history, forecast, summary } = data;

  /* ── Build unified value arrays ────────────────────────────────────── */
  const allDates = useMemo(
    () => [
      ...history.map((h) => h.date),
      ...forecast.map((f) => f.date),
    ],
    [history, forecast]
  );

  const allValues = useMemo(() => {
    const hv = history.map((h) => h.carbon_intensity);
    const fv = forecast.flatMap((f) => [f.predicted, f.lower_80, f.upper_80]);
    return [...hv, ...fv];
  }, [history, forecast]);

  const yMin = Math.floor(Math.min(...allValues) * 0.92);
  const yMax = Math.ceil(Math.max(...allValues) * 1.08);
  const yRange = yMax - yMin || 1;

  /* helpers */
  const x = (idx: number) =>
    PAD.left + (idx / (allDates.length - 1)) * INNER_W;
  const y = (val: number) =>
    PAD.top + INNER_H - ((val - yMin) / yRange) * INNER_H;

  const histLen = history.length;

  /* ── SVG paths ─────────────────────────────────────────────────────── */
  const historyPath = history
    .map((h, i) => `${i === 0 ? "M" : "L"}${x(i).toFixed(1)},${y(h.carbon_intensity).toFixed(1)}`)
    .join(" ");

  const forecastPath = forecast
    .map(
      (f, i) =>
        `${i === 0 ? "M" : "L"}${x(histLen + i).toFixed(1)},${y(f.predicted).toFixed(1)}`
    )
    .join(" ");

  // Connector between history end and forecast start
  const connectorPath =
    history.length > 0 && forecast.length > 0
      ? `M${x(histLen - 1).toFixed(1)},${y(history[histLen - 1].carbon_intensity).toFixed(1)} L${x(histLen).toFixed(1)},${y(forecast[0].predicted).toFixed(1)}`
      : "";

  // 80 % confidence band (filled area)
  const bandUpper = forecast
    .map(
      (f, i) =>
        `${i === 0 ? "M" : "L"}${x(histLen + i).toFixed(1)},${y(f.upper_80).toFixed(1)}`
    )
    .join(" ");
  const bandLower = [...forecast]
    .reverse()
    .map(
      (f, i) =>
        `L${x(histLen + forecast.length - 1 - i).toFixed(1)},${y(f.lower_80).toFixed(1)}`
    )
    .join(" ");
  const bandPath = `${bandUpper} ${bandLower} Z`;

  /* ── y-axis ticks (4 ticks) ────────────────────────────────────────── */
  const yTicks = Array.from({ length: 5 }, (_, i) =>
    Math.round(yMin + (yRange * i) / 4)
  );

  /* ── x-axis labels (first, boundary, last) ─────────────────────────── */
  const xLabels: { idx: number; label: string }[] = [];
  if (allDates.length > 0) {
    xLabels.push({ idx: 0, label: allDates[0].slice(5) });
    if (histLen > 0 && histLen < allDates.length) {
      xLabels.push({ idx: histLen, label: allDates[histLen].slice(5) });
    }
    xLabels.push({
      idx: allDates.length - 1,
      label: allDates[allDates.length - 1].slice(5),
    });
  }

  return (
    <div className="bg-slate-800/50 backdrop-blur rounded-xl border border-slate-700 p-6 w-full h-full flex flex-col">
      {/* Trend badge */}
      <div className="flex items-center gap-4 mb-4">
        <span
          className="text-sm font-semibold px-3 py-1.5 rounded-full"
          style={{
            color: trendColor[summary.trend],
            backgroundColor: `${trendColor[summary.trend]}18`,
          }}
        >
          {trendIcon[summary.trend]} {summary.trend}
        </span>
        <span className="text-sm text-slate-400">
          Recent avg: <span className="text-white font-medium">{summary.recent_avg_gCO2}</span> → Forecast avg:{" "}
          <span className="text-emerald-400 font-medium">{summary.forecast_avg_gCO2}</span> {summary.unit}
        </span>
      </div>

      {/* Chart */}
      <svg
        viewBox={`0 0 ${CHART_W} ${CHART_H}`}
        className="w-full flex-1"
        preserveAspectRatio="xMidYMid meet"
      >
        {/* Grid lines */}
        {yTicks.map((tick) => (
          <g key={tick}>
            <line
              x1={PAD.left}
              x2={CHART_W - PAD.right}
              y1={y(tick)}
              y2={y(tick)}
              stroke="#334155"
              strokeWidth={1}
            />
            <text
              x={PAD.left - 8}
              y={y(tick) + 6}
              textAnchor="end"
              fontSize={14}
              fill="#94a3b8"
            >
              {tick}
            </text>
          </g>
        ))}

        {/* Boundary line between history and forecast */}
        {histLen > 0 && histLen < allDates.length && (
          <line
            x1={x(histLen)}
            x2={x(histLen)}
            y1={PAD.top}
            y2={PAD.top + INNER_H}
            stroke="#475569"
            strokeDasharray="6,6"
            strokeWidth={2}
          />
        )}

        {/* Confidence band */}
        <path d={bandPath} fill="#22c55e" opacity={0.15} />

        {/* History line */}
        <path
          d={historyPath}
          fill="none"
          stroke="#3b82f6"
          strokeWidth={3}
          strokeLinecap="round"
          strokeLinejoin="round"
        />

        {/* Connector */}
        {connectorPath && (
          <path
            d={connectorPath}
            fill="none"
            stroke="#64748b"
            strokeWidth={2}
            strokeDasharray="8,6"
          />
        )}

        {/* Forecast line */}
        <path
          d={forecastPath}
          fill="none"
          stroke="#22c55e"
          strokeWidth={3.5}
          strokeLinecap="round"
          strokeLinejoin="round"
        />

        {/* Forecast dots */}
        {forecast.map((f, i) => (
          <circle
            key={f.date}
            cx={x(histLen + i)}
            cy={y(f.predicted)}
            r={5}
            fill="#22c55e"
          />
        ))}

        {/* x-axis labels */}
        {xLabels.map(({ idx, label }) => (
          <text
            key={idx}
            x={x(idx)}
            y={CHART_H - 12}
            textAnchor="middle"
            fontSize={14}
            fill="#94a3b8"
          >
            {label}
          </text>
        ))}

        {/* Legend */}
        <line x1={PAD.left} y1={20} x2={PAD.left + 40} y2={20} stroke="#3b82f6" strokeWidth={3} />
        <text x={PAD.left + 48} y={26} fontSize={14} fill="#cbd5e1">
          Historical
        </text>
        <line x1={PAD.left + 160} y1={20} x2={PAD.left + 200} y2={20} stroke="#22c55e" strokeWidth={3} />
        <text x={PAD.left + 208} y={26} fontSize={14} fill="#cbd5e1">
          Forecast (7d)
        </text>
      </svg>
    </div>
  );
}
