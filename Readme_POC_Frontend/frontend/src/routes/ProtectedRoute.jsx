import React, { useEffect } from 'react';
import { Navigate, Outlet, useSearchParams } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';

const ProtectedRoute = () => {
    const { user, loading, checkAuth } = useAuth();
    const [searchParams] = useSearchParams();

    // Check for token in sessionStorage as fallback
    const token = sessionStorage.getItem('access_token');
    
    // Also check for token and email in URL (in case user is redirected here directly)
    useEffect(() => {
        const urlToken = searchParams.get('token');
        const urlEmail = searchParams.get('email');
        
        if (urlToken) {
            // Decode and store token
            const decodedToken = decodeURIComponent(urlToken);
            sessionStorage.setItem('access_token', decodedToken);
            console.log('[ProtectedRoute] Token extracted from URL and stored in sessionStorage');
            
            // If email is provided in URL, store it immediately
            if (urlEmail) {
                const decodedEmail = decodeURIComponent(urlEmail);
                sessionStorage.setItem('user_email', decodedEmail);
                console.log('[ProtectedRoute] Email extracted from URL and stored:', decodedEmail);
            }
            
            // Remove token and email from URL
            searchParams.delete('token');
            searchParams.delete('email');
            // Trigger auth check
            if (checkAuth) {
                checkAuth();
            }
        }
    }, [searchParams, checkAuth]);

    if (loading) {
        // You can replace this with a proper loading spinner component later
        return (
            <div className="flex items-center justify-center h-screen">
                <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
            </div>
        );
    }

    // Protect route if no user and no token
    if (!user && !token) {
        return <Navigate to="/" replace />;
    }

    return <Outlet />;
};

export default ProtectedRoute;
