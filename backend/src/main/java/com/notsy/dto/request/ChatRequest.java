package com.notsy.dto.request;

import jakarta.validation.constraints.NotBlank;
import lombok.Data;

@Data
public class ChatRequest {
    @NotBlank(message = "Message is required")
    private String message;

    private String learningMode;

    private Boolean useWebSearch;

    private String explainDepth; // null, "eli5", "deep"

    private String systemPrompt; // For branch context injection
}
