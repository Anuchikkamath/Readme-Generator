import api from './axios';

export const generateDiagram = async (readmeContent, diagramKind = 'flowchart') => {
    const response = await api.post('/generate-diagram', {
        readme_content: readmeContent,
        diagram_kind: diagramKind,
    });
    return response.data;
};

export const renderDiagram = async (mermaidCode, format = 'svg') => {
    const response = await api.post(
        '/render-diagram',
        {
            mermaid_code: mermaidCode,
            format,
        },
        {
            responseType: 'arraybuffer',
        }
    );
    return response.data;
};
