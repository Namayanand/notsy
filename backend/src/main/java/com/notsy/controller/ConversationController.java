package com.notsy.controller;

import com.notsy.dto.request.ChatRequest;
import com.notsy.dto.request.CreateBranchRequest;
import com.notsy.dto.request.CreateConversationRequest;
import com.notsy.dto.request.MergeBranchRequest;
import com.notsy.dto.response.ApiResponse;
import com.notsy.dto.response.ConversationResponse;
import com.notsy.dto.response.MessageResponse;
import com.notsy.entity.User;
import com.notsy.service.AuthService;
import com.notsy.service.ConversationService;
import jakarta.validation.Valid;
import lombok.RequiredArgsConstructor;
import org.springframework.http.ResponseEntity;
import org.springframework.security.core.annotation.AuthenticationPrincipal;
import org.springframework.security.core.userdetails.UserDetails;
import org.springframework.web.bind.annotation.*;

import java.util.List;

@RestController
@RequestMapping("/api/topics/{topicId}/conversations")
@RequiredArgsConstructor
public class ConversationController {

    private final ConversationService conversationService;
    private final AuthService authService;

    @GetMapping
    public ResponseEntity<ApiResponse<List<ConversationResponse>>> getConversations(
            @PathVariable Long topicId,
            @AuthenticationPrincipal UserDetails userDetails) {
        User user = authService.getCurrentUser(userDetails.getUsername());
        List<ConversationResponse> conversations = conversationService.getConversations(topicId, user);
        return ResponseEntity.ok(ApiResponse.success(conversations));
    }

    @PostMapping
    public ResponseEntity<ApiResponse<ConversationResponse>> createConversation(
            @PathVariable Long topicId,
            @Valid @RequestBody CreateConversationRequest request,
            @AuthenticationPrincipal UserDetails userDetails) {
        User user = authService.getCurrentUser(userDetails.getUsername());
        ConversationResponse conversation = conversationService.createConversation(topicId, request, user);
        return ResponseEntity.ok(ApiResponse.success("Conversation created", conversation));
    }

    @GetMapping("/{conversationId}")
    public ResponseEntity<ApiResponse<ConversationResponse>> getConversation(
            @PathVariable Long topicId,
            @PathVariable Long conversationId,
            @AuthenticationPrincipal UserDetails userDetails) {
        User user = authService.getCurrentUser(userDetails.getUsername());
        ConversationResponse conversation = conversationService.getConversation(topicId, conversationId, user);
        return ResponseEntity.ok(ApiResponse.success(conversation));
    }

    @DeleteMapping("/{conversationId}")
    public ResponseEntity<ApiResponse<Void>> deleteConversation(
            @PathVariable Long topicId,
            @PathVariable Long conversationId,
            @AuthenticationPrincipal UserDetails userDetails) {
        User user = authService.getCurrentUser(userDetails.getUsername());
        conversationService.deleteConversation(topicId, conversationId, user);
        return ResponseEntity.ok(ApiResponse.success("Conversation deleted", null));
    }

    @PostMapping("/{conversationId}/chat")
    public ResponseEntity<ApiResponse<MessageResponse>> chat(
            @PathVariable Long topicId,
            @PathVariable Long conversationId,
            @Valid @RequestBody ChatRequest request,
            @AuthenticationPrincipal UserDetails userDetails) {
        User user = authService.getCurrentUser(userDetails.getUsername());
        MessageResponse message = conversationService.chat(topicId, conversationId, request, user);
        return ResponseEntity.ok(ApiResponse.success(message));
    }

    @PostMapping("/{conversationId}/branch")
    public ResponseEntity<ApiResponse<ConversationResponse>> branchConversation(
            @PathVariable Long topicId,
            @PathVariable Long conversationId,
            @Valid @RequestBody CreateBranchRequest request,
            @AuthenticationPrincipal UserDetails userDetails) {
        User user = authService.getCurrentUser(userDetails.getUsername());
        ConversationResponse branch = conversationService.branchConversation(topicId, conversationId, request, user);
        return ResponseEntity.ok(ApiResponse.success("Branch created", branch));
    }

    @PostMapping("/{conversationId}/merge")
    public ResponseEntity<ApiResponse<ConversationResponse>> mergeBranch(
            @PathVariable Long topicId,
            @PathVariable Long conversationId,
            @Valid @RequestBody MergeBranchRequest request,
            @AuthenticationPrincipal UserDetails userDetails) {
        User user = authService.getCurrentUser(userDetails.getUsername());
        ConversationResponse result = conversationService.mergeBranch(topicId, conversationId, request, user);
        return ResponseEntity.ok(ApiResponse.success("Branch " + request.getAction() + "d", result));
    }

    @GetMapping("/{conversationId}/branches")
    public ResponseEntity<ApiResponse<List<ConversationResponse>>> getBranches(
            @PathVariable Long topicId,
            @PathVariable Long conversationId,
            @AuthenticationPrincipal UserDetails userDetails) {
        User user = authService.getCurrentUser(userDetails.getUsername());
        List<ConversationResponse> branches = conversationService.getBranches(topicId, conversationId, user);
        return ResponseEntity.ok(ApiResponse.success(branches));
    }
}
