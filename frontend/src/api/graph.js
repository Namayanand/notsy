import api from './client';

export const getGraph = (notebookId) =>
  api.get(`/api/notebooks/${notebookId}/graph`);

export const generateGraph = (notebookId) =>
  api.post(`/api/notebooks/${notebookId}/graph/generate`);

export const addRelation = (notebookId, data) =>
  api.post(`/api/notebooks/${notebookId}/graph/relations`, data);

export const deleteRelation = (notebookId, relationId) =>
  api.delete(`/api/notebooks/${notebookId}/graph/relations/${relationId}`);
