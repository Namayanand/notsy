package com.notsy.controller;

import com.notsy.dto.response.ApiResponse;
import com.notsy.dto.response.BranchBreadcrumb;
import com.notsy.dto.response.BranchNavigationResponse;
import com.notsy.dto.response.ConversationResponse;
import com.notsy.entity.User;
import com.notsy.service.AuthService;
import com.notsy.service.ConversationService;
import lombok.RequiredArgsConstructor;
import org.springframework.http.ResponseEntity;
import org.springframework.security.core.annotation.AuthenticationPrincipal;
import org.springframework.security.core.userdetails.UserDetails;
import org.springframework.web.bind.annotation.*;

import java.util.List;

@RestController
@RequestMapping("/api/branches")
@RequiredArgsConstructor
public class BranchController {

    private final ConversationService conversationService;
    private final AuthService authService;

    @GetMapping("/{branchId}/breadcrumb")
    public ResponseEntity<ApiResponse<List<BranchBreadcrumb>>> getBreadcrumb(
            @PathVariable Long branchId,
            @AuthenticationPrincipal UserDetails userDetails) {
        User user = authService.getCurrentUser(userDetails.getUsername());
        List<BranchBreadcrumb> breadcrumb = conversationService.getBreadcrumb(branchId, user);
        return ResponseEntity.ok(ApiResponse.success(breadcrumb));
    }

    @GetMapping("/{branchId}/navigate-to-parent")
    public ResponseEntity<ApiResponse<BranchNavigationResponse>> navigateToParent(
            @PathVariable Long branchId,
            @AuthenticationPrincipal UserDetails userDetails) {
        User user = authService.getCurrentUser(userDetails.getUsername());
        BranchNavigationResponse navigation = conversationService.navigateToParent(branchId, user);
        return ResponseEntity.ok(ApiResponse.success(navigation));
    }

    @GetMapping("/message/{messageId}/branches")
    public ResponseEntity<ApiResponse<List<ConversationResponse>>> getBranchesFromMessage(
            @PathVariable Long messageId,
            @AuthenticationPrincipal UserDetails userDetails) {
        User user = authService.getCurrentUser(userDetails.getUsername());
        List<ConversationResponse> branches = conversationService.getBranchesFromMessage(messageId, user);
        return ResponseEntity.ok(ApiResponse.success(branches));
    }
}