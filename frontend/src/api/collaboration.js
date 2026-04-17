import api from './client';

export const getMembers = (notebookId) =>
  api.get(`/api/notebooks/${notebookId}/members`);

export const inviteMember = (notebookId, data) =>
  api.post(`/api/notebooks/${notebookId}/members/invite`, data);

export const removeMember = (notebookId, memberId) =>
  api.delete(`/api/notebooks/${notebookId}/members/${memberId}`);

export const updateMemberRole = (notebookId, memberId, role) =>
  api.patch(`/api/notebooks/${notebookId}/members/${memberId}/role`, { role });
