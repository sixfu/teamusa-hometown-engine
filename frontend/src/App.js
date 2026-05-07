import { useState, useEffect, useRef, useCallback } from 'react';
import './App.css';
import StatsPanel from './components/StatsPanel';
import MapContainer from './components/MapContainer';
import HomtownDetail from './components/HomtownDetail';
import ExploreMode from './components/ExploreMode';
import CompareMode from './components/CompareMode';
import SportFinder from './components/SportFinder';
import { getHometowns, getSports, getHometownsByState, getMapObservation, getMapObservationFromList } from './services/api';

function App() {
  const [hometowns, setHometowns] = useState([]);
  const [sports, setSports] = useState([]);
  const [stateData, setStateData] = useState([]);
  const [selectedHomtown, setSelectedHomtown] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [mode, setMode] = useState('default'); // 'default' | 'explore' | 'compare'
  const [athleteType, setAthleteType] = useState('olympic'); // 'olympic' | 'paralympic'
  const [mapObservation, setMapObservation] = useState(null);
  const [obsRefreshing, setObsRefreshing] = useState(false);
  const [visibleHometowns, setVisibleHometowns] = useState([]);
  const autoRefreshNeededRef = useRef(false);

  useEffect(() => {
    const loadData = async () => {
      try {
        setLoading(true);
        setMapObservation(null);
        const [hometownData, sportsData, stateD] = await Promise.all([
          getHometowns(athleteType),
          getSports(athleteType),
          getHometownsByState(athleteType),
        ]);
        setHometowns(hometownData);
        setSports(sportsData);
        setStateData(stateD);
        setError(null);
        // Fire observation request after main data loads (non-blocking)
        getMapObservation(athleteType)
          .then(d => setMapObservation(d?.observation ?? null))
          .catch(() => {});
      } catch (err) {
        console.error('Error loading data:', err);
        setError('Failed to load data. Make sure the backend is running.');
      } finally {
        setLoading(false);
      }
    };
    loadData();
  }, [athleteType]);

  const handleAthleteTypeChange = (type) => {
    setAthleteType(type);
    setSelectedHomtown(null);
  };

  const refreshMapObservation = () => {
    const total = hometowns.reduce((s, h) => s + h.total_athletes, 0);
    const topVisible = visibleHometowns.slice(0, 10).map(h => ({
      city_name: h.city_name,
      state_code: h.state_code,
      total_athletes: h.total_athletes,
    }));
    setObsRefreshing(true);
    getMapObservationFromList(topVisible, total, athleteType)
      .then(d => setMapObservation(d?.observation ?? null))
      .catch(() => {})
      .finally(() => setObsRefreshing(false));
  };

  // Mark that a refresh is needed each time the user switches to map view
  useEffect(() => {
    if (mode === 'default') {
      autoRefreshNeededRef.current = true;
    }
  }, [mode]);

  // Mark refresh needed when the map filter mode changes (All Cities ↔ Sport Leaders)
  const handleFilterModeChange = useCallback(() => {
    autoRefreshNeededRef.current = true;
  }, []);

  // Fire the auto-refresh once MapContainer reports its visible hometowns
  useEffect(() => {
    if (!autoRefreshNeededRef.current || visibleHometowns.length === 0 || obsRefreshing) return;
    autoRefreshNeededRef.current = false;
    refreshMapObservation();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [visibleHometowns]);

  if (loading) {
    return (
      <div className="app loading-container">
        <h1>Loading...</h1>
      </div>
    );
  }

  if (error) {
    return (
      <div className="app error-container">
        <h1>Error</h1>
        <p>{error}</p>
      </div>
    );
  }

  const isParalympic = athleteType === 'paralympic';

  return (
    <div className={`app ${isParalympic ? 'app--paralympic' : ''}`}>
      <header className="app-header">
        <div className="header-top">
          <div className="header-title-block">
            <h1>🏅 Team USA Hometown Success Engine</h1>
            <p>Discover the stories behind America's Olympic/Paralympic athletes</p>
          </div>
          <div className="summary-card">
            <div className="summary-item">
              <span className="summary-num">
                {hometowns.reduce((s, h) => s + h.total_athletes, 0).toLocaleString()}
              </span>
              <span className="summary-lbl">Athletes</span>
            </div>
            <div className="summary-item">
              <span className="summary-num">{hometowns.length.toLocaleString()}</span>
              <span className="summary-lbl">Hometowns</span>
            </div>
            <div className="summary-item">
              <span className="summary-num">{sports.length}</span>
              <span className="summary-lbl">Sports</span>
            </div>
          </div>
          <div className="header-controls">
            <nav className="mode-tabs">
              <button
                className={`mode-tab ${mode === 'default' ? 'active' : ''}`}
                onClick={() => setMode('default')}
              >
                🗺️ Map View
              </button>
              <button
                className={`mode-tab ${mode === 'explore' ? 'active' : ''}`}
                onClick={() => setMode('explore')}
              >
                🔭 Explore
              </button>
              <button
                className={`mode-tab ${mode === 'compare' ? 'active' : ''}`}
                onClick={() => setMode('compare')}
              >
                ⚖️ Compare
              </button>
            </nav>
            <div className="athlete-type-toggle">
              <button
                className={`athlete-type-btn ${athleteType === 'olympic' ? 'active olympic' : ''}`}
                onClick={() => handleAthleteTypeChange('olympic')}
              >
                🏅 Olympians
              </button>
              <button
                className={`athlete-type-btn ${athleteType === 'paralympic' ? 'active paralympic' : ''}`}
                onClick={() => handleAthleteTypeChange('paralympic')}
              >
                ♿ Paralympians
              </button>
            </div>
          </div>
        </div>
      </header>

      {mode === 'default' && (
        <>
          <StatsPanel hometowns={hometowns} sports={sports} stateData={stateData} />
          <div className="app-container">
            <main className="app-main">
              <MapContainer
                hometowns={hometowns}
                onSelectHomtown={setSelectedHomtown}
                onVisibleChange={setVisibleHometowns}
                onFilterModeChange={handleFilterModeChange}
                athleteType={athleteType}
              />
              <SportFinder />
            </main>
          </div>
        </>
      )}

      {mode === 'explore' && (
        <ExploreMode
          sports={sports}
          athleteType={athleteType}
          onSelectHomtown={setSelectedHomtown}
        />
      )}

      {mode === 'compare' && (
        <CompareMode athleteType={athleteType} />
      )}

      {selectedHomtown && (
        <HomtownDetail
          homtownId={selectedHomtown}
          onClose={() => setSelectedHomtown(null)}
          athleteType={athleteType}
        />
      )}
    </div>
  );
}

export default App;
