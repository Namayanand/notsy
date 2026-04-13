package com.notsy.dto.response;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.util.List;

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class GraphResponse {
    private List<NodeResponse> nodes;
    private List<EdgeResponse> edges;

    @Data
    @Builder
    @NoArgsConstructor
    @AllArgsConstructor
    public static class NodeResponse {
        private Long id;
        private String title;
        private String embeddingStatus;
        private String description;
    }

    @Data
    @Builder
    @NoArgsConstructor
    @AllArgsConstructor
    public static class EdgeResponse {
        private Long id;
        private Long sourceTopicId;
        private Long targetTopicId;
        private String relationshipType;
        private Float strength;
        private String description;
    }
}
