import React, { createContext, useContext, useState, useEffect } from 'react';
import { getCurrentUser, logoutUser } from '../api/auth';

const AuthContext = createContext(null);

export const AuthProvider = ({ children }) => {
    const [user, setUser] = useState(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);

    // Function to check authentication (can be called externally)
    const checkAuth = React.useCallback(async (retryCount = 0) => {
        // Check if token exists in sessionStorage
        const token = sessionStorage.getItem('access_token');
        if (!token) {
            console.log('[AuthContext] No token found in sessionStorage');
            setUser(null);
            setLoading(false);
            // Clear any stale email
            sessionStorage.removeItem('user_email');
            return;
        }

        try {
            console.log('[AuthContext] Checking authentication...', { retryCount, tokenPreview: token.substring(0, 20) + '...' });
            const userData = await getCurrentUser();
            console.log('[AuthContext] User authenticated:', userData);

            // Check if userData is null or invalid
            if (!userData) {
                console.error('[AuthContext] getCurrentUser returned null or undefined');
                throw new Error('User data is null');
            }

            // Ensure email exists in userData
            if (!userData.email) {
                console.warn('[AuthContext] User data missing email:', userData);
                // If we have email in sessionStorage, use it
                const storedEmail = sessionStorage.getItem('user_email');
                if (storedEmail) {
                    console.log('[AuthContext] Using stored email from sessionStorage:', storedEmail);
                    userData.email = storedEmail;
                } else {
                    throw new Error('User data missing email and no stored email found');
                }
            }

            setUser(userData);
            setLoading(false);
            // Store authentication indicators - CRITICAL: Always store email
            sessionStorage.setItem('auth_status', 'authenticated');
            if (userData.email) {
                sessionStorage.setItem('user_email', userData.email);
                console.log('[AuthContext] Email stored in sessionStorage:', userData.email);
            } else {
                console.warn('[AuthContext] No email to store in sessionStorage');
            }
        } catch (err) {
            console.error('[AuthContext] Auth check failed:', err);
            console.error('[AuthContext] Error details:', {
                status: err.response?.status,
                message: err.response?.data?.detail || err.message,
                headers: err.response?.headers
            });

            // If 401, token is invalid - clear it
            if (err.response?.status === 401) {
                console.log('[AuthContext] Token invalid (401) - clearing token');
                sessionStorage.removeItem('access_token');
                sessionStorage.removeItem('auth_status');
                sessionStorage.removeItem('user_email');
                setUser(null);
                setLoading(false);
            } else if (retryCount === 0) {
                // Retry once after a short delay (for network errors, etc.)
                console.log('[AuthContext] Retrying auth check in 500ms...');
                setTimeout(() => {
                    checkAuth(1);
                }, 500);
            } else {
                // Not authenticated or error after retry
                console.log('[AuthContext] User not authenticated after retry');
                setUser(null);
                setLoading(false);
                // Clear auth indicators
                sessionStorage.removeItem('auth_status');
                sessionStorage.removeItem('user_email');
            }
        }
    }, []);

    // Check if user is logged in on mount and when token changes
    useEffect(() => {
        checkAuth();
    }, [checkAuth]);

    // Listen for storage events (when token is set from another tab/window)
    useEffect(() => {
        const handleStorageChange = (e) => {
            if (e.key === 'access_token') {
                console.log('[AuthContext] Token changed in sessionStorage, re-checking auth');
                checkAuth();
            }
        };

        window.addEventListener('storage', handleStorageChange);
        return () => window.removeEventListener('storage', handleStorageChange);
    }, [checkAuth]);

    // Login function - redirects to Google OAuth
    const login = () => {
        // Redirect to backend login endpoint which handles Google OAuth
        window.location.href = `${import.meta.env.VITE_API_URL || 'http://localhost:8000'}/auth/login`;
    };

    // Logout function
    const logout = async () => {
        try {
            console.log('[AuthContext] Logging out user...');
            // Call backend logout endpoint
            await logoutUser();
            console.log('[AuthContext] Backend logout successful');
        } catch (err) {
            console.error('[AuthContext] Logout API call failed:', err);
            // Continue with local cleanup even if backend call fails
        } finally {
            // Always clear token and user state from sessionStorage
            console.log('[AuthContext] Clearing sessionStorage and user state');
            setUser(null);
            setLoading(false);
            
            // Clear all sessionStorage items related to authentication
            sessionStorage.removeItem('access_token');
            sessionStorage.removeItem('auth_status');
            sessionStorage.removeItem('user_email');
            
            // Verify all items are cleared
            const remainingToken = sessionStorage.getItem('access_token');
            if (remainingToken) {
                console.warn('[AuthContext] Warning: access_token still exists in sessionStorage after logout');
            } else {
                console.log('[AuthContext] All sessionStorage items cleared successfully');
            }
            
            // Redirect to login page
            console.log('[AuthContext] Redirecting to login page');
            window.location.href = '/';
        }
    };

    return (
        <AuthContext.Provider value={{ user, loading, error, login, logout, checkAuth }}>
            {children}
        </AuthContext.Provider>
    );
};

export const useAuth = () => {
    const context = useContext(AuthContext);
    if (!context) {
        throw new Error('useAuth must be used within an AuthProvider');
    }
    return context;
};
