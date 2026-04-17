import api from './client';

export const getGlobalStreak = () =>
  api.get('/api/streaks/global');

export const getTopicStreak = (topicId) =>
  api.get(`/api/streaks/topic/${topicId}`);

export const getAllStreaks = () =>
  api.get('/api/streaks');

export const recordReview = (topicId) =>
  api.post(`/api/streaks/topic/${topicId}/review`);
