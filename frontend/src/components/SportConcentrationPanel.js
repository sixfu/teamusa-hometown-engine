import { useState, useEffect } from 'react';
import { getSportConcentration } from '../services/api';

const THRESHOLD = 1.5;

export default function SportConcentrationPanel({ region, athleteType = 'olympic' }) {
  const [data, setData] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    if (!region) return;
    const { cityName, stateCode } = region;
    setLoading(true);
    setError(null);
    getSportConcentration(cityName, stateCode, athleteType)
      .then(setData)
      .catch(() => setError('Could not load sport concentration data.'))
      .finally(() => setLoading(false));
  }, [region, athleteType]);

  const regionLabel = [region.cityName, region.stateCode].filter(Boolean).join(', ');
  const notable = data.filter(d => d.concentration_ratio >= THRESHOLD);

  return (
    <div className="concentration-panel">
      <h3>Sport Patterns — {regionLabel}</h3>
      <p className="concentration-note">
        Sports listed here are represented at a higher rate among athletes from this
        region than the national average. These patterns <em>could reflect</em> local
        training environments, community traditions, or cultural factors — not
        necessarily causes.
      </p>

      {loading && <p className="concentration-loading">Analyzing…</p>}
      {error && <p className="concentration-error">{error}</p>}

      {!loading && !error && notable.length === 0 && data.length > 0 && (
        <p className="concentration-empty">
          No sport stands out unusually compared to the national average for this region.
        </p>
      )}

      {!loading && !error && notable.length > 0 && (
        <ul className="concentration-list">
          {notable.map(d => (
            <li key={d.sport_name} className="concentration-item">
              <div className="concentration-sport">{d.sport_name}</div>
              <div className="concentration-bar-wrap">
                <div
                  className="concentration-bar"
                  style={{ width: `${Math.min(100, (d.concentration_ratio / 5) * 100)}%` }}
                />
              </div>
              <div className="concentration-stats">
                <span className="concentration-ratio">{d.concentration_ratio}× national avg</span>
                <span className="concentration-counts">
                  {d.local_count} local · {d.local_pct}% here vs {d.national_pct}% nationally
                </span>
              </div>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
