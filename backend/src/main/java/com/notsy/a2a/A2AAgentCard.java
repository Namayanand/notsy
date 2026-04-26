package com.notsy.a2a;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.util.List;

/**
 * Agent Card as defined in A2A protocol - exposes agent metadata
 */
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class A2AAgentCard {
    private String name;
    private String description;
    private String version;
    private String url;
    private AgentCapabilities capabilities;
    private List<A2AAgentSkill> skills;

    @Data
    @Builder
    @NoArgsConstructor
    @AllArgsConstructor
    public static class AgentCapabilities {
        private boolean streaming;
        private boolean stateTransitionHistory;
    }
}