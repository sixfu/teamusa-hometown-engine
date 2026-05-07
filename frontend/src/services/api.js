import axios from 'axios';

const API_BASE = process.env.REACT_APP_API_BASE || 'https://team-usa-api-456111731385.us-central1.run.app/api';

export const getHometowns = async (mode = 'olympic') => {
  try {
    const response = await axios.get(`${API_BASE}/hometowns`, { params: { mode } });
    return response.data.data;
  } catch (error) {
    console.error('Error fetching hometowns:', error);
    throw error;
  }
};

export const getHometownsByState = async (mode = 'olympic') => {
  try {
    const response = await axios.get(`${API_BASE}/hometowns/by-state`, { params: { mode } });
    return response.data.data;
  } catch (error) {
    console.error('Error fetching hometowns by state:', error);
    throw error;
  }
};

export const searchHometowns = async (cityName, stateCode, mode = 'olympic') => {
  try {
    const params = { mode };
    if (cityName) params.city_name = cityName;
    if (stateCode) params.state_code = stateCode;
    const response = await axios.get(`${API_BASE}/hometowns/search`, { params });
    return response.data.data;
  } catch (error) {
    console.error('Error searching hometowns:', error);
    throw error;
  }
};

export const getSports = async (mode = 'olympic') => {
  try {
    const response = await axios.get(`${API_BASE}/sports`, { params: { mode } });
    return response.data.data;
  } catch (error) {
    console.error('Error fetching sports:', error);
    throw error;
  }
};

export const getHomtownDetail = async (hometownId, mode = 'olympic') => {
  try {
    const response = await axios.get(`${API_BASE}/hometown/${hometownId}`, { params: { mode } });
    return response.data.data;
  } catch (error) {
    console.error('Error fetching hometown detail:', error);
    throw error;
  }
};

export const getSportConcentration = async (cityName, stateCode, mode = 'olympic') => {
  const params = { mode };
  if (cityName) params.city_name = cityName;
  if (stateCode) params.state_code = stateCode;
  const response = await axios.get(`${API_BASE}/region/sport-concentration`, { params });
  return response.data.data;
};

export const getSportYearCounts = async (sportName, mode = 'olympic') => {
  const response = await axios.get(`${API_BASE}/sports/year-counts`, {
    params: { sport_name: sportName, mode },
  });
  return response.data.data;
};

export const getSportHeatmap = async (sportName, mode = 'olympic') => {
  const response = await axios.get(`${API_BASE}/sports/heatmap`, {
    params: { sport_name: sportName, mode }
  });
  return response.data.data;
};

export const compareRegions = async (city1, state1, city2, state2, mode = 'olympic') => {
  const params = { mode };
  if (city1)  params.city1  = city1;
  if (state1) params.state1 = state1;
  if (city2)  params.city2  = city2;
  if (state2) params.state2 = state2;
  const response = await axios.get(`${API_BASE}/compare`, { params });
  return response.data.data;
};

export const getSportHeatmapDescription = async (sportName, mode = 'olympic') => {
  const response = await axios.get(`${API_BASE}/sport/heatmap-description`, {
    params: { sport_name: sportName, mode },
  });
  return response.data.data;
};

export const getSportAnimation = async (sportName, mode = 'olympic') => {
  const response = await axios.get(`${API_BASE}/sport/animation`, {
    params: { sport_name: sportName, mode },
  });
  return response.data.data;
};

export const getSportHubs = async (mode = 'olympic') => {
  const response = await axios.get(`${API_BASE}/sports/hubs`, {
    params: { mode },
  });
  return response.data.data;
};

export const getRank1Cities = async (mode = 'olympic') => {
  const response = await axios.get(`${API_BASE}/sports/rank1-cities`, {
    params: { mode },
  });
  return response.data.data;
};

export const getMapObservation = async (mode = 'olympic') => {
  const response = await axios.get(`${API_BASE}/hometowns/observation`, {
    params: { mode },
  });
  return response.data.data;
};

export const getMapObservationFromList = async (hometowns, totalAthletes, mode = 'olympic') => {
  const response = await axios.post(`${API_BASE}/hometowns/observation`, {
    hometowns,
    total_athletes: totalAthletes,
    mode,
  });
  return response.data.data;
};

export const queryAgent = async (question, includeParalympics = true, history = []) => {
  const response = await axios.post(`${API_BASE}/agent/query`, {
    question,
    include_paralympics: includeParalympics,
    history,
  });
  return response.data.data;
};

export const findMatchedSports = async ({ height, weight, birth_city, birth_state } = {}) => {
  const body = {};
  if (height !== undefined && height !== '') body.height = Number(height);
  if (weight !== undefined && weight !== '') body.weight = Number(weight);
  if (birth_city) body.birth_city = birth_city;
  if (birth_state) body.birth_state = birth_state;
  const response = await axios.post(`${API_BASE}/find-matched-sports`, body);
  return response.data.data;
};

export const healthCheck = async () => {
  try {
    const response = await axios.get(`http://localhost:5000/health`);
    return response.data;
  } catch (error) {
    console.error('Health check failed:', error);
    throw error;
  }
};
