package com.notsy.controller;

import com.notsy.dto.request.CreateTopicRequest;
import com.notsy.dto.request.ReorderTopicsRequest;
import com.notsy.dto.request.UpdateTopicRequest;
import com.notsy.dto.response.ApiResponse;
import com.notsy.dto.response.TopicResponse;
import com.notsy.entity.User;
import com.notsy.service.AuthService;
import com.notsy.service.TopicService;
import jakarta.validation.Valid;
import lombok.RequiredArgsConstructor;
import org.springframework.http.ResponseEntity;
import org.springframework.security.core.annotation.AuthenticationPrincipal;
import org.springframework.security.core.userdetails.UserDetails;
import org.springframework.web.bind.annotation.*;

import java.util.List;

@RestController
@RequestMapping("/api/notebooks/{notebookId}/topics")
@RequiredArgsConstructor
public class TopicController {

    private final TopicService topicService;
    private final AuthService authService;

    @GetMapping
    public ResponseEntity<ApiResponse<List<TopicResponse>>> getRootTopics(
            @PathVariable Long notebookId,
            @AuthenticationPrincipal UserDetails userDetails) {
        User user = authService.getCurrentUser(userDetails.getUsername());
        List<TopicResponse> topics = topicService.getRootTopics(notebookId, user);
        return ResponseEntity.ok(ApiResponse.success(topics));
    }

    @PostMapping
    public ResponseEntity<ApiResponse<TopicResponse>> createTopic(
            @PathVariable Long notebookId,
            @Valid @RequestBody CreateTopicRequest request,
            @AuthenticationPrincipal UserDetails userDetails) {
        User user = authService.getCurrentUser(userDetails.getUsername());
        TopicResponse topic = topicService.createTopic(notebookId, request, user);
        return ResponseEntity.ok(ApiResponse.success("Topic created", topic));
    }

    @GetMapping("/{topicId}")
    public ResponseEntity<ApiResponse<TopicResponse>> getTopic(
            @PathVariable Long notebookId,
            @PathVariable Long topicId,
            @AuthenticationPrincipal UserDetails userDetails) {
        User user = authService.getCurrentUser(userDetails.getUsername());
        TopicResponse topic = topicService.getTopic(notebookId, topicId, user);
        return ResponseEntity.ok(ApiResponse.success(topic));
    }

    @PutMapping("/{topicId}")
    public ResponseEntity<ApiResponse<TopicResponse>> updateTopic(
            @PathVariable Long notebookId,
            @PathVariable Long topicId,
            @Valid @RequestBody UpdateTopicRequest request,
            @AuthenticationPrincipal UserDetails userDetails) {
        User user = authService.getCurrentUser(userDetails.getUsername());
        TopicResponse topic = topicService.updateTopic(notebookId, topicId, request, user);
        return ResponseEntity.ok(ApiResponse.success("Topic updated", topic));
    }

    @DeleteMapping("/{topicId}")
    public ResponseEntity<ApiResponse<Void>> deleteTopic(
            @PathVariable Long notebookId,
            @PathVariable Long topicId,
            @AuthenticationPrincipal UserDetails userDetails) {
        User user = authService.getCurrentUser(userDetails.getUsername());
        topicService.deleteTopic(notebookId, topicId, user);
        return ResponseEntity.ok(ApiResponse.success("Topic deleted", null));
    }

    @PostMapping("/{topicId}/reorder")
    public ResponseEntity<ApiResponse<Void>> reorderTopics(
            @PathVariable Long notebookId,
            @PathVariable Long topicId,
            @Valid @RequestBody ReorderTopicsRequest request,
            @AuthenticationPrincipal UserDetails userDetails) {
        User user = authService.getCurrentUser(userDetails.getUsername());
        topicService.reorderTopics(notebookId, request, user);
        return ResponseEntity.ok(ApiResponse.success("Topics reordered", null));
    }
}
