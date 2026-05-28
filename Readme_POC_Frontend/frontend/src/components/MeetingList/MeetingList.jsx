import React from 'react';
import { format } from 'date-fns';
import { Clock, Users, Calendar, CheckCircle2, Circle } from 'lucide-react';

const MeetingList = ({ meetings = [], selectedIds = [], onToggleSelection }) => {
    if (!meetings.length) {
        return (
            <div className="p-8 text-center text-gray-500">
                <p>No meetings found for this project.</p>
            </div>
        );
    }

    return (
        <div className="divide-y divide-gray-100">
            {meetings.map((meeting) => {
                const isSelected = selectedIds.includes(meeting.id);
                const meetingDate = meeting.date ? new Date(meeting.date) : new Date();

                return (
                    <div
                        key={meeting.id}
                        className={`p-4 hover:bg-slate-50 transition-colors cursor-pointer group ${isSelected ? 'bg-blue-50/50 hover:bg-blue-50' : ''
                            }`}
                        onClick={() => onToggleSelection(meeting.id)}
                    >
                        <div className="flex items-start gap-3">
                            <div className="mt-1 text-gray-400 group-hover:text-blue-600 transition-colors">
                                {isSelected ? (
                                    <CheckCircle2 className="h-5 w-5 text-blue-600" />
                                ) : (
                                    <Circle className="h-5 w-5" />
                                )}
                            </div>

                            <div className="flex-1 min-w-0">
                                <h4 className={`font-medium text-sm mb-1 truncate ${isSelected ? 'text-blue-900' : 'text-gray-900'
                                    }`}>
                                    {meeting.title || 'Untitled Meeting'}
                                </h4>

                                <div className="flex flex-wrap gap-x-4 gap-y-1 text-xs text-gray-500">
                                    <div className="flex items-center gap-1">
                                        <Calendar className="h-3 w-3" />
                                        <span>{format(meetingDate, 'MMM d, yyyy')}</span>
                                    </div>
                                </div>

                            </div>
                        </div>
                    </div>
                );
            })}
        </div>
    );
};

export default MeetingList;
