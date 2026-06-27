import api from './client';

const AGENT_BASE = '/agent';

export const startAgentSession = (goal, topicId = null, notebookId = null) => {
  const userId = parseInt(localStorage.getItem('userId'));
  if (!userId || isNaN(userId)) {
    return Promise.reject(new Error('User not logged in'));
  }
  return api.post(`${AGENT_BASE}/start-session`, {
    user_id: userId,
    goal,
    topic_id: topicId,
    notebook_id: notebookId
  });
};

export const sendAgentMessage = (sessionId, message, agent = null) =>
  api.post(`${AGENT_BASE}/message`, {
    session_id: sessionId,
    message,
    agent
  });

export const getAgentState = (sessionId) =>
  api.get(`${AGENT_BASE}/state/${sessionId}`);

export const getRoadmap = (sessionId) =>
  api.get(`${AGENT_BASE}/roadmap/${sessionId}`);

export const generateQuiz = (sessionId, topic, difficulty = 'medium', numQuestions = 5) =>
  api.post(`${AGENT_BASE}/quiz/generate`, {
    session_id: sessionId,
    topic,
    difficulty,
    num_questions: numQuestions
  });

export const evaluateAnswer = (sessionId, question, userAnswer, correctAnswer, topic) =>
  api.post(`${AGENT_BASE}/quiz/evaluate`, {
    session_id: sessionId,
    question,
    user_answer: userAnswer,
    correct_answer: correctAnswer,
    topic
  });

export const getInsights = (userId) =>
  api.get(`${AGENT_BASE}/insights/${userId}`);

export const endSession = (sessionId) =>
  api.post(`${AGENT_BASE}/end-session/${sessionId}`);

export const connectAgentStream = (sessionId) => {
  // Derive WebSocket URL from VITE_WS_URL, or fall back to converting VITE_API_URL
  // (http → ws, https → wss). Default to localhost for local dev.
  const httpBase = import.meta.env.VITE_API_URL || 'http://localhost:8080';
  const wsBase = import.meta.env.VITE_WS_URL || httpBase.replace(/^http/, 'ws');
  const wsUrl = `${wsBase}/agent/stream/${sessionId}`;
  return new WebSocket(wsUrl);
};