import api from './axios';

// Sync emails from Gmail
export const syncGmail = async () => {
    const response = await api.post('/sync');
    return response.data;
};

// Get all projects
export const getProjects = async () => {
    const response = await api.get('/projects');
    const rawProjects = response.data.projects || [];

    // Map backend response to frontend model
    return rawProjects.map(project => ({
        id: project.normalized_name,
        name: project.canonical_name,
        description: 'AI-generated documentation from meeting notes',
        updated_at: new Date().toISOString(), // Fallback since API doesn't return this yet
        status: 'active',
        meeting_count: 0, // Fallback
        is_new: false
    }));
};

// Get single project details
export const getProjectDetails = async (projectId) => {
    const response = await api.get(`/projects/${projectId}`);
    return response.data;
};

// Generate README for a project
export const generateReadme = async (projectId, startDate, endDate, meetingIds) => {
    const payload = {
        project_id: projectId,
        start_date: startDate,
        end_date: endDate,
        meeting_ids: meetingIds
    };
    const response = await api.post('/generate-readme', payload);
    return response.data;
};
