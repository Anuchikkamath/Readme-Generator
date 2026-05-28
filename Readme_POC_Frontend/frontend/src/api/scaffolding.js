import api from './axios';

export const createFolderStructure = async ({ mermaidCode, diagramKind = 'flowchart', projectName = null }) => {
    const response = await api.post('/create-folder-structure', {
        mermaid_code: mermaidCode,
        diagram_kind: diagramKind,
        project_name: projectName,
    });
    return response.data;
};
