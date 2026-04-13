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
public class TopicResponse {
    private Long id;
    private String title;
    private String description;
    private Integer orderIndex;
    private Long notebookId;
    private Long parentTopicId;
    private String embeddingStatus;
    private List<String> tags;
    private List<ResourceResponse> resources;
    private List<ConversationSummaryResponse> conversations;
    private List<TopicResponse> subtopics;
    private LocalDateTime createdAt;

    @Data
    @Builder
    @NoArgsConstructor
    @AllArgsConstructor
    public static class ConversationSummaryResponse {
        private Long id;
        private String title;
        private String learningMode;
        private Boolean isBranch;
        private String branchStatus;
        private LocalDateTime createdAt;
    }
}
