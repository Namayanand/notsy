import api from './client';

export const generateQuiz = (data) =>
  api.post('/api/quizzes/generate', data);

export const getQuizzesByTopic = (topicId) =>
  api.get(`/api/quizzes/topic/${topicId}`);

export const getQuiz = (quizId) =>
  api.get(`/api/quizzes/${quizId}`);

export const submitQuizAnswer = (quizId, data) =>
  api.post(`/api/quizzes/${quizId}/answer`, data);

export const completeQuiz = (quizId) =>
  api.post(`/api/quizzes/${quizId}/complete`);

export const getWeakAreas = (topicId) =>
  api.get(`/api/quizzes/topic/${topicId}/weak-areas`);
