package com.notsy.controller;

import com.notsy.dto.request.AddLinkRequest;
import com.notsy.dto.response.ApiResponse;
import com.notsy.dto.response.ResourceResponse;
import com.notsy.entity.User;
import com.notsy.service.AuthService;
import com.notsy.service.ResourceService;
import jakarta.validation.Valid;
import lombok.RequiredArgsConstructor;
import org.springframework.http.ResponseEntity;
import org.springframework.security.core.annotation.AuthenticationPrincipal;
import org.springframework.security.core.userdetails.UserDetails;
import org.springframework.web.bind.annotation.*;
import org.springframework.web.multipart.MultipartFile;

import java.util.List;

@RestController
@RequestMapping("/api/topics/{topicId}/resources")
@RequiredArgsConstructor
public class ResourceController {

    private final ResourceService resourceService;
    private final AuthService authService;

    @GetMapping
    public ResponseEntity<ApiResponse<List<ResourceResponse>>> getResources(
            @PathVariable Long topicId,
            @AuthenticationPrincipal UserDetails userDetails) {
        User user = authService.getCurrentUser(userDetails.getUsername());
        List<ResourceResponse> resources = resourceService.getResources(topicId, user);
        return ResponseEntity.ok(ApiResponse.success(resources));
    }

    @PostMapping("/upload")
    public ResponseEntity<ApiResponse<ResourceResponse>> uploadFile(
            @PathVariable Long topicId,
            @RequestParam("file") MultipartFile file,
            @AuthenticationPrincipal UserDetails userDetails) {
        User user = authService.getCurrentUser(userDetails.getUsername());
        ResourceResponse resource = resourceService.uploadFile(topicId, file, user);
        return ResponseEntity.ok(ApiResponse.success("File uploaded, processing started", resource));
    }

    @PostMapping("/link")
    public ResponseEntity<ApiResponse<ResourceResponse>> addLink(
            @PathVariable Long topicId,
            @Valid @RequestBody AddLinkRequest request,
            @AuthenticationPrincipal UserDetails userDetails) {
        User user = authService.getCurrentUser(userDetails.getUsername());
        ResourceResponse resource = resourceService.addLink(topicId, request, user);
        return ResponseEntity.ok(ApiResponse.success("Link added, processing started", resource));
    }

    @DeleteMapping("/{resourceId}")
    public ResponseEntity<ApiResponse<Void>> deleteResource(
            @PathVariable Long topicId,
            @PathVariable Long resourceId,
            @AuthenticationPrincipal UserDetails userDetails) {
        User user = authService.getCurrentUser(userDetails.getUsername());
        resourceService.deleteResource(topicId, resourceId, user);
        return ResponseEntity.ok(ApiResponse.success("Resource deleted", null));
    }

    @PostMapping("/{resourceId}/reembed")
    public ResponseEntity<ApiResponse<ResourceResponse>> reembedResource(
            @PathVariable Long topicId,
            @PathVariable Long resourceId,
            @AuthenticationPrincipal UserDetails userDetails) {
        User user = authService.getCurrentUser(userDetails.getUsername());
        ResourceResponse resource = resourceService.reembedResource(topicId, resourceId, user);
        return ResponseEntity.ok(ApiResponse.success("Re-embedding started", resource));
    }
}
