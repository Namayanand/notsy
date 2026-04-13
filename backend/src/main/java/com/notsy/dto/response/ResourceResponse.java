package com.notsy.dto.response;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.time.LocalDateTime;

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class ResourceResponse {
    private Long id;
    private String filename;
    private String originalName;
    private String fileType;
    private Long fileSize;
    private String sourceUrl;
    private String embeddingStatus;
    private Integer chunkCount;
    private Long topicId;
    private LocalDateTime createdAt;
}
