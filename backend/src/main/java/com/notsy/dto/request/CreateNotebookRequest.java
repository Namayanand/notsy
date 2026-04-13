package com.notsy.dto.request;

import jakarta.validation.constraints.NotBlank;
import lombok.Data;

@Data
public class CreateNotebookRequest {
    @NotBlank(message = "Title is required")
    private String title;

    private String description;

    private String colorTheme;

    private Boolean isPublic = false;
}
