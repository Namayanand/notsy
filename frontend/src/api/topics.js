import api from './client';

export const getTopics = (notebookId) =>
  api.get(`/api/notebooks/${notebookId}/topics`);

export const getTopic = (notebookId, topicId) =>
  api.get(`/api/notebooks/${notebookId}/topics/${topicId}`);

export const createTopic = (notebookId, data) =>
  api.post(`/api/notebooks/${notebookId}/topics`, data);

export const updateTopic = (notebookId, topicId, data) =>
  api.put(`/api/notebooks/${notebookId}/topics/${topicId}`, data);

export const deleteTopic = (notebookId, topicId) =>
  api.delete(`/api/notebooks/${notebookId}/topics/${topicId}`);

export const reorderTopics = (notebookId, topicIds) =>
  api.post(`/api/notebooks/${notebookId}/topics/reorder`, { topicIds });
