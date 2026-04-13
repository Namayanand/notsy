import api from './client';

export const login = (email, password) =>
  api.post('/api/auth/login', { email, password });

export const register = (name, email, password) =>
  api.post('/api/auth/register', { name, email, password });

export const refreshToken = (refreshToken) =>
  api.post('/api/auth/refresh', { refreshToken });

export const getCurrentUser = () =>
  api.get('/api/auth/me');
