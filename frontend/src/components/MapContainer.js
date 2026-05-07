import { useState, useCallback, useMemo, useRef, useEffect } from 'react';
import { GoogleMap, useJsApiLoader, MarkerF, InfoWindowF } from '@react-google-maps/api';
import { getSportHubs } from '../services/api';

const mapCenter = { lat: 39.8283, lng: -98.5795 };
const mapContainerStyle = { width: '100%', height: '500px', borderRadius: '8px' };
const mapOptions = { zoom: 4, gestureHandling: 'greedy' };

const WINTER_SPORTS = new Set([
  'Alpine Skiing', 'Biathlon', 'Bobsleigh', 'Cross Country Skiing', 'Curling',
  'Figure Skating', 'Freestyle Skiing', 'Ice Hockey', 'Luge', 'Nordic Combined',
  'Short Track Speed Skating', 'Skeleton', 'Ski Jumping', 'Snowboarding', 'Speed Skating',
]);

// 30 visually distinct colors for sport hubs
const HUB_COLORS = [
  '#FF6B6B', '#4ECDC4', '#45B7D1', '#FFA07A', '#98D8C8',
  '#7EC8E3', '#FFD700', '#FF8C42', '#6BCB77', '#4D96FF',
  '#C77DFF', '#FF5733', '#52B788', '#F4A261', '#2D6A4F',
  '#E9C46A', '#264653', '#A8DADC', '#457B9D', '#1D3557',
  '#F72585', '#7209B7', '#3A0CA3', '#4361EE', '#4CC9F0',
  '#80B918', '#FFBE0B', '#FB5607', '#FF006E', '#8338EC',
];

// scale grows ~30% per zoom level, capped to avoid giant circles at high zoom
function buildIcon(count, maxCount, isStateLevel = false, zoom = 4) {
  const ratio = (maxCount > 0 && count > 1) ? count / maxCount : 0;
  const zoomFactor = Math.max(0.4, Math.min(2.5, Math.pow(1.3, zoom - 4)));
  const scale = (5 + ratio * 16) * zoomFactor;
  const opacity = 0.4 + ratio * 0.6;
  return {
    path: window.google.maps.SymbolPath.CIRCLE,
    scale,
    fillColor: isStateLevel ? '#f97316' : '#dc2626',
    fillOpacity: isStateLevel ? opacity * 0.7 : opacity,
    strokeColor: isStateLevel ? '#9a3412' : '#7f1d1d',
    strokeWeight: isStateLevel ? 1.5 : 1,
    strokeOpacity: isStateLevel ? 0.8 : 1,
  };
}

// Size = sport_count (athlete volume), opacity = concentration_ratio (geographic specificity)
function buildHubIcon(color, sportCount, maxSportCount, concentration, maxConc, zoom = 4) {
  const zoomFactor = Math.max(0.5, Math.min(2.5, Math.pow(1.3, zoom - 4)));
  const sizeRatio = maxSportCount > 1 ? (sportCount - 1) / (maxSportCount - 1) : 0.5;
  const scale = (6 + sizeRatio * 13) * zoomFactor;
  const opacity = 0.40 + Math.min(concentration / maxConc, 1) * 0.55;
  return {
    path: window.google.maps.SymbolPath.CIRCLE,
    scale,
    fillColor: color,
    fillOpacity: opacity,
    strokeColor: 'white',
    strokeWeight: 2,
    strokeOpacity: 1,
  };
}

// 0 is the sentinel for "All" (no limit)
const TOP_N_OPTIONS = [20, 25, 30, 35, 40, 45, 50, 100, 200, 500, 1000, 2000, 3000, 0];

export default function MapContainer({
  hometowns = [],
  onSelectHomtown,
  heatmapData,
  heatmapMode = false,
  showDescription = true,
  onVisibleChange,
  onFilterModeChange,
  athleteType = 'olympic',
}) {
  const [mapRef, setMapRef] = useState(null);
  const [mapBounds, setMapBounds] = useState(null);
  const [mapZoom, setMapZoom] = useState(4);
  const [hoveredMarker, setHoveredMarker] = useState(null);
  const [clickedMarker, setClickedMarker] = useState(null);
  const [topN, setTopN] = useState(20);
  const [filterMode, setFilterMode] = useState('all'); // 'all' | 'sport_leaders'
  const [rank1Data, setRank1Data] = useState([]);
  const [rank1Loading, setRank1Loading] = useState(false);
  const [legendOpen, setLegendOpen] = useState(true);
  const hoverTimer = useRef(null);

  const apiKey = process.env.REACT_APP_GOOGLE_MAPS_API_KEY;
  const { isLoaded } = useJsApiLoader({ googleMapsApiKey: apiKey || '' });

  const onLoad = useCallback(map => setMapRef(map), []);

  const onBoundsChanged = useCallback(() => {
    if (mapRef) {
      setMapBounds(mapRef.getBounds());
      setMapZoom(mapRef.getZoom());
    }
  }, [mapRef]);

  // Fetch rank-1 hub data when Sport Leaders mode is active or athleteType changes
  useEffect(() => {
    if (filterMode !== 'sport_leaders') return;
    setRank1Loading(true);
    setRank1Data([]);
    getSportHubs(athleteType)
      .then(data => setRank1Data(data || []))
      .catch(() => setRank1Data([]))
      .finally(() => setRank1Loading(false));
  }, [filterMode, athleteType]);

  // Top N hometowns within the current viewport (hometowns already sorted by athletes desc)
  const visibleTopN = useMemo(() => {
    if (!hometowns.length) return [];
    const all = topN === 0;
    if (!mapBounds) return all ? hometowns : hometowns.slice(0, topN);
    const inView = hometowns.filter(
      h => h.latitude && h.longitude &&
           mapBounds.contains({ lat: h.latitude, lng: h.longitude })
    );
    return all ? inView : inView.slice(0, topN);
  }, [mapBounds, hometowns, topN]);

  // heatmapMode stays true even while data is loading (empty array), preventing revert to default view
  const isHeatmap = heatmapMode;

  // Notify parent when filter mode changes so it can trigger an observation refresh
  useEffect(() => {
    if (onFilterModeChange) onFilterModeChange(filterMode);
  }, [filterMode, onFilterModeChange]);

  // Notify parent of visible hometowns in All Cities mode
  useEffect(() => {
    if (onVisibleChange && !isHeatmap && filterMode === 'all') {
      onVisibleChange(visibleTopN);
    }
  }, [visibleTopN, onVisibleChange, isHeatmap, filterMode]);

  // Notify parent of hub cities when Sport Leaders data loads
  useEffect(() => {
    if (!onVisibleChange || isHeatmap || filterMode !== 'sport_leaders') return;
    if (!rank1Data.length) return;
    const seen = new Set();
    const uniqueCities = rank1Data
      .filter(d => { if (seen.has(d.hometown_id)) return false; seen.add(d.hometown_id); return true; })
      .map(d => ({ hometown_id: d.hometown_id, city_name: d.city_name, state_code: d.state_code, total_athletes: d.sport_count }));
    onVisibleChange(uniqueCities);
  }, [rank1Data, filterMode, onVisibleChange, isHeatmap]);

  // Sorted unique sport names for consistent color assignment
  const uniqueSports = useMemo(
    () => [...new Set(rank1Data.map(d => d.sport_name))].sort(),
    [rank1Data]
  );

  const maxHubSportCount = useMemo(
    () => rank1Data.length ? Math.max(...rank1Data.map(d => d.sport_count), 1) : 1,
    [rank1Data]
  );
  const maxHubConc = useMemo(
    () => rank1Data.length ? Math.max(...rank1Data.map(d => d.concentration_ratio || 0), 1) : 1,
    [rank1Data]
  );

  // Hub markers with position offsets for same-city stacking
  const hubMarkers = useMemo(() => {
    if (!rank1Data.length) return [];
    const cityGroups = {};
    rank1Data.forEach(d => {
      if (!cityGroups[d.hometown_id]) cityGroups[d.hometown_id] = [];
      cityGroups[d.hometown_id].push(d);
    });
    return rank1Data
      .filter(d => d.latitude && d.longitude)
      .map(d => {
        const siblings = cityGroups[d.hometown_id];
        const idx = siblings.indexOf(d);
        const total = siblings.length;
        const sportIdx = uniqueSports.indexOf(d.sport_name);
        let lat = d.latitude;
        let lng = d.longitude;
        if (total > 1) {
          const angle = (idx * 2 * Math.PI) / total;
          lat += 0.015 * Math.cos(angle);
          lng += 0.015 * Math.sin(angle);
        }
        return { ...d, lat, lng, color: HUB_COLORS[sportIdx % HUB_COLORS.length], isHub: true };
      });
  }, [rank1Data, uniqueSports]);

  const hasHeatmapData = Array.isArray(heatmapData) && heatmapData.length > 0;

  const maxCount = hasHeatmapData
    ? Math.max(...heatmapData.map(d => d.sport_athletes))
    : Math.max(...visibleTopN.map(h => h.total_athletes), 1);

  const handleMouseOver = useCallback((marker) => {
    if (hoverTimer.current) clearTimeout(hoverTimer.current);
    setHoveredMarker(marker);
  }, []);

  const handleMouseOut = useCallback(() => {
    hoverTimer.current = setTimeout(() => setHoveredMarker(null), 150);
  }, []);

  const handleClick = useCallback((marker) => {
    if (hoverTimer.current) clearTimeout(hoverTimer.current);
    setHoveredMarker(null);
    setClickedMarker(marker);
  }, []);

  if (!apiKey) {
    return (
      <div className="map-container">
        <div className="map-error">
          <h3>⚠️ Google Maps API Key Missing</h3>
          <p>Set REACT_APP_GOOGLE_MAPS_API_KEY in your .env file.</p>
        </div>
      </div>
    );
  }

  const isShowingHubs = !isHeatmap && filterMode === 'sport_leaders';

  return (
    <div className="map-container">
      {!isHeatmap && showDescription && (
        <div className="map-description-row">
          <p className="map-description" style={{ margin: 0 }}>
            {filterMode === 'all' ? (
              <>
                {topN === 0 ? 'Showing' : 'Showing the top'}{' '}
                <select
                  className="map-top-n-inline"
                  value={topN}
                  onChange={e => setTopN(Number(e.target.value))}
                >
                  {TOP_N_OPTIONS.map(n => <option key={n} value={n}>{n === 0 ? 'All' : n}</option>)}
                </select>
                {' '}hometowns in current view — zoom in to explore local concentrations
              </>
            ) : rank1Loading ? (
              'Loading sport hubs…'
            ) : rank1Data.length === 0 ? (
              'No sport hubs found for this mode'
            ) : (
              <>
                <strong>Geographic Hubs:</strong> Geographic &ldquo;hubs&rdquo; where athletes have
                naturally clustered due to climate, infrastructure, or tradition. Each hub has both
                high concentration (city specializes in the sport) and enough athletes to matter.
                Click on the cities for details!
              </>
            )}
          </p>
          <div className="map-filter-toggle">
            <label className={`filter-opt ${filterMode === 'all' ? 'active' : ''}`}>
              <input type="radio" name="mapFilter" value="all"
                checked={filterMode === 'all'}
                onChange={() => setFilterMode('all')} />
              Top Athlete Hometowns
            </label>
            <label className={`filter-opt ${filterMode === 'sport_leaders' ? 'active' : ''}`}>
              <input type="radio" name="mapFilter" value="sport_leaders"
                checked={filterMode === 'sport_leaders'}
                onChange={() => setFilterMode('sport_leaders')} />
              🏆 Sport Hubs
            </label>
          </div>
        </div>
      )}

      <div className="map-google-wrap">
        {!isLoaded ? (
          <div style={{ height: '500px', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
            <p>Loading map…</p>
          </div>
        ) : (
          <GoogleMap
            mapContainerStyle={mapContainerStyle}
            center={mapCenter}
            options={mapOptions}
            onLoad={onLoad}
            onBoundsChanged={onBoundsChanged}
          >
            {/* Default map view: top N in viewport */}
            {!isHeatmap && filterMode === 'all' && visibleTopN.map(h =>
              h.latitude && h.longitude ? (
                <MarkerF
                  key={h.hometown_id}
                  position={{ lat: h.latitude, lng: h.longitude }}
                  icon={buildIcon(h.total_athletes, maxCount, false, mapZoom)}
                  onMouseOver={() => handleMouseOver(h)}
                  onMouseOut={handleMouseOut}
                  onClick={() => handleClick(h)}
                />
              ) : null
            )}

            {/* Sport Leaders hub markers */}
            {isShowingHubs && hubMarkers.map(h => (
              <MarkerF
                key={`hub-${h.hometown_id}-${h.sport_name}`}
                position={{ lat: h.lat, lng: h.lng }}
                icon={buildHubIcon(h.color, h.sport_count, maxHubSportCount, h.concentration_ratio, maxHubConc, mapZoom)}
                onMouseOver={() => handleMouseOver(h)}
                onMouseOut={handleMouseOut}
                onClick={() => handleClick(h)}
              />
            ))}

            {/* Explore mode: sport heatmap markers */}
            {isHeatmap && hasHeatmapData && heatmapData.map(h =>
              h.latitude && h.longitude ? (
                <MarkerF
                  key={h.hometown_id}
                  position={{ lat: h.latitude, lng: h.longitude }}
                  icon={buildIcon(h.sport_athletes, maxCount, h.match_level === 'state', mapZoom)}
                  onMouseOver={() => handleMouseOver({ ...h, total_athletes: h.sport_athletes })}
                  onMouseOut={handleMouseOut}
                  onClick={() => handleClick({ ...h, total_athletes: h.sport_athletes })}
                />
              ) : null
            )}

            {/* Hover tooltip */}
            {hoveredMarker && (
              <InfoWindowF
                position={{
                  lat: hoveredMarker.lat ?? hoveredMarker.latitude,
                  lng: hoveredMarker.lng ?? hoveredMarker.longitude,
                }}
                onCloseClick={() => setHoveredMarker(null)}
                options={{ disableAutoPan: true }}
              >
                <div style={{ fontSize: '0.82rem', padding: '2px 4px', lineHeight: 1.5 }}>
                  {hoveredMarker.isHub ? (
                    <>
                      <strong>{hoveredMarker.sport_name} Hub</strong>
                      <div>{hoveredMarker.city_name}, {hoveredMarker.state_code}</div>
                      <div>{hoveredMarker.sport_count} athletes · {Math.round((hoveredMarker.hub_pct ?? 0) * 100)}% of US total</div>
                      <div style={{ color: '#667eea' }}>{hoveredMarker.concentration_ratio}× national avg</div>
                    </>
                  ) : (
                    <>
                      <strong>
                        {hoveredMarker.match_level === 'state'
                          ? `${hoveredMarker.state_code} (state)`
                          : `${hoveredMarker.city_name}, ${hoveredMarker.state_code}`}
                      </strong>
                      <div>{hoveredMarker.total_athletes} athletes</div>
                    </>
                  )}
                </div>
              </InfoWindowF>
            )}

            {/* Click detail window */}
            {clickedMarker && (
              <InfoWindowF
                position={{
                  lat: clickedMarker.lat ?? clickedMarker.latitude,
                  lng: clickedMarker.lng ?? clickedMarker.longitude,
                }}
                onCloseClick={() => setClickedMarker(null)}
              >
                <div className="info-window-content">
                  {clickedMarker.isHub ? (
                    <>
                      <h4>{clickedMarker.sport_name} Hub</h4>
                      <p><strong>Location:</strong> {clickedMarker.city_name}, {clickedMarker.state_code}</p>
                      <p><strong>Athletes:</strong> {clickedMarker.sport_count} ({Math.round((clickedMarker.hub_pct ?? 0) * 100)}% of US total)</p>
                      <p><strong>Concentration:</strong> {clickedMarker.concentration_ratio}× national avg</p>
                      {onSelectHomtown && (
                        <button
                          className="view-details-btn"
                          onClick={() => {
                            onSelectHomtown(clickedMarker.hometown_id);
                            setClickedMarker(null);
                          }}
                        >
                          View City Story →
                        </button>
                      )}
                    </>
                  ) : (
                    <>
                      <h4>
                        {clickedMarker.match_level === 'state'
                          ? `${clickedMarker.state_code} (state-level)`
                          : `${clickedMarker.city_name}, ${clickedMarker.state_code}`}
                      </h4>
                      {clickedMarker.match_level === 'state' && (
                        <p style={{ fontSize: '0.8rem', color: '#f97316', marginBottom: 4 }}>
                          ⚠️ No city data — placed at state centre
                        </p>
                      )}
                      <p>
                        <strong>{isHeatmap ? 'Athletes (this sport):' : 'Athletes:'}</strong>{' '}
                        {clickedMarker.total_athletes}
                      </p>
                      {!isHeatmap && onSelectHomtown && (
                        <button
                          className="view-details-btn"
                          onClick={() => {
                            onSelectHomtown(clickedMarker.hometown_id);
                            setClickedMarker(null);
                          }}
                        >
                          View Details & Story →
                        </button>
                      )}
                    </>
                  )}
                </div>
              </InfoWindowF>
            )}
          </GoogleMap>
        )}

        {/* Sport Leaders Legend — bottom-left of map */}
        {isShowingHubs && uniqueSports.length > 0 && (() => {
          const summerSports = uniqueSports.filter(s => !WINTER_SPORTS.has(s));
          const winterSports = uniqueSports.filter(s => WINTER_SPORTS.has(s));
          return (
            <div className="hub-legend">
              <div className="hub-legend-header">
                <span className="hub-legend-title">Sport Hubs ({rank1Data.length})</span>
                <button
                  className="hub-legend-toggle"
                  onClick={() => setLegendOpen(o => !o)}
                  aria-label={legendOpen ? 'Collapse legend' : 'Expand legend'}
                >
                  {legendOpen ? '▼' : '▲'}
                </button>
              </div>

              {legendOpen && (
                <div className="hub-legend-body">
                  {summerSports.length > 0 && (
                    <div className="hub-legend-section">
                      <div className="hub-legend-section-title">☀️ Summer</div>
                      {summerSports.map(sport => (
                        <div key={sport} className="hub-legend-item">
                          <span className="hub-legend-dot" style={{ background: HUB_COLORS[uniqueSports.indexOf(sport) % HUB_COLORS.length] }} />
                          <span className="hub-legend-name">{sport}</span>
                        </div>
                      ))}
                    </div>
                  )}

                  {winterSports.length > 0 && (
                    <div className="hub-legend-section">
                      <div className="hub-legend-section-title">❄️ Winter</div>
                      {winterSports.map(sport => (
                        <div key={sport} className="hub-legend-item">
                          <span className="hub-legend-dot" style={{ background: HUB_COLORS[uniqueSports.indexOf(sport) % HUB_COLORS.length] }} />
                          <span className="hub-legend-name">{sport}</span>
                        </div>
                      ))}
                    </div>
                  )}

                  <div className="hub-legend-scale">
                    <div className="hub-legend-section-title">Circle Size = Athletes</div>
                    <div className="hub-scale-row">
                      <span className="hub-scale-dot" style={{ width: 7, height: 7 }} />
                      <span className="hub-scale-dot" style={{ width: 13, height: 13 }} />
                      <span className="hub-scale-dot" style={{ width: 20, height: 20 }} />
                      <span className="hub-scale-label">Few → Many</span>
                    </div>
                    <div className="hub-legend-section-title" style={{ marginTop: 8 }}>Shade = Concentration</div>
                    <div className="hub-scale-row">
                      <span className="hub-scale-dot" style={{ width: 13, height: 13, opacity: 0.40 }} />
                      <span className="hub-scale-dot" style={{ width: 13, height: 13, opacity: 0.65 }} />
                      <span className="hub-scale-dot" style={{ width: 13, height: 13, opacity: 0.95 }} />
                      <span className="hub-scale-label">Low → High</span>
                    </div>
                  </div>
                </div>
              )}
            </div>
          );
        })()}
      </div>

    </div>
  );
}
