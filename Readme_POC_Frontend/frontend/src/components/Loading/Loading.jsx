import React from 'react';
import { Loader2 } from 'lucide-react';

export const LoadingSpinner = ({ size = 'md', className = '' }) => {
    const sizes = {
        sm: 'h-4 w-4',
        md: 'h-8 w-8',
        lg: 'h-12 w-12',
        xl: 'h-16 w-16',
    };

    return (
        <div className={`flex justify-center items-center ${className}`}>
            <Loader2 className={`animate-spin text-blue-600 ${sizes[size]}`} />
        </div>
    );
};

export const LoadingPage = () => {
    return (
        <div className="flex items-center justify-center h-screen bg-gray-50">
            <div className="text-center">
                <LoadingSpinner size="xl" className="mb-4" />
                <p className="text-gray-500 font-medium">Loading...</p>
            </div>
        </div>
    );
};

export const Skeleton = ({ className = '' }) => {
    return (
        <div className={`animate-pulse bg-gray-200 rounded ${className}`}></div>
    );
};
