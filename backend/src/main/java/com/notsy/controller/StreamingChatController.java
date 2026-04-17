package com.notsy.controller;

import com.notsy.config.StreamingHandler;
import com.notsy.dto.request.StreamingChatRequest;
import com.notsy.entity.User;
import com.notsy.service.AIProxyService;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.http.ResponseEntity;
import org.springframework.security.core.annotation.AuthenticationPrincipal;
import org.springframework.web.bind.annotation.*;
import org.springframework.web.socket.WebSocketSession;

import java.util.Map;

@RestController
@RequestMapping("/api/chat")
@RequiredArgsConstructor
@Slf4j
public class StreamingChatController {

    private final AIProxyService aiProxyService;
    private final StreamingHandler streamingHandler;

    @PostMapping("/{conversationId}/stream")
    public ResponseEntity<Map<String, String>> startStreaming(
            @PathVariable Long conversationId,
            @RequestBody StreamingChatRequest request,
            @AuthenticationPrincipal User user) {
        // WebSocket URL for the client to connect to
        return ResponseEntity.ok(Map.of(
            "status", "streaming",
            "websocketUrl", "/ws/stream",
            "conversationId", conversationId.toString()
        ));
    }

    @PostMapping("/{conversationId}/cancel")
    public ResponseEntity<Void> cancelStreaming(
            @PathVariable Long conversationId,
            @AuthenticationPrincipal User user) {
        // Signal cancellation via WebSocket
        return ResponseEntity.ok().build();
    }
}
