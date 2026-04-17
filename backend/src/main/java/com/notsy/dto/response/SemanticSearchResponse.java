package com.notsy.dto.response;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.util.List;
import java.util.Map;

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class SemanticSearchResponse {

    private List<SearchResult> results;

    @Data
    @Builder
    @NoArgsConstructor
    @AllArgsConstructor
    public static class SearchResult {
        private String type; // topic, resource, conversation
        private Long id;
        private Long notebookId;
        private String title;
        private String snippet;
        private Float score;
    }
}
