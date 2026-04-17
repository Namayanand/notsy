import api from './client';

export const getNotifications = () =>
  api.get('/api/notifications');

export const getUnreadNotifications = () =>
  api.get('/api/notifications/unread');

export const getUnreadCount = () =>
  api.get('/api/notifications/unread/count');

export const markAsRead = (notificationId) =>
  api.patch(`/api/notifications/${notificationId}/read`);

export const markAllAsRead = () =>
  api.patch('/api/notifications/read-all');

export const deleteNotification = (notificationId) =>
  api.delete(`/api/notifications/${notificationId}`);
