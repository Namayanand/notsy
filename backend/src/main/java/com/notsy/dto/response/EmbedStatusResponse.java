package com.notsy.dto.response;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class EmbedStatusResponse {
    private Long resourceId;
    private String status;
    private Integer chunkCount;
}
