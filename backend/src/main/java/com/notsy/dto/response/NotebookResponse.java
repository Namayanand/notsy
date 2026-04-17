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
    private OwnerInfo owner;
    private List<TopicSummaryResponse> topics;
    private List<MemberInfo> members;
    private LocalDateTime createdAt;
    private LocalDateTime updatedAt;
    private Boolean isShared;
    private String sharedRole;

    @Data
    @Builder
    @NoArgsConstructor
    @AllArgsConstructor
    public static class OwnerInfo {
        private Long id;
        private String name;
        private String email;
    }

    @Data
    @Builder
    @NoArgsConstructor
    @AllArgsConstructor
    public static class MemberInfo {
        private Long userId;
        private String name;
        private String email;
        private String role;
    }

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
