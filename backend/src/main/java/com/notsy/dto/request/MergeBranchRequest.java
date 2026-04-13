package com.notsy.dto.request;

import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotNull;
import lombok.Data;

@Data
public class MergeBranchRequest {
    @NotNull(message = "Branch conversation ID is required")
    private Long branchConversationId;

    @NotBlank(message = "Action is required (merge or discard)")
    private String action; // "merge" or "discard"
}
