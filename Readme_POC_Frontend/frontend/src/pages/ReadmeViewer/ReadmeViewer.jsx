import React, { useState } from 'react';
import { useParams, Link, useLocation, useNavigate } from 'react-router-dom';
import {
    ChevronLeft, Copy, Download, FileText,
    List, Sparkles
} from 'lucide-react';
import Header from '../../components/Header/Header';
import Button from '../../components/Button/Button';

// Simple Markdown Parser (for visualization only, real app would use remark/rehype)
const MarkdownViewer = ({ content }) => {
    // Use provided content or fallback (but we should have content from navigation)
    const text = content || "# No README content available";

    return (
        <div className="prose prose-blue max-w-none">
            <div className="whitespace-pre-wrap font-sans text-gray-800 leading-relaxed">
                {/* Very basic split for demo purposes */}
                {text.split('\n').map((line, i) => {
                    if (line.startsWith('# ')) return <h1 key={i} className="text-3xl font-bold mt-8 mb-4">{line.replace('# ', '')}</h1>;
                    if (line.startsWith('## ')) return <h2 key={i} className="text-xl font-bold mt-6 mb-3">{line.replace('## ', '')}</h2>;
                    if (line.startsWith('### ')) return <h3 key={i} className="text-lg font-bold mt-5 mb-2">{line.replace('### ', '')}</h3>;
                    if (line.startsWith('> ')) return <blockquote key={i} className="bg-blue-50 border-l-4 border-blue-500 p-4 my-4 italic text-gray-700">{line.replace('> ', '')}</blockquote>;
                    if (line.startsWith('```')) return <div key={i} className="bg-gray-900 text-green-400 p-4 rounded-lg font-mono text-sm my-4 overflow-x-auto">Code Block</div>;
                    if (line.trim().startsWith('- [ ]')) return (
                        <div key={i} className="flex items-center gap-2 my-1 p-2 bg-gray-50 rounded border border-gray-100">
                            <input type="checkbox" disabled className="text-blue-600 rounded" />
                            <span>{line.replace('- [ ]', '')}</span>
                        </div>
                    );
                    // Handle bullet points
                    if (line.trim().startsWith('- ')) return (
                        <div key={i} className="flex items-center gap-2 my-1 pl-4">
                            <span className="w-1.5 h-1.5 rounded-full bg-gray-400 flex-shrink-0"></span>
                            <span>{line.replace('- ', '')}</span>
                        </div>
                    );
                    if (line.trim() === '') return <div key={i} className="h-4"></div>;
                    return <p key={i} className="my-1">{line}</p>;
                })}
            </div>
        </div>
    );
};

const ReadmeViewer = () => {
    const { projectId } = useParams();
    const location = useLocation();
    const navigate = useNavigate();
    const [copied, setCopied] = useState(false);

    // Get content passed from navigation
    const content = location.state?.content;
    const readmeId = location.state?.readmeId;

    const handleCopy = () => {
        if (content) {
            navigator.clipboard.writeText(content);
            setCopied(true);
            setTimeout(() => setCopied(false), 2000);
        }
    };

    const handleDownload = () => {
        if (!content) return;

        const element = document.createElement("a");
        const file = new Blob([content], { type: 'text/markdown' });
        element.href = URL.createObjectURL(file);
        element.download = `${projectId}_README.md`;
        document.body.appendChild(element); // Required for this to work in FireFox
        element.click();
        document.body.removeChild(element);
    };

    const handleOpenVisualChart = () => {
        navigate(`/readme/${projectId}/visual-chart`, {
            state: {
                content,
                readmeId,
            }
        });
    };

    return (
        <div className="min-h-screen bg-gray-50 flex flex-col">
            <Header />

            <div className="bg-white border-b border-gray-200 px-4 py-3 sm:px-6 lg:px-8">
                <div className="max-w-7xl mx-auto flex justify-between items-center">
                    <div className="flex items-center gap-2 text-sm">
                        <Link to={`/projects/${projectId}`} className="text-gray-500 hover:text-gray-900 flex items-center gap-1">
                            <ChevronLeft className="h-4 w-4" />
                            Back to Project
                        </Link>
                        <span className="text-gray-300">/</span>
                        <span className="font-bold text-gray-900">README.md</span>
                    </div>

                    <div className="flex items-center gap-4 text-xs text-gray-500">
                        <div className="flex items-center gap-1.5 bg-blue-50 text-blue-700 px-2 py-1 rounded">
                            <div className="w-1.5 h-1.5 rounded-full bg-blue-600"></div>
                            Generated Just Now
                        </div>
                        <div className="flex items-center gap-1.5">
                            Source: AI Generator
                        </div>
                    </div>
                </div>
            </div>

            <div className="flex-1 max-w-7xl w-full mx-auto p-4 sm:p-6 lg:p-8 flex gap-8">

                {/* Table of Contents (Sidebar) - Simplified for now since we don't parse headers yet */}
                <div className="hidden lg:block w-64 flex-shrink-0">
                    <div className="sticky top-24">
                        <h3 className="flex items-center gap-2 text-sm font-semibold text-gray-900 mb-4">
                            <List className="h-4 w-4" />
                            Table of Contents
                        </h3>
                        <div className="text-sm text-gray-500 italic">
                            Generated from content structure
                        </div>
                    </div>
                </div>

                {/* Main Content */}
                <div className="flex-1 min-w-0">
                    <div className="bg-white rounded-xl shadow-sm border border-gray-200 overflow-hidden">
                        <div className="bg-gray-50 border-b border-gray-200 px-4 py-3 flex justify-between items-center">
                            <div className="text-sm font-medium text-gray-700 flex items-center gap-2">
                                <FileText className="h-4 w-4 text-gray-400" />
                                Preview
                            </div>
                            <div className="flex gap-2">
                                <Button
                                    size="sm"
                                    variant="outline"
                                    onClick={handleOpenVisualChart}
                                    disabled={!content}
                                >
                                    <Sparkles className="h-3.5 w-3.5 mr-1.5" />
                                    Generate Visual Chart
                                </Button>
                                <Button
                                    size="sm"
                                    variant="outline"
                                    onClick={handleCopy}
                                    className={copied ? "text-green-600 border-green-200 bg-green-50" : ""}
                                >
                                    <Copy className="h-3.5 w-3.5 mr-1.5" />
                                    {copied ? 'Copied!' : 'Copy Markdown'}
                                </Button>
                                <Button
                                    size="sm"
                                    className="bg-blue-600 hover:bg-blue-700 text-white"
                                    onClick={handleDownload}
                                >
                                    <Download className="h-3.5 w-3.5 mr-1.5" />
                                    Download README.md
                                </Button>
                            </div>
                        </div>

                        <div className="p-8 lg:p-12">
                            <MarkdownViewer content={content} />
                        </div>
                    </div>
                </div>

            </div>
        </div>
    );
};

export default ReadmeViewer;
