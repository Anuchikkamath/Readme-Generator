import React, { useEffect, useState } from 'react';
import { useAuth } from '../../contexts/AuthContext';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { FileText, AlertCircle } from 'lucide-react';
import Button from '../../components/Button/Button';

const Login = () => {
    const { user, login, loading, checkAuth } = useAuth();
    const navigate = useNavigate();
    const [searchParams] = useSearchParams();
    const [error, setError] = useState(null);

    // Extract token and email from URL if present (from OAuth callback)
    // This handles the case where user is redirected to /dashboard?token=... but ends up on / first
    useEffect(() => {
        const token = searchParams.get('token');
        const email = searchParams.get('email');
        
        if (token) {
            // Decode and store token
            const decodedToken = decodeURIComponent(token);
            sessionStorage.setItem('access_token', decodedToken);
            console.log('[Login] Token extracted from URL and stored in sessionStorage:', {
                length: decodedToken.length,
                preview: decodedToken.substring(0, 20) + '...'
            });
            
            // If email is provided in URL, store it immediately
            if (email) {
                const decodedEmail = decodeURIComponent(email);
                sessionStorage.setItem('user_email', decodedEmail);
                console.log('[Login] Email extracted from URL and stored:', decodedEmail);
            }
            
            // Remove token and email from URL
            searchParams.delete('token');
            searchParams.delete('email');
            // Update URL without token
            navigate('/dashboard', { replace: true });
            // Trigger auth check
            if (checkAuth) {
                checkAuth();
            }
            return;
        }
    }, [searchParams, navigate, checkAuth]);

    // Redirect if already logged in (check both user state and token)
    useEffect(() => {
        const token = sessionStorage.getItem('access_token');
        if ((user || token) && !loading) {
            navigate('/dashboard');
        }
    }, [user, loading, navigate]);

    // Handle URL errors
    useEffect(() => {
        const errorParam = searchParams.get('error');
        if (errorParam) {
            setError('Authentication failed. Please try again.');
        }
    }, [searchParams]);

    const handleGoogleAuth = () => {
        login();
    };

    if (loading) {
        return null;
    }

    return (
        <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100 flex flex-col items-center justify-center p-4">
            <div className="bg-white rounded-2xl shadow-xl max-w-md w-full overflow-hidden">
                <div className="p-8">
                    {/* Logo & Header */}
                    <div className="text-center mb-8">
                        <div className="flex justify-center mb-4">
                            <div className="bg-blue-600 p-3 rounded-xl shadow-lg shadow-blue-200">
                                <FileText className="h-8 w-8 text-white" />
                            </div>
                        </div>
                        <h1 className="text-2xl font-bold text-gray-900 mb-1">
                            Welcome Back
                        </h1>
                        <p className="text-sm text-gray-500">
                            Sign in with Google to access your dashboard
                        </p>
                    </div>

                    {/* Error Message */}
                    {error && (
                        <div className="mb-6 p-3 bg-red-50 border border-red-100 rounded-lg flex items-center gap-2 text-sm text-red-600 text-left animate-in fade-in slide-in-from-top-2">
                            <AlertCircle className="h-4 w-4 flex-shrink-0" />
                            <span>{error}</span>
                        </div>
                    )}

                    {/* Google Auth Button */}
                    <Button
                        onClick={handleGoogleAuth}
                        variant="outline"
                        className="w-full flex items-center justify-center gap-3 py-2.5 bg-white border-gray-300 hover:bg-gray-50 text-gray-700 shadow-sm transition-all hover:shadow-md"
                    >
                        <img
                            src="https://www.google.com/favicon.ico"
                            alt="Google"
                            className="w-5 h-5"
                        />
                        <span className="font-medium text-gray-700">
                            Continue with Google
                        </span>
                    </Button>
                </div>

                {/* Decorative Footer */}
                <div className="h-1.5 bg-gradient-to-r from-blue-600 to-indigo-600 opacity-90"></div>
            </div>

            <div className="mt-8 text-center text-xs text-gray-500">
                <div className="flex items-center justify-center gap-2 mb-2">
                    <span>Internal Tool</span>
                    <span className="w-1 h-1 bg-gray-400 rounded-full"></span>
                    <span>© 2026 Company Name</span>
                </div>
            </div>
        </div>
    );
};

export default Login;
