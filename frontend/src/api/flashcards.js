import api from './client';

export const getFlashcards = (topicId) =>
  topicId
    ? api.get(`/api/flashcards/topic/${topicId}`)
    : api.get('/api/flashcards');

export const getDueCards = (topicId) =>
  api.get(`/api/flashcards/due${topicId ? `?topicId=${topicId}` : ''}`);

export const createFlashcard = (data) =>
  api.post('/api/flashcards', data);

export const reviewFlashcard = (cardId, data) =>
  api.post(`/api/flashcards/${cardId}/review`, data);

export const deleteFlashcard = (cardId) =>
  api.delete(`/api/flashcards/${cardId}`);

export const getSharedCards = () =>
  api.get('/api/flashcards/shared');
