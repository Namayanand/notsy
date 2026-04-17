import api from './client';

export const semanticSearch = (data) =>
  api.post('/api/search/semantic', data);
