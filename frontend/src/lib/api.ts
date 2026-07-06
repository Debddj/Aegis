import axios from 'axios';

const API_URL = 'http://localhost:8000';

const client = axios.create({
  baseURL: API_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

export const api = {
  // Metrics API
  getMetricsSummary: async () => {
    const res = await client.get('/metrics/summary');
    return res.data;
  },
  getMetricsHistory: async (limit = 30) => {
    const res = await client.get(`/metrics/history?limit=${limit}`);
    return res.data;
  },
  takeSnapshot: async () => {
    const res = await client.get('/metrics/snapshot');
    return res.data;
  },
  
  // Incidents API
  listIncidents: async (status?: string) => {
    const url = status ? `/incidents/?status=${status}` : '/incidents/';
    const res = await client.get(url);
    return res.data;
  },
  getIncidentDetail: async (id: string) => {
    const res = await client.get(`/incidents/${id}`);
    return res.data;
  },
  
  // Agents & Scenarios API
  triggerScenario: async (scenario: string) => {
    const res = await client.post('/agents/trigger', { scenario });
    return res.data;
  },
  listApprovals: async () => {
    const res = await client.get('/agents/approvals');
    return res.data;
  },
  approveAction: async (incidentId: string, approved: boolean, operator = 'operator_console') => {
    const res = await client.post(`/agents/approve/${incidentId}`, {
      approved,
      resolved_by: operator,
    }, {
      headers: {
        Authorization: 'Bearer aegis-secure-token-2026',
      }
    });
    return res.data;
  },
  getAgentStatus: async () => {
    const res = await client.get('/agents/status');
    return res.data;
  },
};
