import React from 'react';
import { useAuth } from '../../contexts/AuthContext';
import { LogOut, User, FileText } from 'lucide-react';
import Button from '../Button/Button';
import { Link } from 'react-router-dom';

const Header = () => {
    const { user, logout, loading } = useAuth();
    
    // Check if user is authenticated (either user object exists or token exists)
    const token = sessionStorage.getItem('access_token');
    const storedEmail = sessionStorage.getItem('user_email');
    const isAuthenticated = user || token;
    
    // Get user email - prefer from user object, fallback to sessionStorage
    // Only use storedEmail if user object is not available yet (during loading)
    const userEmail = user?.email || (loading ? null : storedEmail) || '';
    
    // Display name: show user's name if available
    const displayName = user?.name;
    // Always show email as the primary identifier
    const userInitial = userEmail ? (userEmail[0] || 'U').toUpperCase() : 'U';
    
    // Only show user info when we have email (either from user object or sessionStorage)
    // Wait for loading to complete before showing
    const shouldShowUserInfo = isAuthenticated && !loading && userEmail;

    return (
        <header className="bg-white border-b border-gray-200 sticky top-0 z-50">
            <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
                <div className="flex justify-between items-center h-16">
                    {/* Logo */}
                    <div className="flex items-center">
                        <Link to="/dashboard" className="flex items-center gap-2">
                            <div className="bg-blue-600 p-1.5 rounded-lg">
                                <FileText className="h-5 w-5 text-white" />
                            </div>
                            <span className="font-bold text-xl text-gray-900">README Generator</span>
                        </Link>
                    </div>

                    {/* User Profile & Actions */}
                    <div className="flex items-center gap-4">
                        {isAuthenticated && (
                            <>
                                {loading ? (
                                    // Show loading state while fetching user data
                                    <div className="flex items-center gap-2">
                                        <div className="h-4 w-4 border-2 border-blue-600 border-t-transparent rounded-full animate-spin"></div>
                                        <span className="text-sm text-gray-500">Loading...</span>
                                    </div>
                                ) : shouldShowUserInfo ? (
                                    <>
                                        {/* User Info - Show email when available */}
                                        <div className="flex flex-col items-end mr-2">
                                            {/* Show name if available */}
                                            {displayName && (
                                                <span className="text-sm font-medium text-gray-900">
                                                    {displayName}
                                                </span>
                                            )}
                                            {/* Always show email address */}
                                            <span className={`${displayName ? 'text-xs text-gray-500' : 'text-sm font-medium text-gray-900'}`}>
                                                {userEmail}
                                            </span>
                                        </div>

                                        {/* User Avatar */}
                                        <div className="h-8 w-8 rounded-full bg-blue-100 flex items-center justify-center border border-blue-200 text-blue-700 font-medium">
                                            {user?.picture ? (
                                                <img
                                                    src={user.picture}
                                                    alt={userEmail || 'User'}
                                                    className="h-8 w-8 rounded-full object-cover"
                                                />
                                            ) : (
                                                userInitial
                                            )}
                                        </div>

                                        {/* Divider */}
                                        <div className="h-6 w-px bg-gray-200 mx-2"></div>
                                    </>
                                ) : null}

                                {/* Logout Button - Show if authenticated (even during loading) */}
                                {!loading && (
                                    <Button
                                        variant="ghost"
                                        size="sm"
                                        onClick={logout}
                                        className="text-gray-500 hover:text-red-600 flex items-center gap-2"
                                        title="Sign out"
                                    >
                                        <LogOut className="h-4 w-4" />
                                        <span className="hidden sm:inline">Logout</span>
                                    </Button>
                                )}
                            </>
                        )}
                    </div>
                </div>
            </div>
        </header>
    );
};

export default Header;
