import React from 'react';
import { Calendar, Clock, MoreVertical, FileText } from 'lucide-react';
import { format } from 'date-fns';
import { Link } from 'react-router-dom';

const ProjectCard = ({ project }) => {
    // Format date safely
    const formattedDate = project.created_at
        ? format(new Date(project.created_at), 'MMM d, yyyy')
        : 'Unknown date';

    return (
        <div className="bg-white rounded-xl border border-gray-200 shadow-sm hover:shadow-md transition-all duration-200 group overflow-hidden flex flex-col h-full">
            {/* Card Header / Thumbnail placeholder */}
            <div className="h-32 bg-gradient-to-br from-blue-50 to-indigo-50 border-b border-gray-100 flex items-center justify-center relative">
                <div className="bg-white p-3 rounded-xl shadow-sm">
                    <FileText className="h-8 w-8 text-blue-600" />
                </div>

                {/* Read Status Badge (Mock) */}
                {project.is_new && (
                    <span className="absolute top-3 right-3 bg-blue-600 text-white text-[10px] font-bold px-2 py-1 rounded uppercase tracking-wider">
                        New
                    </span>
                )}
            </div>

            <div className="p-5 flex flex-col flex-grow">
                <div className="flex justify-between items-start mb-2">
                    <Link to={`/projects/${project.id}`} className="block group-hover:text-blue-600 transition-colors">
                        <h3 className="font-semibold text-lg text-gray-900 line-clamp-1">
                            {project.name || 'Untitled Project'}
                        </h3>
                    </Link>

                    <button className="text-gray-400 hover:text-gray-600 p-1 rounded-full hover:bg-gray-100 transition-colors">
                        <MoreVertical className="h-4 w-4" />
                    </button>
                </div>

                {/* Project Meta */}
                <div className="flex items-center gap-4 text-xs text-gray-500 mb-4">
                    <div className="flex items-center gap-1.5">
                        <Calendar className="h-3.5 w-3.5" />
                        <span>{formattedDate}</span>
                    </div>
                    <div className="flex items-center gap-1.5">
                        <Clock className="h-3.5 w-3.5" />
                        <span>{project.read_time || '5 min read'}</span>
                    </div>
                </div>

                {/* Description / Summary */}
                <p className="text-sm text-gray-600 line-clamp-3 mb-4 flex-grow">
                    {project.description || 'Comprehensive README generated from the quarterly planning session. Covers market expansion targets, product roadmaps, and key OKRs.'}
                </p>

                {/* Footer Actions */}
                <div className="mt-auto pt-4 border-t border-gray-50 flex items-center justify-between">
                    <Link
                        to={`/projects/${project.id}`}
                        className="text-sm font-medium text-blue-600 hover:text-blue-700"
                    >
                        View Details
                    </Link>

                    {project.source === 'gmail' && (
                        <span className="text-[10px] font-medium text-gray-400 bg-gray-100 px-2 py-0.5 rounded-full">
                            GMAIL SOURCE
                        </span>
                    )}
                </div>
            </div>
        </div>
    );
};

export default ProjectCard;
