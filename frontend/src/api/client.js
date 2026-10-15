import axios from 'axios';

const configuredBaseUrl = import.meta.env.VITE_API_BASE_URL?.trim();

if (import.meta.env.PROD && !configuredBaseUrl) {
  throw new Error('VITE_API_BASE_URL must be configured for production builds.');
}

// Local development may use the local FastAPI server; production must be explicit.
const BASE_URL = configuredBaseUrl || 'http://localhost:8000';
const API_PREFIX = '/api/v1';

export const apiClient = axios.create({
  baseURL: `${BASE_URL}${API_PREFIX}`,
  headers: {
    'Content-Type': 'application/json',
  },
  timeout: 15000,
});

// Request interceptor: attach JWT bearer token
apiClient.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('token');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => Promise.reject(error)
);

// Response interceptor: handle 401 unauthenticated automatically
apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response && error.response.status === 401) {
      // Discard invalid / expired auth state
      localStorage.removeItem('token');
      localStorage.removeItem('user');
      localStorage.removeItem('refresh_token');
      window.dispatchEvent(new Event('auth:unauthorized'));
    }
    return Promise.reject(error);
  }
);

// Format API errors into human-readable strings
export const getErrorMessage = (error) => {
  if (error.response?.data?.detail) {
    const detail = error.response.data.detail;
    if (Array.isArray(detail)) {
      return detail.map((err) => `${err.loc?.slice(-1)[0] || 'Field'}: ${err.msg}`).join('; ');
    }
    return typeof detail === 'string' ? detail : JSON.stringify(detail);
  }
  if (!error.response && (error.request || error.code === 'ERR_NETWORK' || error.message === 'Network Error')) {
    return 'Cannot get a response from the server. It may be starting up, unreachable, blocked by CORS, '
      + 'or it hit an internal error. Please retry in a moment; if this persists, contact the administrator.';
  }
  if (error.code === 'ECONNABORTED') {
    return 'The server took too long to respond. It may be waking up; please retry.';
  }
  return error.message || 'An unexpected error occurred. Please try again.';
};

export default apiClient;
