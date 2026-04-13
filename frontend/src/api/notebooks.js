import api from './client';

export const getNotebooks = () => api.get('/api/notebooks');

export const getNotebook = (id) => api.get(`/api/notebooks/${id}`);

export const createNotebook = (data) =>
  api.post('/api/notebooks', data);

export const updateNotebook = (id, data) =>
  api.put(`/api/notebooks/${id}`, data);

export const deleteNotebook = (id) =>
  api.delete(`/api/notebooks/${id}`);
