import api from './axios';

// Get current user info (protected route)
export const getCurrentUser = async () => {
    const response = await api.get('/auth/me');
    return response.data;
};

// Logout user
export const logoutUser = async () => {
    const response = await api.post('/auth/logout');
    return response.data;
};

// Check health of auth service
export const checkAuthHealth = async () => {
    const response = await api.get('/auth/health');
    return response.data;
};
