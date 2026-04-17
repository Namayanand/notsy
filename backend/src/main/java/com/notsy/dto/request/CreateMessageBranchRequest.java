package com.notsy.dto.request;

import jakarta.validation.constraints.NotNull;
import lombok.Data;

@Data
public class CreateMessageBranchRequest {

    @NotNull(message = "Parent message ID is required")
    private Long parentMessageId;

    private Integer selectionStart;

    private Integer selectionEnd;

    // The anchor text (selected text) - becomes the branch title
    private String anchorText;

    // Optional branch context for AI (hidden from user)
    private String branchContext;

    private String learningMode;
}