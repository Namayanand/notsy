package com.notsy.controller;

import com.notsy.dto.request.CreateNotebookRequest;
import com.notsy.dto.request.UpdateNotebookRequest;
import com.notsy.dto.response.ApiResponse;
import com.notsy.dto.response.NotebookResponse;
import com.notsy.entity.User;
import com.notsy.service.AuthService;
import com.notsy.service.NotebookService;
import jakarta.validation.Valid;
import lombok.RequiredArgsConstructor;
import org.springframework.http.ResponseEntity;
import org.springframework.security.core.annotation.AuthenticationPrincipal;
import org.springframework.security.core.userdetails.UserDetails;
import org.springframework.web.bind.annotation.*;

import java.util.List;

@RestController
@RequestMapping("/api/notebooks")
@RequiredArgsConstructor
public class NotebookController {

    private final NotebookService notebookService;
    private final AuthService authService;

    @GetMapping
    public ResponseEntity<ApiResponse<List<NotebookResponse>>> getAllNotebooks(
            @AuthenticationPrincipal UserDetails userDetails) {
        User user = authService.getCurrentUser(userDetails.getUsername());
        List<NotebookResponse> notebooks = notebookService.getAllNotebooks(user);
        return ResponseEntity.ok(ApiResponse.success(notebooks));
    }

    @PostMapping
    public ResponseEntity<ApiResponse<NotebookResponse>> createNotebook(
            @Valid @RequestBody CreateNotebookRequest request,
            @AuthenticationPrincipal UserDetails userDetails) {
        User user = authService.getCurrentUser(userDetails.getUsername());
        NotebookResponse notebook = notebookService.createNotebook(request, user);
        return ResponseEntity.ok(ApiResponse.success("Notebook created", notebook));
    }

    @GetMapping("/{id}")
    public ResponseEntity<ApiResponse<NotebookResponse>> getNotebook(
            @PathVariable Long id,
            @AuthenticationPrincipal UserDetails userDetails) {
        User user = authService.getCurrentUser(userDetails.getUsername());
        NotebookResponse notebook = notebookService.getNotebook(id, user);
        return ResponseEntity.ok(ApiResponse.success(notebook));
    }

    @PutMapping("/{id}")
    public ResponseEntity<ApiResponse<NotebookResponse>> updateNotebook(
            @PathVariable Long id,
            @Valid @RequestBody UpdateNotebookRequest request,
            @AuthenticationPrincipal UserDetails userDetails) {
        User user = authService.getCurrentUser(userDetails.getUsername());
        NotebookResponse notebook = notebookService.updateNotebook(id, request, user);
        return ResponseEntity.ok(ApiResponse.success("Notebook updated", notebook));
    }

    @DeleteMapping("/{id}")
    public ResponseEntity<ApiResponse<Void>> deleteNotebook(
            @PathVariable Long id,
            @AuthenticationPrincipal UserDetails userDetails) {
        User user = authService.getCurrentUser(userDetails.getUsername());
        notebookService.deleteNotebook(id, user);
        return ResponseEntity.ok(ApiResponse.success("Notebook deleted", null));
    }
}
