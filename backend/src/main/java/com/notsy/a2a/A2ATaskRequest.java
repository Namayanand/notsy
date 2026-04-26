package com.notsy.a2a;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.util.Map;

/**
 * A2A Task request matching tasks/send JSON body
 */
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class A2ATaskRequest {
    private String taskId;
    private A2ASkill skill;
    private A2AMessage message;

    @Data
    @Builder
    @NoArgsConstructor
    @AllArgsConstructor
    public static class A2ASkill {
        private String id;
    }

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