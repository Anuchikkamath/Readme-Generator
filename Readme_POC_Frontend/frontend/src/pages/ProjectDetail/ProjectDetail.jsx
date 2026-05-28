import React, { useState } from 'react';
import { useParams } from 'react-router-dom';
import { useQuery, useMutation } from '@tanstack/react-query';
import { format } from 'date-fns';
import {
    FileText, Sparkles, Copy, Download, ChevronLeft,
    MessageSquare, User, Calendar, Clock
} from 'lucide-react';
import Header from '../../components/Header/Header';
import Button from '../../components/Button/Button';
import MeetingList from '../../components/MeetingList/MeetingList';
import { LoadingPage } from '../../components/Loading/Loading';
// We'll need a way to fetch single project details - for now using getProjects and filtering
import { getProjectDetails, generateReadme } from '../../api/projects'; // Import updated API
import { Link, useNavigate } from 'react-router-dom';

const ProjectDetail = () => {
    const { projectId } = useParams();
    const navigate = useNavigate();
    const [selectedMeetingIds, setSelectedMeetingIds] = useState([]);

    // Fetch project details (Real Data)
    const { data: project, isLoading, error } = useQuery({
        queryKey: ['project', projectId],
        queryFn: () => getProjectDetails(projectId),
        enabled: !!projectId, // Only run if we have an ID
    });

    // Handle Mock/Real Data Mapping
    const meetings = project?.meetings?.map(m => ({
        ...m,
        // Ensure transcript is an array or constructed from text fields
        transcript: Array.isArray(m.transcript) ? m.transcript :
            (m.summary ? [{ time: '00:00', speaker: 'Summary', text: m.summary }] :
                (m.raw_content ? [{ time: '00:00', speaker: 'Raw Note', text: m.raw_content }] : []))
    })) || [];

    const [generatingType, setGeneratingType] = useState(null); // 'all' or 'selected'

    // Generate README mutation
    const generateMutation = useMutation({
        mutationFn: (data) => generateReadme(data.projectId, data.startDate, data.endDate, data.meetingIds),
        onSuccess: (data) => {
            // Navigate to README viewer with the result content directly
            navigate(`/readme/${projectId}`, {
                state: {
                    content: data.readme_content,
                    readmeId: data.readme_id
                }
            });
        },
        onError: (err) => {
            alert('Failed to generate README: ' + err.message);
        },
        onSettled: () => {
            setGeneratingType(null);
        }
    });

    const handleToggleSelection = (id) => {
        setSelectedMeetingIds(prev =>
            prev.includes(id) ? prev.filter(i => i !== id) : [...prev, id]
        );
    };

    const handleGenerate = (useSelection = false) => {
        // If "Generate Selected" is clicked but nothing selected, warn user
        if (useSelection && selectedMeetingIds.length === 0) {
            alert("Please select at least one meeting to generate a README.");
            return;
        }

        setGeneratingType(useSelection ? 'selected' : 'all');

        generateMutation.mutate({
            projectId,
            startDate: null, // Let backend handle logic using IDs
            endDate: null,
            meetingIds: useSelection ? selectedMeetingIds : null
        });
    };

    if (isLoading) return <LoadingPage />;
    if (!project) return <div className="p-8 text-center">Project not found</div>;

    const activeMeeting = meetings.find(m => selectedMeetingIds.includes(m.id)) || meetings[0];

    return (
        <div className="min-h-screen bg-gray-50 flex flex-col">
            <Header />

            {/* Breadcrumb / Back Navigation */}
            <div className="bg-white border-b border-gray-200 px-4 py-3 sm:px-6 lg:px-8">
                <div className="max-w-7xl mx-auto flex items-center gap-2 text-sm">
                    <Link to="/dashboard" className="text-gray-500 hover:text-gray-900 flex items-center gap-1">
                        <ChevronLeft className="h-4 w-4" />
                        Back to Projects
                    </Link>
                    <span className="text-gray-300">/</span>
                    <span className="font-medium text-gray-900 flex items-center gap-2">
                        <span className="w-2 h-2 rounded-full bg-green-500"></span>
                        {project?.name}
                    </span>
                    <span className="px-2 py-0.5 rounded bg-gray-100 text-xs font-mono text-gray-600">
                        Source: {project?.source || 'Gmail'}
                    </span>
                </div>
            </div>

            <div className="flex-1 max-w-7xl w-full mx-auto p-4 sm:p-6 lg:p-8 flex flex-col lg:flex-row gap-6 overflow-hidden max-h-[calc(100vh-64px-45px)]">

                {/* Sidebar: Available Meetings */}
                <div className="w-full lg:w-80 flex flex-col bg-white rounded-xl border border-gray-200 shadow-sm overflow-hidden flex-shrink-0">
                    <div className="p-4 border-b border-gray-100 bg-gray-50 flex justify-between items-center">
                        <h3 className="font-semibold text-gray-900">Available Meetings</h3>
                        <span className="text-xs font-medium text-gray-500">{meetings.length} notes found</span>
                    </div>

                    <div className="overflow-y-auto flex-1">
                        <MeetingList
                            meetings={meetings}
                            selectedIds={selectedMeetingIds}
                            onToggleSelection={handleToggleSelection}
                        />
                    </div>
                </div>

                {/* Main Content: Meeting Transcript & Actions */}
                <div className="flex-1 flex flex-col bg-white rounded-xl border border-gray-200 shadow-sm overflow-hidden">
                    {/* Header */}
                    <div className="p-6 border-b border-gray-100 flex justify-between items-start">
                        <div>
                            <div className="flex items-center gap-2 text-gray-500 text-sm mb-1">
                                <FileText className="h-4 w-4" />
                                <span>Raw Meeting Notes: {format(new Date(activeMeeting.date), 'MMM d, yyyy')}</span>
                            </div>
                            <h2 className="text-xl font-bold text-gray-900">{activeMeeting.title}</h2>
                        </div>

                        <div className="flex gap-2">
                            <Button variant="outline" size="sm" className="text-gray-600">
                                <Copy className="h-4 w-4 mr-1.5" />
                                Copy Raw Text
                            </Button>
                            <Button variant="outline" size="sm" className="text-gray-600">
                                <Download className="h-4 w-4 mr-1.5" />
                                Export JSON
                            </Button>
                        </div>
                    </div>

                    {/* Transcript View */}
                    <div className="flex-1 overflow-y-auto p-6 bg-slate-50/50">
                        {activeMeeting.transcript ? (
                            <div className="max-w-3xl mx-auto space-y-6">
                                <div className="bg-blue-50 border border-blue-100 rounded-lg p-4 mb-6">
                                    <h4 className="text-blue-900 font-semibold mb-2 flex items-center gap-2">
                                        <Sparkles className="h-4 w-4" />
                                        Transcript Snippets
                                    </h4>
                                    <p className="text-sm text-blue-700">
                                        Automatic extraction from Google Meet. Verify content before generating README.
                                    </p>
                                </div>

                                {activeMeeting.transcript.map((item, idx) => (
                                    <div key={idx} className="flex gap-4 group">
                                        <div className="w-16 text-xs text-gray-400 font-mono pt-1 text-right flex-shrink-0 select-none">
                                            {item.time}
                                        </div>
                                        <div>
                                            <div className="text-sm font-semibold text-gray-900 mb-0.5 flex items-center gap-2">
                                                {item.speaker}
                                            </div>
                                            <p className="text-gray-700 leading-relaxed bg-white p-3 rounded-lg border border-transparent group-hover:border-gray-200 shadow-sm group-hover:shadow transition-all">
                                                {item.text}
                                            </p>
                                        </div>
                                    </div>
                                ))}
                            </div>
                        ) : (
                            <div className="flex flex-col items-center justify-center h-full text-gray-400">
                                <MessageSquare className="h-12 w-12 mb-2 opacity-50" />
                                <p>Select a meeting to view details</p>
                            </div>
                        )}
                    </div>

                    {/* Footer Metadata & Main Action */}
                    <div className="p-6 border-t border-gray-100 bg-white">
                        <div className="flex flex-col sm:flex-row justify-between items-end gap-4">

                            <div className="flex gap-3 w-full sm:w-auto">
                                <Button
                                    className="flex-1 sm:flex-none"
                                    onClick={() => handleGenerate(false)}
                                    isLoading={generatingType === 'all'}
                                    disabled={generatingType === 'selected'}
                                >
                                    <Sparkles className="h-4 w-4 mr-2" />
                                    Generate Combined README
                                </Button>
                                <Button
                                    className="flex-1 sm:flex-none bg-blue-500 hover:bg-blue-600"
                                    onClick={() => handleGenerate(true)}
                                    isLoading={generatingType === 'selected'}
                                    disabled={generatingType === 'all' || selectedMeetingIds.length === 0}
                                    title={selectedMeetingIds.length === 0 ? "Select meetings first" : "Generate for selected meetings"}
                                >
                                    <Sparkles className="h-4 w-4 mr-2" />
                                    Generate Selected ({selectedMeetingIds.length})
                                </Button>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    );
};

export default ProjectDetail;
