import React, { useState, useEffect } from 'react';
import { getHomtownDetail } from '../services/api';

export default function HomtownDetail({ homtownId, onClose, athleteType = 'olympic' }) {
  const [hometown, setHometown] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    const loadDetail = async () => {
      try {
        setLoading(true);
        const data = await getHomtownDetail(homtownId, athleteType);
        setHometown(data);
        setError(null);
      } catch (err) {
        console.error('Error loading hometown detail:', err);
        setError('Failed to load hometown details');
      } finally {
        setLoading(false);
      }
    };
    loadDetail();
  }, [homtownId, athleteType]);

  if (loading) {
    return (
      <div className="modal-overlay" onClick={onClose}>
        <div className="modal-content" onClick={(e) => e.stopPropagation()}>
          <h2>Loading...</h2>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="modal-overlay" onClick={onClose}>
        <div className="modal-content" onClick={(e) => e.stopPropagation()}>
          <h2>Error</h2>
          <p>{error}</p>
          <button onClick={onClose} className="modal-close-btn">Close</button>
        </div>
      </div>
    );
  }

  if (!hometown) return null;

  const label = athleteType === 'paralympic' ? 'Paralympic' : 'Olympic';
  const elevationDisplay = hometown.elevation != null && !Number.isNaN(Number(hometown.elevation))
    ? `${Math.round(Number(hometown.elevation))}m`
    : 'N/A';

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-content" onClick={(e) => e.stopPropagation()}>
        <button className="modal-close" onClick={onClose}>✕</button>

        <div className="modal-header">
          <h2>{hometown.city_name}, {hometown.state_code}</h2>
          <p className="athletes-count">{hometown.total_athletes} {label} Athletes</p>
        </div>

        <div className="modal-body">

          {/* Story — first, with word count */}
          {hometown.story && (
            <div className="info-section story-section">
              <h3>📖 The Story</h3>
              <div className="story-text">{hometown.story}</div>
            </div>
          )}

          {/* Geographic Profile */}
          <div className="info-section">
            <h3>🌍 Geographic Profile</h3>
            <ul className="geo-profile-list">
              {hometown.region && (
                <li><span className="geo-label">Region</span><span className="geo-value">{hometown.region}</span></li>
              )}
              <li><span className="geo-label">Elevation</span><span className="geo-value">{elevationDisplay}</span></li>
              {hometown.climate_zone && (
                <li><span className="geo-label">Climate</span><span className="geo-value">{hometown.climate_zone}</span></li>
              )}
            </ul>
          </div>

          {/* Sports Statistics */}
          {hometown.top_sports && hometown.top_sports.length > 0 && (
            <div className="info-section">
              <h3>🏅 Sports Statistics</h3>
              <ul className="sports-list">
                {hometown.top_sports.map((sport, index) => (
                  <li key={index}>
                    <span className="sport-name">{sport.sport_name}</span>
                    <span className="sport-count">{sport.count} athletes</span>
                  </li>
                ))}
              </ul>
            </div>
          )}

        </div>

        <div className="modal-footer">
          <button onClick={onClose} className="modal-close-btn">Close</button>
        </div>
      </div>
    </div>
  );
}
