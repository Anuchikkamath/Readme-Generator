import React, { useEffect, useState } from 'react';
import { Link, useLocation, useParams } from 'react-router-dom';
import { ChevronLeft, Copy, Download, FolderTree } from 'lucide-react';
import Header from '../../components/Header/Header';
import Button from '../../components/Button/Button';
import { createFolderStructure } from '../../api/scaffolding';

const FolderStructureViewer = () => {
    const { projectId } = useParams();
    const location = useLocation();

    const mermaidCode = location.state?.mermaidCode || '';
    const diagramKind = location.state?.diagramKind || 'flowchart';
    const projectName = location.state?.projectName || projectId || 'GeneratedProject';

    const [folderStructure, setFolderStructure] = useState('');
    const [requirementsTxt, setRequirementsTxt] = useState('');
    const [error, setError] = useState('');
    const [isGenerating, setIsGenerating] = useState(false);
    const [copiedSection, setCopiedSection] = useState('');

    const handleGenerate = async () => {
        if (!mermaidCode) {
            setError('Architecture diagram is missing. Go back to Visual Chart and generate one first.');
            return;
        }

        setError('');
        setIsGenerating(true);

        try {
            const response = await createFolderStructure({
                mermaidCode,
                diagramKind,
                projectName,
            });
            setFolderStructure(response.folder_structure || '');
            setRequirementsTxt(response.requirements_txt || '');
        } catch (err) {
            const message = err?.response?.data?.detail || err?.message || 'Failed to generate folder structure';
            setError(message);
            setFolderStructure('');
            setRequirementsTxt('');
        } finally {
            setIsGenerating(false);
        }
    };

    useEffect(() => {
        if (mermaidCode) {
            handleGenerate();
        }
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, []);

    const copyText = async (key, text) => {
        if (!text) return;
        await navigator.clipboard.writeText(text);
        setCopiedSection(key);
        setTimeout(() => setCopiedSection(''), 1500);
    };

    const downloadText = (filename, text) => {
        if (!text) return;
        const blob = new Blob([text], { type: 'text/plain;charset=utf-8' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = filename;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
    };

    return (
        <div className="min-h-screen bg-gray-50 flex flex-col">
            <Header />

            <div className="bg-white border-b border-gray-200 px-4 py-3 sm:px-6 lg:px-8">
                <div className="max-w-7xl mx-auto flex items-center gap-2 text-sm">
                    <Link
                        to={`/readme/${projectId}/visual-chart`}
                        state={location.state}
                        className="text-gray-500 hover:text-gray-900 flex items-center gap-1"
                    >
                        <ChevronLeft className="h-4 w-4" />
                        Back to Visual Chart
                    </Link>
                    <span className="text-gray-300">/</span>
                    <span className="font-bold text-gray-900">Folder Structure</span>
                </div>
            </div>

            <div className="flex-1 max-w-7xl w-full mx-auto p-4 sm:p-6 lg:p-8">
                <div className="bg-white rounded-xl shadow-sm border border-gray-200 overflow-hidden mb-6">
                    <div className="bg-gray-50 border-b border-gray-200 px-4 py-3 flex items-center justify-between">
                        <div className="text-sm font-medium text-gray-700 flex items-center gap-2">
                            <FolderTree className="h-4 w-4 text-blue-600" />
                            Project Scaffold from Architecture Diagram
                        </div>
                        <Button
                            size="sm"
                            className="bg-blue-600 hover:bg-blue-700 text-white"
                            onClick={handleGenerate}
                            isLoading={isGenerating}
                            disabled={!mermaidCode}
                        >
                            Regenerate
                        </Button>
                    </div>

                    <div className="p-6">
                        {!mermaidCode && (
                            <div className="mb-4 rounded-md border border-amber-200 bg-amber-50 px-3 py-2 text-sm text-amber-700">
                                Architecture diagram is not available. Please go back and generate a visual chart first.
                            </div>
                        )}

                        {error && (
                            <div className="mb-4 rounded-md border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700">
                                {error}
                            </div>
                        )}
                    </div>
                </div>

                <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                    <div className="bg-white rounded-xl shadow-sm border border-gray-200 overflow-hidden">
                        <div className="bg-gray-50 border-b border-gray-200 px-4 py-3 flex items-center justify-between">
                            <h3 className="text-sm font-semibold text-gray-900">Folder Structure</h3>
                            <div className="flex gap-2">
                                <Button
                                    size="sm"
                                    variant="outline"
                                    onClick={() => copyText('folder', folderStructure)}
                                    disabled={!folderStructure}
                                >
                                    <Copy className="h-3.5 w-3.5 mr-1.5" />
                                    {copiedSection === 'folder' ? 'Copied' : 'Copy'}
                                </Button>
                                <Button
                                    size="sm"
                                    variant="outline"
                                    onClick={() => downloadText(`${projectId}_folder_structure.txt`, folderStructure)}
                                    disabled={!folderStructure}
                                >
                                    <Download className="h-3.5 w-3.5 mr-1.5" />
                                    Download
                                </Button>
                            </div>
                        </div>
                        <pre className="p-4 text-xs sm:text-sm text-gray-800 bg-white overflow-auto max-h-[550px] whitespace-pre">
                            {folderStructure || 'No folder structure generated yet.'}
                        </pre>
                    </div>

                    <div className="bg-white rounded-xl shadow-sm border border-gray-200 overflow-hidden">
                        <div className="bg-gray-50 border-b border-gray-200 px-4 py-3 flex items-center justify-between">
                            <h3 className="text-sm font-semibold text-gray-900">requirements.txt</h3>
                            <div className="flex gap-2">
                                <Button
                                    size="sm"
                                    variant="outline"
                                    onClick={() => copyText('requirements', requirementsTxt)}
                                    disabled={!requirementsTxt}
                                >
                                    <Copy className="h-3.5 w-3.5 mr-1.5" />
                                    {copiedSection === 'requirements' ? 'Copied' : 'Copy'}
                                </Button>
                                <Button
                                    size="sm"
                                    variant="outline"
                                    onClick={() => downloadText('requirements.txt', requirementsTxt)}
                                    disabled={!requirementsTxt}
                                >
                                    <Download className="h-3.5 w-3.5 mr-1.5" />
                                    Download
                                </Button>
                            </div>
                        </div>
                        <pre className="p-4 text-xs sm:text-sm text-gray-800 bg-white overflow-auto max-h-[550px] whitespace-pre">
                            {requirementsTxt || 'No requirements generated yet.'}
                        </pre>
                    </div>
                </div>
            </div>
        </div>
    );
};

export default FolderStructureViewer;
