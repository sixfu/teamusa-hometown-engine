import { useState, useRef } from 'react';
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid } from 'recharts';
import MapContainer from './MapContainer';
import SearchBar from './SearchBar';
import AgentQA from './AgentQA';
import { getSportHeatmap, getSportAnimation, getSportHeatmapDescription, getSportYearCounts } from '../services/api';

export default function ExploreMode({ sports, athleteType = 'olympic', onSelectHomtown }) {
  const [activeTab, setActiveTab] = useState('sport');

  // Sport-exploration state (preserved across tab switches)
  const [selectedSport, setSelectedSport] = useState('');
  const [heatmapData, setHeatmapData] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [animationSvg, setAnimationSvg] = useState(null);
  const [animationLoading, setAnimationLoading] = useState(false);
  const [heatmapDesc, setHeatmapDesc] = useState(null);
  const [yearCounts, setYearCounts] = useState([]);
  const latestSportRef = useRef('');

  const handleSportChange = async (sportName) => {
    latestSportRef.current = sportName;
    setSelectedSport(sportName);
    setAnimationSvg(null);
    setHeatmapDesc(null);
    setHeatmapData([]);
    setYearCounts([]);
    if (!sportName) return;

    setLoading(true);
    setAnimationLoading(true);
    setError(null);
    try {
      const [data, animData, descData, yearData] = await Promise.allSettled([
        getSportHeatmap(sportName, athleteType),
        getSportAnimation(sportName, athleteType),
        getSportHeatmapDescription(sportName, athleteType),
        getSportYearCounts(sportName, athleteType),
      ]);
      if (latestSportRef.current !== sportName) return;

      setHeatmapData(data.status === 'fulfilled' ? data.value : []);
      if (animData.status === 'fulfilled' && animData.value?.svg) {
        setAnimationSvg(animData.value.svg);
      }
      if (descData.status === 'fulfilled' && descData.value?.observations) {
        setHeatmapDesc(descData.value.observations);
      }
      if (yearData.status === 'fulfilled' && Array.isArray(yearData.value)) {
        setYearCounts(yearData.value);
      }
      if (data.status === 'rejected') {
        setError('Could not load heatmap data. Please try again.');
      }
    } finally {
      if (latestSportRef.current === sportName) {
        setLoading(false);
        setAnimationLoading(false);
      }
    }
  };

  const topCities = [...heatmapData]
    .sort((a, b) => b.sport_athletes - a.sport_athletes)
    .slice(0, 5);

  return (
    <div className="explore-mode">

      {/* ── Tab bar ── */}
      <div className="explore-tab-bar">
        <button
          className={`explore-tab ${activeTab === 'sport' ? 'active' : ''}`}
          onClick={() => setActiveTab('sport')}
        >
          🔭 Explore Sport
        </button>
        <button
          className={`explore-tab ${activeTab === 'search' ? 'active' : ''}`}
          onClick={() => setActiveTab('search')}
        >
          🔍 Search Hometowns
        </button>
        <button
          className={`explore-tab ${activeTab === 'agent' ? 'active' : ''}`}
          onClick={() => setActiveTab('agent')}
        >
          🤖 Ask Agent
        </button>
      </div>

      {/* ── Sport tab ── */}
      {activeTab === 'sport' && (
        <div className="explore-sport-content">
          <div className="explore-left-col">
            <div className="explore-sidebar">
              <h2>🔭 Explore by Sport</h2>
              <p className="explore-description">
                Select a sport to reveal where its athletes are concentrated across the US.
                Larger circles indicate higher concentration of athletes.
                For more details about specific cities, switch to the{' '}
                <strong>Search Hometowns</strong> tab.
              </p>

              <label className="explore-label" htmlFor="sport-select"><b>Select a sport</b></label>
              <select
                id="sport-select"
                className="explore-select"
                value={selectedSport}
                onChange={e => handleSportChange(e.target.value)}
              >
                <option value="">— choose a sport —</option>
                {sports
                  .sort((a, b) => a.sport_name.localeCompare(b.sport_name))
                  .map(s => (
                    <option key={s.sport_id} value={s.sport_name}>
                      {s.sport_name}
                    </option>
                  ))}
              </select>

              {loading && <p className="explore-loading">Loading heatmap…</p>}
              {error && <p className="explore-error">{error}</p>}

              {!loading && selectedSport && heatmapData.length > 0 && (
                <div className="explore-summary">
                  <h4>Top concentrations</h4>
                  <ol className="explore-top-list">
                    {topCities.map(c => (
                      <li key={c.hometown_id} className={c.match_level === 'state' ? 'state-level' : ''}>
                        {c.match_level === 'state' ? (
                          <span>{c.state_code} (state)</span>
                        ) : (
                          <button
                            className="explore-city-link"
                            onClick={() => onSelectHomtown(c.hometown_id)}
                          >
                            {c.city_name}, {c.state_code}
                          </button>
                        )}
                        <span className="explore-count"> — {c.sport_athletes}</span>
                      </li>
                    ))}
                  </ol>
                </div>
              )}

              {!loading && selectedSport && heatmapData.length === 0 && !error && (
                <p className="explore-empty">No location data available for this sport.</p>
              )}

              <div className="explore-legend">
                <h4>Legend</h4>
                <div className="legend-row">
                  <span className="legend-dot large" />
                  <span>More athletes (city-level)</span>
                </div>
                <div className="legend-row">
                  <span className="legend-dot small" />
                  <span>Fewer athletes (city-level)</span>
                </div>
                <div className="legend-row">
                  <span className="legend-dot state" />
                  <span>State-level only (no city data)</span>
                </div>
              </div>
            </div>
          </div>

          <div className="explore-map">
            <div className="explore-map-area">
              <MapContainer heatmapMode={!!selectedSport} heatmapData={heatmapData} showDescription={false} />
              {!selectedSport && (
                <div className="explore-map-placeholder">
                  <p>Select a sport above to see its geographic distribution.</p>
                </div>
              )}

              {selectedSport && (animationLoading || animationSvg) && (
                <div className="explore-animation-overlay">
                  {animationLoading && (
                    <div className="explore-animation-loading">
                      <span className="explore-animation-spinner" />
                    </div>
                  )}
                  {!animationLoading && animationSvg && (
                    <div
                      className="explore-animation-svg"
                      dangerouslySetInnerHTML={{ __html: animationSvg }}
                    />
                  )}
                </div>
              )}
            </div>

            {heatmapDesc && (
              <div className="map-observation-box explore-obs-below">
                <span className="map-obs-label">🤖 AI-generated insight</span>
                <span className="map-obs-text">{heatmapDesc}</span>
              </div>
            )}

            {yearCounts.length > 0 && (
              <div className="explore-year-chart">
                <h4>📅 Athletes per Year — {selectedSport}</h4>
                <ResponsiveContainer width="100%" height={200}>
                  <BarChart data={yearCounts} margin={{ top: 4, right: 12, left: -10, bottom: 0 }}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" vertical={false} />
                    <XAxis
                      dataKey="year"
                      type="number"
                      domain={[1896, 2026]}
                      ticks={[1896, 1920, 1948, 1968, 1984, 2000, 2016, 2026]}
                      tick={{ fontSize: 10 }}
                    />
                    <YAxis tick={{ fontSize: 11 }} allowDecimals={false} width={30} />
                    <Tooltip
                      formatter={(value) => [value, 'Athletes']}
                      labelFormatter={(label) => `Year: ${label}`}
                      contentStyle={{ fontSize: '0.82rem' }}
                    />
                    <Bar dataKey="num_athletes" fill="#667eea" radius={[3, 3, 0, 0]} barSize={7} />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            )}
          </div>
        </div>
      )}

      {/* ── Search tab ── */}
      {activeTab === 'search' && (
        <div className="explore-search-content">
          <h2>🔍 Search Hometowns</h2>
          <SearchBar onSelectHomtown={onSelectHomtown} athleteType={athleteType} />
        </div>
      )}

      {/* ── Agent tab ── */}
      {activeTab === 'agent' && (
        <AgentQA athleteType={athleteType} />
      )}
    </div>
  );
}
