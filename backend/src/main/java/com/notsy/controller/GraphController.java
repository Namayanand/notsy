package com.notsy.controller;

import com.notsy.dto.request.AddRelationRequest;
import com.notsy.dto.response.ApiResponse;
import com.notsy.dto.response.GraphResponse;
import com.notsy.entity.User;
import com.notsy.service.AuthService;
import com.notsy.service.GraphService;
import jakarta.validation.Valid;
import lombok.RequiredArgsConstructor;
import org.springframework.http.ResponseEntity;
import org.springframework.security.core.annotation.AuthenticationPrincipal;
import org.springframework.security.core.userdetails.UserDetails;
import org.springframework.web.bind.annotation.*;

@RestController
@RequestMapping("/api/notebooks/{notebookId}/graph")
@RequiredArgsConstructor
public class GraphController {

    private final GraphService graphService;
    private final AuthService authService;

    @GetMapping
    public ResponseEntity<ApiResponse<GraphResponse>> getGraph(
            @PathVariable Long notebookId,
            @AuthenticationPrincipal UserDetails userDetails) {
        User user = authService.getCurrentUser(userDetails.getUsername());
        GraphResponse graph = graphService.getGraph(notebookId, user);
        return ResponseEntity.ok(ApiResponse.success(graph));
    }

    @PostMapping("/generate")
    public ResponseEntity<ApiResponse<GraphResponse>> generateGraph(
            @PathVariable Long notebookId,
            @AuthenticationPrincipal UserDetails userDetails) {
        User user = authService.getCurrentUser(userDetails.getUsername());
        GraphResponse graph = graphService.generateGraph(notebookId, user);
        return ResponseEntity.ok(ApiResponse.success("Graph generated", graph));
    }

    @PostMapping("/relations")
    public ResponseEntity<ApiResponse<GraphResponse.EdgeResponse>> addRelation(
            @PathVariable Long notebookId,
            @Valid @RequestBody AddRelationRequest request,
            @AuthenticationPrincipal UserDetails userDetails) {
        User user = authService.getCurrentUser(userDetails.getUsername());
        GraphResponse.EdgeResponse relation = graphService.addRelation(notebookId, request, user);
        return ResponseEntity.ok(ApiResponse.success("Relation added", relation));
    }

    @DeleteMapping("/relations/{relationId}")
    public ResponseEntity<ApiResponse<Void>> deleteRelation(
            @PathVariable Long notebookId,
            @PathVariable Long relationId,
            @AuthenticationPrincipal UserDetails userDetails) {
        User user = authService.getCurrentUser(userDetails.getUsername());
        graphService.deleteRelation(notebookId, relationId, user);
        return ResponseEntity.ok(ApiResponse.success("Relation deleted", null));
    }
}
