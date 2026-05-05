import { useState } from 'react';
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip,
  Legend, ResponsiveContainer,
} from 'recharts';
import { compareRegions } from '../services/api';

const US_STATES = [
  'AL','AK','AZ','AR','CA','CO','CT','DE','FL','GA',
  'HI','ID','IL','IN','IA','KS','KY','LA','ME','MD',
  'MA','MI','MN','MS','MO','MT','NE','NV','NH','NJ',
  'NM','NY','NC','ND','OH','OK','OR','PA','RI','SC',
  'SD','TN','TX','UT','VT','VA','WA','WV','WI','WY','DC',
];

function RegionPicker({ label, region, onChange }) {
  const { type, cityName, stateCode } = region;
  return (
    <div className="region-picker">
      <h3>{label}</h3>
      <div className="region-type-toggle">
        <button
          className={type === 'city' ? 'active' : ''}
          onClick={() => onChange({ type: 'city', cityName: '', stateCode: '' })}
        >
          City
        </button>
        <button
          className={type === 'state' ? 'active' : ''}
          onClick={() => onChange({ type: 'state', cityName: '', stateCode: '' })}
        >
          State
        </button>
      </div>

      {type === 'city' && (
        <>
          <input
            className="compare-input"
            placeholder="City name (e.g. Los Angeles)"
            value={cityName}
            onChange={e => onChange({ ...region, cityName: e.target.value })}
          />
          <input
            className="compare-input"
            placeholder="State code (e.g. CA)"
            maxLength={2}
            value={stateCode}
            onChange={e => onChange({ ...region, stateCode: e.target.value.toUpperCase() })}
          />
        </>
      )}

      {type === 'state' && (
        <select
          className="compare-select"
          value={stateCode}
          onChange={e => onChange({ ...region, stateCode: e.target.value })}
        >
          <option value="">— select a state —</option>
          {US_STATES.map(s => <option key={s} value={s}>{s}</option>)}
        </select>
      )}
    </div>
  );
}

const TOP_N_OPTIONS = [15, 20, 25, 30];

function mergeForChart(sports1, sports2, label1, label2, n) {
  const top1 = sports1.slice(0, n);
  const top2 = sports2.slice(0, n);

  const top1Names = new Set(top1.map(s => s.sport_name));
  const lookup1 = Object.fromEntries(sports1.map(s => [s.sport_name, s.athlete_count]));
  const lookup2 = Object.fromEntries(sports2.map(s => [s.sport_name, s.athlete_count]));

  // A's top N first (A's rank order), with B's counts filled in
  const aRows = top1.map(s => ({
    sport: s.sport_name,
    [label1]: s.athlete_count,
    [label2]: lookup2[s.sport_name] ?? 0,
  }));

  // Then sports only in B's top N, not already in A's top N (B's rank order)
  const bOnlyRows = top2
    .filter(s => !top1Names.has(s.sport_name))
    .map(s => ({
      sport: s.sport_name,
      [label1]: lookup1[s.sport_name] ?? 0,
      [label2]: s.athlete_count,
    }));

  return [...aRows, ...bOnlyRows];
}

const EMPTY_REGION = { type: 'city', cityName: '', stateCode: '' };

export default function CompareMode({ athleteType = 'olympic' }) {
  const [region1, setRegion1] = useState(EMPTY_REGION);
  const [region2, setRegion2] = useState(EMPTY_REGION);
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [topN, setTopN] = useState(15);

  const isRegionReady = r =>
    r.type === 'state' ? !!r.stateCode : !!(r.cityName || r.stateCode);

  const handleCompare = async () => {
    setLoading(true);
    setError(null);
    setResult(null);
    try {
      const data = await compareRegions(
        region1.cityName || null, region1.stateCode || null,
        region2.cityName || null, region2.stateCode || null,
        athleteType,
      );
      setResult(data);
    } catch {
      setError('Comparison failed. Please check your inputs and try again.');
    } finally {
      setLoading(false);
    }
  };

  const canCompare = isRegionReady(region1) && isRegionReady(region2);

  const chartData = result
    ? mergeForChart(result.region1.sports, result.region2.sports, result.region1.label, result.region2.label, topN)
    : [];

  return (
    <div className="compare-mode">
      <div className="compare-header">
        <h2>⚖️ Compare Regions</h2>
        <p className="compare-description">
          Select two regions — cities or states — to compare their athlete counts and
          sport distributions side by side.
        </p>
      </div>

      <div className="compare-pickers">
        <RegionPicker label="Region A" region={region1} onChange={setRegion1} />
        <div className="compare-vs">vs</div>
        <RegionPicker label="Region B" region={region2} onChange={setRegion2} />
      </div>

      <div className="compare-actions">
        <button
          className="compare-btn"
          onClick={handleCompare}
          disabled={!canCompare || loading}
        >
          {loading ? 'Comparing…' : 'Compare'}
        </button>
      </div>

      {error && <p className="compare-error">{error}</p>}

      {result && (
        <div className="compare-results">
          <div className="compare-totals">
            <div className="compare-total-card">
              <div className="compare-total-label">{result.region1.label}</div>
              <div className="compare-total-num">
                {result.region1.sports.reduce((s, d) => s + d.athlete_count, 0)} athletes
              </div>
            </div>
            <div className="compare-total-card">
              <div className="compare-total-label">{result.region2.label}</div>
              <div className="compare-total-num">
                {result.region2.sports.reduce((s, d) => s + d.athlete_count, 0)} athletes
              </div>
            </div>
          </div>

          <div className="compare-chart-header">
            <h3 className="compare-chart-title">Sport Distribution Comparison</h3>
            <div className="compare-top-n">
              <label>Show top</label>
              <select value={topN} onChange={e => setTopN(Number(e.target.value))}>
                {TOP_N_OPTIONS.map(n => <option key={n} value={n}>{n}</option>)}
              </select>
              <span>sports</span>
            </div>
          </div>
          <p className="compare-chart-note">
            Top {topN} from each region — A's sports first, then sports unique to B.
            Up to {topN * 2} bars when the two regions share no sports.
          </p>
          <ResponsiveContainer width="100%" height={420}>
            <BarChart data={chartData} margin={{ top: 10, right: 30, left: 0, bottom: 100 }}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="sport" angle={-45} textAnchor="end" interval={0} />
              <YAxis />
              <Tooltip />
              <Legend verticalAlign="top" />
              <Bar dataKey={result.region1.label} fill="#6366f1" />
              <Bar dataKey={result.region2.label} fill="#f59e0b" />
            </BarChart>
          </ResponsiveContainer>

          {/* Tables use the same sports + order as the chart (combined ranking) */}
          <div className="compare-tables">
            {[result.region1, result.region2].map(r => {
              const sportLookup = Object.fromEntries(
                r.sports.map(s => [s.sport_name, s.athlete_count])
              );
              return (
                <div key={r.label} className="compare-table-wrap">
                  <h4>{r.label}</h4>
                  <table className="compare-table">
                    <thead>
                      <tr><th>Sport</th><th>Athletes</th></tr>
                    </thead>
                    <tbody>
                      {chartData.map(({ sport }) => (
                        <tr key={sport}>
                          <td>{sport}</td>
                          <td>{sportLookup[sport] ?? 0}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
}
