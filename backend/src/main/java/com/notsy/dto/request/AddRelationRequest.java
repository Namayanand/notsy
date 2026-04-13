package com.notsy.dto.request;

import jakarta.validation.constraints.NotNull;
import lombok.Data;

@Data
public class AddRelationRequest {
    @NotNull(message = "Source topic ID is required")
    private Long sourceTopicId;

    @NotNull(message = "Target topic ID is required")
    private Long targetTopicId;

    @NotNull(message = "Relationship type is required")
    private String relationshipType; // RELATED, PREREQUISITE, EXTENDS, CONTRASTS

    private Float strength;

    private String description;
}
