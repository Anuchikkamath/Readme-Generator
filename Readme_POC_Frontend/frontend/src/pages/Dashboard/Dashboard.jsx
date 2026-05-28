import React, { useState, useEffect } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useSearchParams, useNavigate } from 'react-router-dom';
import { useAuth } from '../../contexts/AuthContext';
import { Search, Filter, Grid, List as ListIcon, RefreshCw, Plus } from 'lucide-react';
import Header from '../../components/Header/Header';
import ProjectCard from '../../components/ProjectCard/ProjectCard';
import Button from '../../components/Button/Button';
import { LoadingPage, LoadingSpinner } from '../../components/Loading/Loading';
import { getProjects, syncGmail } from '../../api/projects';

const Dashboard = () => {
    const [filter, setFilter] = useState('all'); // all, recent, archived, favorites
    const [searchQuery, setSearchQuery] = useState('');
    const queryClient = useQueryClient();
    const [searchParams, setSearchParams] = useSearchParams();
    const navigate = useNavigate();
    const { checkAuth } = useAuth();

    // Extract token and email from URL query parameters (from OAuth callback)
    useEffect(() => {
        const token = searchParams.get('token');
        const email = searchParams.get('email');
        
        if (token) {
            // Decode the token (it's URL-encoded from backend)
            const decodedToken = decodeURIComponent(token);
            // Store token in sessionStorage
            sessionStorage.setItem('access_token', decodedToken);
            console.log('[Dashboard] Token stored in sessionStorage:', {
                length: decodedToken.length,
                preview: decodedToken.substring(0, 20) + '...',
                firstChar: decodedToken[0]
            });
            
            // If email is provided in URL, store it immediately
            if (email) {
                const decodedEmail = decodeURIComponent(email);
                sessionStorage.setItem('user_email', decodedEmail);
                console.log('[Dashboard] Email stored in sessionStorage:', decodedEmail);
            }
            
            // Remove token and email from URL for security
            searchParams.delete('token');
            searchParams.delete('email');
            setSearchParams(searchParams, { replace: true });
            // Trigger AuthContext to re-check authentication with new token
            if (checkAuth) {
                console.log('[Dashboard] Triggering checkAuth after storing token');
                checkAuth();
            }
        }
    }, [searchParams, setSearchParams, checkAuth]);

    // Fetch projects
    const { data: projects = [], isLoading, error } = useQuery({
        queryKey: ['projects'],
        queryFn: getProjects,
    });

    // Sync mutation
    const syncMutation = useMutation({
        mutationFn: syncGmail,
        onSuccess: (data) => {
            console.log('[Dashboard] Sync completed:', data);
            // Invalidate projects query to refetch
            queryClient.invalidateQueries(['projects']);
            if (data?.status === 'up_to_date') {
                alert('Notes are already synced and up to date');
            } else {
                alert('Sync completed successfully!');
            }
            navigate('/dashboard', { replace: true });
        },
        onError: (err) => {
            console.error('[Dashboard] Sync failed:', err);
            // Check if it's an authentication error
            if (err.response?.status === 401) {
                console.warn('[Dashboard] Authentication error during sync');
                alert('Session expired. Please log in again.');
                // Don't manually redirect - let ProtectedRoute handle it
            } else {
                alert(`Failed to sync: ${err.response?.data?.detail || err.message || 'Unknown error'}`);
            }
        },
    });

    // Filter projects
    const filteredProjects = projects.filter(project => {
        // Search filter
        const matchesSearch = project.name?.toLowerCase().includes(searchQuery.toLowerCase()) ||
            project.description?.toLowerCase().includes(searchQuery.toLowerCase());

        // Category filter (mock logic since we don't have these fields yet)
        if (filter === 'recent') return matchesSearch && project.created_at; // Mock
        if (filter === 'favorites') return matchesSearch && false; // Mock
        if (filter === 'archived') return matchesSearch && false; // Mock

        return matchesSearch;
    });

    if (isLoading) return <LoadingPage />;

    return (
        <div className="min-h-screen bg-gray-50 pb-12">
            <Header />

            <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
                {/* Dashboard Header */}
                <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 mb-8">
                    <div>
                        <h1 className="text-2xl font-bold text-gray-900">Meeting READMEs</h1>
                        <p className="text-gray-500 text-sm mt-1">
                            Manage and access your AI-processed documentation.
                        </p>
                    </div>

                    <div className="flex items-center gap-3">
                        <div className="relative hidden md:block">
                            <input
                                type="text"
                                placeholder="Search projects..."
                                className="pl-10 pr-4 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent w-64"
                                value={searchQuery}
                                onChange={(e) => setSearchQuery(e.target.value)}
                            />
                            <Search className="absolute left-3 top-2.5 h-4 w-4 text-gray-400" />
                        </div>

                        <Button
                            onClick={() => syncMutation.mutate()}
                            isLoading={syncMutation.isPending}
                            className="whitespace-nowrap"
                        >
                            <RefreshCw className={`h-4 w-4 mr-2 ${syncMutation.isPending ? 'animate-spin' : ''}`} />
                            Sync Gmail Notes
                        </Button>
                    </div>
                </div>

                {/* Filters & Mobile Search */}
                <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4 mb-6">
                    <div className="flex space-x-1 bg-white p-1 rounded-lg border border-gray-200 shadow-sm overflow-x-auto max-w-full">
                        {[
                            { id: 'all', label: 'All Projects', icon: Grid },
                            { id: 'recent', label: 'Recent', icon: null },
                            { id: 'archived', label: 'Archived', icon: null },
                            { id: 'favorites', label: 'Favorites', icon: null },
                        ].map((tab) => (
                            <button
                                key={tab.id}
                                onClick={() => setFilter(tab.id)}
                                className={`flex items-center px-3 py-1.5 rounded-md text-sm font-medium transition-colors whitespace-nowrap ${filter === tab.id
                                        ? 'bg-blue-50 text-blue-600'
                                        : 'text-gray-600 hover:bg-gray-50'
                                    }`}
                            >
                                {tab.icon && <tab.icon className="h-4 w-4 mr-1.5" />}
                                {tab.label}
                            </button>
                        ))}
                    </div>

                    <div className="relative md:hidden w-full">
                        <input
                            type="text"
                            placeholder="Search..."
                            className="pl-10 pr-4 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 w-full"
                            value={searchQuery}
                            onChange={(e) => setSearchQuery(e.target.value)}
                        />
                        <Search className="absolute left-3 top-2.5 h-4 w-4 text-gray-400" />
                    </div>
                </div>

                {/* Error State */}
                {error && (
                    <div className="bg-red-50 border border-red-200 rounded-lg p-4 mb-8 text-red-700">
                        Error loading projects: {error.message}
                    </div>
                )}

                {/* Projects Grid */}
                {filteredProjects.length > 0 ? (
                    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6">
                        {filteredProjects.map((project) => (
                            <ProjectCard key={project.id} project={project} />
                        ))}
                    </div>
                ) : (
                    <div className="bg-white rounded-xl border border-dashed border-gray-300 p-12 text-center">
                        <div className="mx-auto h-12 w-12 bg-gray-100 rounded-full flex items-center justify-center mb-4">
                            <Search className="h-6 w-6 text-gray-400" />
                        </div>
                        <h3 className="text-lg font-medium text-gray-900">No projects found</h3>
                        <p className="mt-1 text-gray-500 max-w-sm mx-auto">
                            {searchQuery
                                ? `No projects match "${searchQuery}"`
                                : "Sync your Gmail to import project notes from your meetings."}
                        </p>
                        {!searchQuery && (
                            <Button
                                variant="outline"
                                className="mt-4"
                                onClick={() => syncMutation.mutate()}
                                isLoading={syncMutation.isPending}
                            >
                                Sync Now
                            </Button>
                        )}
                    </div>
                )}
            </main>
        </div>
    );
};

export default Dashboard;
