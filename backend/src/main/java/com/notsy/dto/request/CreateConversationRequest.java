package com.notsy.dto.request;

import jakarta.validation.constraints.NotBlank;
import lombok.Data;

@Data
public class CreateConversationRequest {
    @NotBlank(message = "Title is required")
    private String title;

    private String learningMode;
}
