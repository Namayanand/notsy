import api from './client';

export const getConversations = (topicId) =>
  api.get(`/api/topics/${topicId}/conversations`);

export const getConversation = (topicId, conversationId) =>
  api.get(`/api/topics/${topicId}/conversations/${conversationId}`);

export const createConversation = (topicId, data) =>
  api.post(`/api/topics/${topicId}/conversations`, data);

export const deleteConversation = (topicId, conversationId) =>
  api.delete(`/api/topics/${topicId}/conversations/${conversationId}`);

export const chat = (topicId, conversationId, message, learningMode = 'MASTER_THIS', useWebSearch = false) =>
  api.post(`/api/topics/${topicId}/conversations/${conversationId}/chat`, {
    message,
    learningMode,
    useWebSearch
  });

export const branchConversation = (topicId, conversationId, data) =>
  api.post(`/api/topics/${topicId}/conversations/${conversationId}/branch`, data);

export const branchFromMessage = (topicId, conversationId, data) =>
  api.post(`/api/topics/${topicId}/conversations/${conversationId}/branch-from-message`, data);

export const mergeBranch = (topicId, conversationId, data) =>
  api.post(`/api/topics/${topicId}/conversations/${conversationId}/merge`, data);

export const getBranches = (topicId, conversationId) =>
  api.get(`/api/topics/${topicId}/conversations/${conversationId}/branches`);

export const getBranchesFromMessage = (messageId) =>
  api.get(`/api/branches/message/${messageId}/branches`);

export const getBreadcrumb = (branchId) =>
  api.get(`/api/branches/${branchId}/breadcrumb`);

export const navigateToParent = (branchId) =>
  api.get(`/api/branches/${branchId}/navigate-to-parent`);
