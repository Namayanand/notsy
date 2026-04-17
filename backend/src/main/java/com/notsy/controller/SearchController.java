package com.notsy.controller;

import com.notsy.entity.User;
import com.notsy.dto.request.SemanticSearchRequest;
import com.notsy.dto.response.SemanticSearchResponse;
import com.notsy.service.SemanticSearchService;
import lombok.RequiredArgsConstructor;
import org.springframework.http.ResponseEntity;
import org.springframework.security.core.annotation.AuthenticationPrincipal;
import org.springframework.web.bind.annotation.*;

@RestController
@RequestMapping("/api/search")
@RequiredArgsConstructor
public class SearchController {

    private final SemanticSearchService semanticSearchService;

    @PostMapping("/semantic")
    public ResponseEntity<SemanticSearchResponse> semanticSearch(
            @RequestBody SemanticSearchRequest request,
            @AuthenticationPrincipal User user) {
        int limit = request.getLimit() != null ? request.getLimit() : 10;
        return ResponseEntity.ok(semanticSearchService.search(
            request.getQuery(),
            request.getNotebookId(),
            user.getId(),
            limit
        ));
    }
}
