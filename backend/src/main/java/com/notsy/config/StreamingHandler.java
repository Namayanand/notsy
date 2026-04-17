package com.notsy.config;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.notsy.entity.User;
import com.notsy.repository.UserRepository;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Component;
import org.springframework.web.socket.CloseStatus;
import org.springframework.web.socket.TextMessage;
import org.springframework.web.socket.WebSocketSession;
import org.springframework.web.socket.handler.TextWebSocketHandler;

import java.io.IOException;
import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;

@Component
@Slf4j
public class StreamingHandler extends TextWebSocketHandler {

    // conversationId -> session
    private final Map<Long, WebSocketSession> chatSessions = new ConcurrentHashMap<>();
    // sessionId -> conversationId
    private final Map<String, Long> sessionConversations = new ConcurrentHashMap<>();
    // sessionId -> userId
    private final Map<String, Long> sessionUsers = new ConcurrentHashMap<>();

    private final ObjectMapper objectMapper;

    public StreamingHandler(ObjectMapper objectMapper) {
        this.objectMapper = objectMapper;
    }

    public void registerSession(Long conversationId, Long userId, WebSocketSession session) {
        chatSessions.put(conversationId, session);
        sessionConversations.put(session.getId(), conversationId);
        sessionUsers.put(session.getId(), userId);
        log.info("WebSocket session registered for conversation {} by user {}", conversationId, userId);
    }

    public void sendToken(Long conversationId, String token) {
        WebSocketSession session = chatSessions.get(conversationId);
        if (session != null && session.isOpen()) {
            try {
                Map<String, Object> payload = Map.of(
                    "type", "token",
                    "data", Map.of("token", token)
                );
                session.sendMessage(new TextMessage(objectMapper.writeValueAsString(payload)));
            } catch (IOException e) {
                log.error("Error sending token to conversation {}", conversationId, e);
            }
        }
    }

    public void sendDone(Long conversationId, String finalResponse, int tokensUsed) {
        WebSocketSession session = chatSessions.get(conversationId);
        if (session != null && session.isOpen()) {
            try {
                Map<String, Object> payload = Map.of(
                    "type", "done",
                    "data", Map.of(
                        "response", finalResponse,
                        "tokensUsed", tokensUsed
                    )
                );
                session.sendMessage(new TextMessage(objectMapper.writeValueAsString(payload)));
            } catch (IOException e) {
                log.error("Error sending done to conversation {}", conversationId, e);
            }
        }
    }

    public void sendError(Long conversationId, String error) {
        WebSocketSession session = chatSessions.get(conversationId);
        if (session != null && session.isOpen()) {
            try {
                Map<String, Object> payload = Map.of(
                    "type", "error",
                    "data", Map.of("error", error)
                );
                session.sendMessage(new TextMessage(objectMapper.writeValueAsString(payload)));
            } catch (IOException e) {
                log.error("Error sending error to conversation {}", conversationId, e);
            }
        }
    }

    public void cleanup(Long conversationId) {
        WebSocketSession session = chatSessions.remove(conversationId);
        if (session != null && session.isOpen()) {
            try {
                session.close();
            } catch (IOException e) {
                log.error("Error closing session for conversation {}", conversationId, e);
            }
        }
    }

    public Long getConversationId(String sessionId) {
        return sessionConversations.get(sessionId);
    }

    public Long getUserId(String sessionId) {
        return sessionUsers.get(sessionId);
    }

    @Override
    public void afterConnectionEstablished(WebSocketSession session) {
        log.info("WebSocket connection established: {}", session.getId());
    }

    @Override
    public void afterConnectionClosed(WebSocketSession session, CloseStatus status) {
        Long convId = sessionConversations.remove(session.getId());
        if (convId != null) {
            chatSessions.remove(convId);
        }
        sessionUsers.remove(session.getId());
        log.info("WebSocket connection closed: {} (conversation: {})", session.getId(), convId);
    }

    @Override
    protected void handleTextMessage(WebSocketSession session, TextMessage message) {
        // Handle incoming messages from client (e.g., cancel stream)
        try {
            Map<String, Object> msg = objectMapper.readValue(message.getPayload(), Map.class);
            String type = (String) msg.get("type");
            if ("cancel".equals(type)) {
                Long convId = sessionConversations.get(session.getId());
                if (convId != null) {
                    // Signal cancellation - streaming handlers will check this
                    log.info("Stream cancel requested for conversation {}", convId);
                }
            }
        } catch (Exception e) {
            log.error("Error processing WebSocket message", e);
        }
    }
}
