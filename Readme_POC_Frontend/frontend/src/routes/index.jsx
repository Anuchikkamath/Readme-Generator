import React from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import ProtectedRoute from './ProtectedRoute';
import Login from '../pages/Login/Login';
import Dashboard from '../pages/Dashboard/Dashboard';
import ProjectDetail from '../pages/ProjectDetail/ProjectDetail';
import ReadmeViewer from '../pages/ReadmeViewer/ReadmeViewer';
import VisualChartViewer from '../pages/VisualChartViewer/VisualChartViewer';
import FolderStructureViewer from '../pages/FolderStructureViewer/FolderStructureViewer';

const AppRoutes = () => {
    return (
        <BrowserRouter>
            <Routes>
                {/* Public Routes */}
                <Route path="/" element={<Login />} />

                {/* Protected Routes */}
                <Route element={<ProtectedRoute />}>
                    <Route path="/dashboard" element={<Dashboard />} />
                    <Route path="/projects/:projectId" element={<ProjectDetail />} />
                    <Route path="/readme/:projectId" element={<ReadmeViewer />} />
                    <Route path="/readme/:projectId/visual-chart" element={<VisualChartViewer />} />
                    <Route path="/readme/:projectId/folder-structure" element={<FolderStructureViewer />} />
                </Route>

                {/* Fallback */}
                <Route path="*" element={<Navigate to="/" replace />} />
            </Routes>
        </BrowserRouter>
    );
};

export default AppRoutes;
