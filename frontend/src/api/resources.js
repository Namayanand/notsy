import api from './client';

export const getResources = (topicId) =>
  api.get(`/api/topics/${topicId}/resources`);

export const uploadFile = (topicId, formData) =>
  api.post(`/api/topics/${topicId}/resources/upload`, formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  });

export const addLink = (topicId, data) =>
  api.post(`/api/topics/${topicId}/resources/link`, data);

export const deleteResource = (topicId, resourceId) =>
  api.delete(`/api/topics/${topicId}/resources/${resourceId}`);

export const reembedResource = (topicId, resourceId) =>
  api.post(`/api/topics/${topicId}/resources/${resourceId}/reembed`);
