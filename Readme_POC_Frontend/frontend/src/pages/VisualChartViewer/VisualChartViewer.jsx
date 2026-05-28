import React, { useState } from 'react';
import { Link, useLocation, useNavigate, useParams } from 'react-router-dom';
import { ChevronLeft, Sparkles } from 'lucide-react';
import Header from '../../components/Header/Header';
import Button from '../../components/Button/Button';
import { generateDiagram, renderDiagram } from '../../api/diagrams';
import mermaid from 'mermaid';

const DIAGRAM_TYPES = [
    { value: 'flowchart', label: 'Flowchart' },
    { value: 'sequence', label: 'Sequence' },
    { value: 'class', label: 'Class' },
    { value: 'er', label: 'ER' },
    { value: 'journey', label: 'Journey' },
    { value: 'state', label: 'State' },
    { value: 'mindmap', label: 'Mindmap' },
];

const VisualChartViewer = () => {
    const { projectId } = useParams();
    const location = useLocation();
    const navigate = useNavigate();

    const content = location.state?.content;

    const [diagramKind, setDiagramKind] = useState('flowchart');
    const [mermaidCode, setMermaidCode] = useState('');
    const [diagramSvg, setDiagramSvg] = useState('');
    const [diagramError, setDiagramError] = useState('');
    const [isGeneratingDiagram, setIsGeneratingDiagram] = useState(false);
    const [isDownloadingDiagram, setIsDownloadingDiagram] = useState(false);

    const validateAndRenderMermaid = async (code) => {
        const cleaned = (code || '').trim();
        if (!cleaned) {
            throw new Error('Generated diagram is empty.');
        }

        mermaid.initialize({
            startOnLoad: false,
            securityLevel: 'strict',
            theme: 'default',
        });

        await mermaid.parse(cleaned);
        const renderId = `diagram-${Date.now()}`;
        const { svg } = await mermaid.render(renderId, cleaned);
        setDiagramSvg(svg);
        setMermaidCode(cleaned);
    };

    const handleGenerateDiagram = async () => {
        if (!content) return;

        setIsGeneratingDiagram(true);
        setDiagramError('');

        try {
            const response = await generateDiagram(content, diagramKind);
            await validateAndRenderMermaid(response.mermaid_code);
        } catch (err) {
            const message = err?.response?.data?.detail || err?.message || 'Failed to generate diagram';
            setDiagramError(message);
            setDiagramSvg('');
            setMermaidCode('');
        } finally {
            setIsGeneratingDiagram(false);
        }
    };

    const handleDownloadDiagram = async (format) => {
        if (!mermaidCode) return;

        setIsDownloadingDiagram(true);
        setDiagramError('');

        try {
            const binary = await renderDiagram(mermaidCode, format);
            const blobType = format === 'svg'
                ? 'image/svg+xml'
                : format === 'png'
                    ? 'image/png'
                    : 'application/pdf';

            const blob = new Blob([binary], { type: blobType });
            const url = URL.createObjectURL(blob);
            const element = document.createElement('a');
            element.href = url;
            element.download = `${projectId}_diagram.${format}`;
            document.body.appendChild(element);
            element.click();
            document.body.removeChild(element);
            URL.revokeObjectURL(url);
        } catch (err) {
            const message = err?.response?.data?.detail || err?.message || 'Failed to render diagram';
            setDiagramError(message);
        } finally {
            setIsDownloadingDiagram(false);
        }
    };

    const handleOpenFolderStructure = () => {
        if (!mermaidCode) {
            setDiagramError('Generate a visual chart first, then create folder structure.');
            return;
        }

        navigate(`/readme/${projectId}/folder-structure`, {
            state: {
                ...location.state,
                mermaidCode,
                diagramKind,
                projectName: projectId,
            }
        });
    };

    return (
        <div className="min-h-screen bg-gray-50 flex flex-col">
            <Header />

            <div className="bg-white border-b border-gray-200 px-4 py-3 sm:px-6 lg:px-8">
                <div className="max-w-7xl mx-auto flex items-center gap-2 text-sm">
                    <Link to={`/readme/${projectId}`} state={location.state} className="text-gray-500 hover:text-gray-900 flex items-center gap-1">
                        <ChevronLeft className="h-4 w-4" />
                        Back to README
                    </Link>
                    <span className="text-gray-300">/</span>
                    <span className="font-bold text-gray-900">Visual Chart</span>
                </div>
            </div>

            <div className="flex-1 max-w-7xl w-full mx-auto p-4 sm:p-6 lg:p-8">
                <div className="bg-white rounded-xl shadow-sm border border-gray-200 overflow-hidden">
                    <div className="bg-gray-50 border-b border-gray-200 px-4 py-3 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
                        <div className="text-sm font-medium text-gray-700 flex items-center gap-2">
                            <Sparkles className="h-4 w-4 text-blue-600" />
                            Visual Chart
                        </div>

                        <div className="flex flex-wrap items-center gap-2">
                            <select
                                value={diagramKind}
                                onChange={(e) => setDiagramKind(e.target.value)}
                                className="text-sm border border-gray-300 rounded-md px-2 py-1.5 bg-white"
                            >
                                {DIAGRAM_TYPES.map((type) => (
                                    <option key={type.value} value={type.value}>{type.label}</option>
                                ))}
                            </select>

                            <Button
                                size="sm"
                                variant="outline"
                                onClick={handleOpenFolderStructure}
                                disabled={!mermaidCode}
                            >
                                Create Folder Structure
                            </Button>

                            <Button
                                size="sm"
                                className="bg-blue-600 hover:bg-blue-700 text-white"
                                onClick={handleGenerateDiagram}
                                isLoading={isGeneratingDiagram}
                                disabled={!content}
                            >
                                <Sparkles className="h-3.5 w-3.5 mr-1.5" />
                                Generate Visual Chart
                            </Button>

                            <Button
                                size="sm"
                                variant="outline"
                                onClick={() => handleDownloadDiagram('svg')}
                                isLoading={isDownloadingDiagram}
                                disabled={!mermaidCode}
                            >
                                Download SVG
                            </Button>
                            <Button
                                size="sm"
                                variant="outline"
                                onClick={() => handleDownloadDiagram('png')}
                                isLoading={isDownloadingDiagram}
                                disabled={!mermaidCode}
                            >
                                Download PNG
                            </Button>
                        </div>
                    </div>

                    <div className="p-6">
                        {!content && (
                            <div className="mb-4 rounded-md border border-amber-200 bg-amber-50 px-3 py-2 text-sm text-amber-700">
                                README content is not available in this session. Go back and open this page from the README viewer.
                            </div>
                        )}

                        {diagramError && (
                            <div className="mb-4 rounded-md border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700">
                                {diagramError}
                            </div>
                        )}

                        {!diagramSvg && !diagramError && content && (
                            <p className="text-sm text-gray-500">
                                Select a diagram type and click Generate Visual Chart.
                            </p>
                        )}

                        {diagramSvg && (
                            <div className="overflow-auto rounded-md border border-gray-200 bg-white p-4">
                                <div dangerouslySetInnerHTML={{ __html: diagramSvg }} />
                            </div>
                        )}
                    </div>
                </div>
            </div>
        </div>
    );
};

export default VisualChartViewer;
