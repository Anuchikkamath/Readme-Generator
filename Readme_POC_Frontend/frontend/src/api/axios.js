import axios from 'axios';

const api = axios.create({
    baseURL: import.meta.env.VITE_API_URL || 'http://localhost:8000',
    headers: {
        'Content-Type': 'application/json',
    },
});

// Request interceptor to add token from sessionStorage to Authorization header
api.interceptors.request.use(
    (config) => {
        const token = sessionStorage.getItem('access_token');
        if (token) {
            config.headers.Authorization = `Bearer ${token}`;
            console.log('[Axios] Adding Authorization header:', {
                url: config.url,
                hasToken: !!token,
                tokenPreview: token.substring(0, 20) + '...'
            });
        } else {
            console.warn('[Axios] No token found in sessionStorage for request:', config.url);
        }
        return config;
    },
    (error) => {
        return Promise.reject(error);
    }
);

// Response interceptor for error handling
api.interceptors.response.use(
    (response) => response,
    (error) => {
        // Handle 401 Unauthorized - clear token and redirect to login
        if (error.response && error.response.status === 401) {
            console.warn('[Axios] 401 Unauthorized - clearing token');
            sessionStorage.removeItem('access_token');
            sessionStorage.removeItem('auth_status');
            sessionStorage.removeItem('user_email');
            // Redirect to login if not already there
            if (window.location.pathname !== '/') {
                window.location.href = '/';
            }
        }
        return Promise.reject(error);
    }
);

export default api;
