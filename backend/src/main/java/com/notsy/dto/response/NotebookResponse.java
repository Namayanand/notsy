package com.notsy.dto.response;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.time.LocalDateTime;
import java.util.List;

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class NotebookResponse {
    private Long id;
    private String title;
    private String description;
    private String colorTheme;
    private Boolean isPublic;
    private Long userId;
    private List<TopicSummaryResponse> topics;
    private LocalDateTime createdAt;
    private LocalDateTime updatedAt;

    @Data
    @Builder
    @NoArgsConstructor
    @AllArgsConstructor
    public static class TopicSummaryResponse {
        private Long id;
        private String title;
        private Integer orderIndex;
        private String embeddingStatus;
    }
}
