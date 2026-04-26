package com.notsy.a2a;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.util.Map;

/**
 * A2A Task response matching Task object response
 */
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class A2ATaskResponse {
    private String id;
    private A2ATaskStatus status;
    private A2AMessage input;
    private A2AMessage output;
    private Map<String, Object> metadata;
    private String createdAt;
    private String updatedAt;

    @Data
    @Builder
    @NoArgsConstructor
    @AllArgsConstructor
    public static class A2AMessage {
        private String role;
        private String content;
        private Map<String, Object> metadata;
    }
}