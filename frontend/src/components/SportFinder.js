import { useState } from 'react';
import { findMatchedSports } from '../services/api';

export default function SportFinder() {
  const [form, setForm] = useState({ height: '', weight: '', birth_city: '', birth_state: '' });
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const handleChange = (e) => {
    setForm(prev => ({ ...prev, [e.target.name]: e.target.value }));
  };

  const handleSubmit = async () => {
    setLoading(true);
    setError(null);
    setResult(null);
    try {
      const data = await findMatchedSports(form);
      setResult(data);
    } catch (err) {
      const msg = err.response?.data?.error
        || (err.message === 'Network Error'
          ? 'Cannot reach the backend. Make sure the Flask server is running on port 5000 and you restarted npm start after creating .env.local.'
          : err.message)
        || 'Failed to find sport matches. Please try again.';
      setError(msg);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="sport-finder-card-wrap">
      <h3 className="sport-finder-title">Find Your Sport Match</h3>
      <p className="sport-finder-subtitle">
        Enter your stats to discover which Olympic sports best match your profile.
        All fields are optional — provide as many as you like.
      </p>
      <div className="sport-finder-inputs">
        <label className="sport-finder-field">
          <span>Height (cm)</span>
          <input
            type="number"
            name="height"
            value={form.height}
            onChange={handleChange}
            placeholder="e.g. 180"
            min="50"
            max="300"
          />
        </label>
        <label className="sport-finder-field">
          <span>Weight (kg)</span>
          <input
            type="number"
            name="weight"
            value={form.weight}
            onChange={handleChange}
            placeholder="e.g. 75"
            min="20"
            max="500"
          />
        </label>
        <label className="sport-finder-field">
          <span>City</span>
          <input
            type="text"
            name="birth_city"
            value={form.birth_city}
            onChange={handleChange}
            placeholder="e.g. Houston"
          />
        </label>
        <label className="sport-finder-field">
          <span>State</span>
          <input
            type="text"
            name="birth_state"
            value={form.birth_state}
            onChange={handleChange}
            placeholder="e.g. TX"
            maxLength={2}
          />
        </label>
      </div>
      <button
        className="sport-finder-btn"
        onClick={handleSubmit}
        disabled={loading}
      >
        {loading ? 'Finding…' : 'Find My Sport'}
      </button>

      {error && <p className="sport-finder-error">{error}</p>}

      {result && result.sports && (
        <div className="sport-finder-results">
          <h4>Your Top Sport Matches</h4>
          <div className="sport-finder-cards">
            {result.sports.map((item, i) => (
              <div key={item.sport} className="sport-finder-card">
                <span className="sport-finder-rank">#{i + 1}</span>
                <span className="sport-finder-sport">{item.sport}</span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
