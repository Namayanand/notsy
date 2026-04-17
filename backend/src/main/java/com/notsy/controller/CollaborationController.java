package com.notsy.controller;

import com.notsy.entity.User;
import com.notsy.dto.request.InviteMemberRequest;
import com.notsy.dto.response.MemberResponse;
import com.notsy.service.AuthService;
import com.notsy.service.CollaborationService;
import jakarta.validation.Valid;
import lombok.RequiredArgsConstructor;
import org.springframework.http.ResponseEntity;
import org.springframework.security.core.annotation.AuthenticationPrincipal;
import org.springframework.security.core.userdetails.UserDetails;
import org.springframework.web.bind.annotation.*;

import java.util.List;

@RestController
@RequestMapping("/api/notebooks/{notebookId}/members")
@RequiredArgsConstructor
public class CollaborationController {

    private final CollaborationService collaborationService;
    private final AuthService authService;

    @GetMapping
    public ResponseEntity<List<MemberResponse>> getMembers(
            @PathVariable Long notebookId,
            @AuthenticationPrincipal UserDetails userDetails) {
        User user = authService.getCurrentUser(userDetails.getUsername());
        return ResponseEntity.ok(collaborationService.getMembers(notebookId, user));
    }

    @PostMapping("/invite")
    public ResponseEntity<MemberResponse> inviteMember(
            @PathVariable Long notebookId,
            @Valid @RequestBody InviteMemberRequest request,
            @AuthenticationPrincipal UserDetails userDetails) {
        User user = authService.getCurrentUser(userDetails.getUsername());
        return ResponseEntity.ok(collaborationService.inviteMember(notebookId, request, user));
    }

    @DeleteMapping("/{memberId}")
    public ResponseEntity<Void> removeMember(
            @PathVariable Long notebookId,
            @PathVariable Long memberId,
            @AuthenticationPrincipal UserDetails userDetails) {
        User user = authService.getCurrentUser(userDetails.getUsername());
        collaborationService.removeMember(notebookId, memberId, user);
        return ResponseEntity.noContent().build();
    }

    @PatchMapping("/{memberId}/role")
    public ResponseEntity<Void> updateMemberRole(
            @PathVariable Long notebookId,
            @PathVariable Long memberId,
            @RequestBody java.util.Map<String, String> body,
            @AuthenticationPrincipal UserDetails userDetails) {
        User user = authService.getCurrentUser(userDetails.getUsername());
        collaborationService.updateMemberRole(notebookId, memberId, body.get("role"), user);
        return ResponseEntity.ok().build();
    }
}