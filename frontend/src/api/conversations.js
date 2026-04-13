import api from './client';

export const getConversations = (topicId) =>
  api.get(`/api/topics/${topicId}/conversations`);

export const getConversation = (topicId, conversationId) =>
  api.get(`/api/topics/${topicId}/conversations/${conversationId}`);

export const createConversation = (topicId, data) =>
  api.post(`/api/topics/${topicId}/conversations`, data);

export const deleteConversation = (topicId, conversationId) =>
  api.delete(`/api/topics/${topicId}/conversations/${conversationId}`);

export const chat = (topicId, conversationId, message) =>
  api.post(`/api/topics/${topicId}/conversations/${conversationId}/chat`, { message });

export const branchConversation = (topicId, conversationId, data) =>
  api.post(`/api/topics/${topicId}/conversations/${conversationId}/branch`, data);

export const mergeBranch = (topicId, conversationId, data) =>
  api.post(`/api/topics/${topicId}/conversations/${conversationId}/merge`, data);

export const getBranches = (topicId, conversationId) =>
  api.get(`/api/topics/${topicId}/conversations/${conversationId}/branches`);
