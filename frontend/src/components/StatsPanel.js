import { useState, memo } from 'react';
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip,
  ResponsiveContainer, PieChart, Pie, Cell,
} from 'recharts';

const COLORS = [
  '#667eea','#764ba2','#f97316','#22c55e','#06b6d4',
  '#ec4899','#eab308','#14b8a6','#8b5cf6','#f43f5e',
  '#84cc16','#0ea5e9','#d946ef','#fb923c','#34d399',
  '#60a5fa','#a78bfa','#fb7185','#4ade80','#facc15',
  '#38bdf8','#c084fc','#f472b6','#a3e635','#2dd4bf',
  '#818cf8','#fbbf24','#f87171','#86efac','#93c5fd',
];

const BAR_RANGE_OPTIONS  = [10, 15, 20, 25, 30];
const PIE_RANGE_OPTIONS  = [10, 15, 20, 25, 30];

// Single fixed height for all three panels — avoids flex-stretch whitespace mismatch
const CHART_HEIGHT = 420;
const RADIAN = Math.PI / 180;

function RangeSelector({ value, onChange, options = BAR_RANGE_OPTIONS }) {
  return (
    <div className="range-selector">
      <label>Show top</label>
      <select value={value} onChange={e => onChange(Number(e.target.value))}>
        {options.map(n => <option key={n} value={n}>{n}</option>)}
      </select>
    </div>
  );
}

export default memo(function StatsPanel({ hometowns, sports, stateData = [] }) {
  const [hometownRange, setHometownRange] = useState(10);
  const [sportsRange,   setSportsRange]   = useState(10);
  const [statesRange,   setStatesRange]   = useState(10);

  const topHometowns = [...hometowns]
    .sort((a, b) => b.total_athletes - a.total_athletes)
    .slice(0, hometownRange)
    .map(h => ({ name: `${h.city_name}, ${h.state_code}`, athletes: h.total_athletes }));

  const topStates = [...stateData]
    .sort((a, b) => b.total_athletes_in_state - a.total_athletes_in_state)
    .slice(0, statesRange)
    .map(s => ({ name: s.state_code, athletes: s.total_athletes_in_state }));

  // Pie: top N slices + one "Others" slice for the rest
  const sortedSports = [...sports].sort((a, b) => b.total_us_athletes - a.total_us_athletes);
  const othersValue  = sortedSports.slice(sportsRange).reduce((sum, s) => sum + s.total_us_athletes, 0);
  const pieData = [
    ...sortedSports.slice(0, sportsRange).map(s => ({ name: s.sport_name, value: s.total_us_athletes })),
    ...(othersValue > 0 ? [{ name: 'Others', value: othersValue }] : []),
  ];

  const renderPieLabel = ({ name, cx, cy, midAngle, outerRadius, percent }) => {
    const radius  = outerRadius + 22;
    const x       = cx + radius * Math.cos(-midAngle * RADIAN);
    const y       = cy + radius * Math.sin(-midAngle * RADIAN);
    const maxLen  = percent > 0.07 ? 16 : percent > 0.04 ? 11 : percent > 0.02 ? 7 : 4;
    const display = name.length > maxLen ? name.slice(0, maxLen - 1) + '…' : name;
    return (
      <text x={x} y={y} fill="#333" fontSize={9}
        textAnchor={x > cx ? 'start' : 'end'} dominantBaseline="central">
        {display}
      </text>
    );
  };

  return (
    <div className="stats-row">

      {/* Top Hometowns */}
      <div className="stats-panel-card">
        <div className="stats-card-header">
          <h3>🏘️ Top Hometowns by Athletes</h3>
          <RangeSelector value={hometownRange} onChange={setHometownRange} />
        </div>
        <ResponsiveContainer width="100%" height={CHART_HEIGHT}>
          <BarChart layout="vertical" data={topHometowns}
            margin={{ top: 4, right: 24, left: 0, bottom: 4 }}>
            <CartesianGrid strokeDasharray="3 3" horizontal={false} />
            <XAxis type="number" tick={{ fontSize: 11 }} />
            <YAxis type="category" dataKey="name" width={130} tick={{ fontSize: 11 }} />
            <Tooltip formatter={(v) => [`${v} athletes`, 'Athletes']} />
            <Bar dataKey="athletes" fill="#667eea" radius={[0, 4, 4, 0]} isAnimationActive={false} />
          </BarChart>
        </ResponsiveContainer>
      </div>

      {/* Top Sports — pie with N + "Others" */}
      <div className="stats-panel-card">
        <div className="stats-card-header">
          <h3>🥇 Top Sports Distribution</h3>
          <RangeSelector value={sportsRange} onChange={setSportsRange} options={PIE_RANGE_OPTIONS} />
        </div>
        <ResponsiveContainer width="100%" height={CHART_HEIGHT}>
          <PieChart margin={{ top: 8, right: 36, bottom: 8, left: 36 }}>
            <Pie
              data={pieData}
              cx="50%"
              cy="50%"
              outerRadius="82%"
              dataKey="value"
              label={renderPieLabel}
              labelLine={{ stroke: '#bbb', strokeWidth: 0.8 }}
              isAnimationActive={false}
            >
              {pieData.map((entry, i) => (
                <Cell key={i} fill={entry.name === 'Others' ? '#9ca3af' : COLORS[i % COLORS.length]} />
              ))}
            </Pie>
            <Tooltip formatter={(v, n) => [`${v} athletes`, n]} />
          </PieChart>
        </ResponsiveContainer>
      </div>

      {/* Top States */}
      <div className="stats-panel-card">
        <div className="stats-card-header">
          <h3>🗾 Top States by Athletes</h3>
          <RangeSelector value={statesRange} onChange={setStatesRange} />
        </div>
        <ResponsiveContainer width="100%" height={CHART_HEIGHT}>
          <BarChart layout="vertical" data={topStates}
            margin={{ top: 4, right: 24, left: 0, bottom: 4 }}>
            <CartesianGrid strokeDasharray="3 3" horizontal={false} />
            <XAxis type="number" tick={{ fontSize: 11 }} />
            <YAxis type="category" dataKey="name" width={40} tick={{ fontSize: 11 }} />
            <Tooltip formatter={(v) => [`${v} athletes`, 'Athletes']} />
            <Bar dataKey="athletes" fill="#764ba2" radius={[0, 4, 4, 0]} isAnimationActive={false} />
          </BarChart>
        </ResponsiveContainer>
      </div>

    </div>
  );
});
