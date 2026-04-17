import api from './client';

export const createStudyPlan = (data) =>
  api.post('/api/study-plans', data);

export const getActivePlans = () =>
  api.get('/api/study-plans');

export const getAllPlans = () =>
  api.get('/api/study-plans/all');

export const getPlan = (planId) =>
  api.get(`/api/study-plans/${planId}`);

export const updatePlanDay = (planId, dayId, data) =>
  api.patch(`/api/study-plans/${planId}/days/${dayId}`, data);
