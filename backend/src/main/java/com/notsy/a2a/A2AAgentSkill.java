package com.notsy.a2a;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.util.List;

/**
 * Agent skill definition as defined in A2A protocol
 */
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class A2AAgentSkill {
    private String id;
    private String name;
    private String description;
    private List<String> inputModes;
    private List<String> outputModes;
}