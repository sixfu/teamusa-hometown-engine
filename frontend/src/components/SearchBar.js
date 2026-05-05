import { useState } from 'react';
import { searchHometowns, getSportConcentration } from '../services/api';

const THRESHOLD = 1.5;

export default function SearchBar({ onSelectHomtown, athleteType = 'olympic' }) {
  const [cityName, setCityName] = useState('');
  const [stateCode, setStateCode] = useState('');
  const [searchResults, setSearchResults] = useState([]);
  const [sportPatterns, setSportPatterns] = useState([]);
  const [regionLabel, setRegionLabel] = useState('');
  const [loading, setLoading] = useState(false);
  const [showModal, setShowModal] = useState(false);

  const handleSearch = async (e) => {
    e.preventDefault();
    if (!cityName && !stateCode) {
      alert('Please enter a city name or state code');
      return;
    }
    try {
      setLoading(true);
      const [results, patterns] = await Promise.all([
        searchHometowns(cityName, stateCode, athleteType),
        getSportConcentration(cityName || null, stateCode || null, athleteType).catch(() => []),
      ]);
      setSearchResults(results);
      setSportPatterns((patterns || []).filter(d => d.concentration_ratio >= THRESHOLD));
      setRegionLabel([cityName, stateCode].filter(Boolean).join(', '));
      setShowModal(true);
    } catch (error) {
      console.error('Search error:', error);
      alert('Search failed. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  const handleSelectResult = (hometown) => {
    onSelectHomtown(hometown.hometown_id);
    setShowModal(false);
  };

  const handleClose = () => {
    setShowModal(false);
    setCityName('');
    setStateCode('');
  };

  const label = athleteType === 'paralympic' ? 'Paralympic' : 'Olympic';

  return (
    <>
      <div className="search-bar">
        <form onSubmit={handleSearch}>
          <input
            type="text"
            placeholder="City name (e.g., Los Angeles)"
            value={cityName}
            onChange={(e) => setCityName(e.target.value)}
            className="search-input"
          />
          <input
            type="text"
            placeholder="State code (e.g., CA)"
            value={stateCode}
            onChange={(e) => setStateCode(e.target.value.toUpperCase())}
            maxLength="2"
            className="search-input"
          />
          <button type="submit" disabled={loading} className="search-button">
            {loading ? 'Searching…' : 'Search'}
          </button>
        </form>
      </div>

      {showModal && (
        <div className="search-modal-overlay" onClick={handleClose}>
          <div className="search-modal" onClick={(e) => e.stopPropagation()}>
            <button className="modal-close" onClick={handleClose}>✕</button>

            {/* Sport Patterns Section */}
            {sportPatterns.length > 0 && (
              <div className="smodal-patterns">
                <h3>🎯 Sport Patterns — {regionLabel}</h3>
                <div className="smodal-explain">
                  <strong>Concentration ratio</strong> measures how many times more likely athletes
                  from this region are to compete in a sport compared to the national average.
                  For example, <strong>2.5×</strong> means athletes here are 2.5 times more
                  represented in that sport than the US average. Only sports above 1.5× are shown.
                </div>
                <ul className="smodal-pattern-list">
                  {sportPatterns.map(d => (
                    <li key={d.sport_name} className="smodal-pattern-item">
                      <div className="spi-header">
                        <span className="spi-sport">{d.sport_name}</span>
                        <span className="spi-ratio">{d.concentration_ratio}× national avg</span>
                      </div>
                      <div className="spi-bar-wrap">
                        <div
                          className="spi-bar"
                          style={{ width: `${Math.min(100, (d.concentration_ratio / 5) * 100)}%` }}
                        />
                      </div>
                      <div className="spi-detail">
                        {d.local_count} local athletes ({d.local_pct}% of region)
                        &nbsp;·&nbsp; {d.national_pct}% nationally
                      </div>
                    </li>
                  ))}
                </ul>
              </div>
            )}

            {/* Matching Hometowns Section */}
            <div className="smodal-results">
              <h3>
                {searchResults.length > 0
                  ? `📍 ${searchResults.length} Matching Hometown${searchResults.length !== 1 ? 's' : ''}`
                  : '📍 No Matching Hometowns'}
              </h3>
              <p className="smodal-results-note">
                The number shown is the count of <strong>US {label} athletes</strong> who
                listed that city as their hometown. Click a location to open its full story.
              </p>
              {searchResults.length > 0 ? (
                <ul className="search-modal-list">
                  {searchResults.map((h) => (
                    <li key={h.hometown_id}>
                      <button className="search-modal-item" onClick={() => handleSelectResult(h)}>
                        <span className="smi-location">
                          <strong>{h.city_name}</strong>, {h.state_code}
                        </span>
                        <span className="smi-count">{h.total_athletes} athletes</span>
                      </button>
                    </li>
                  ))}
                </ul>
              ) : (
                <p className="search-modal-empty">Try a different city name or state code.</p>
              )}
            </div>

            <button className="search-modal-close-btn" onClick={handleClose}>
              Close &amp; Search Again
            </button>
          </div>
        </div>
      )}
    </>
  );
}
