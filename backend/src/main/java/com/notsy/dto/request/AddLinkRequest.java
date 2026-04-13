package com.notsy.dto.request;

import jakarta.validation.constraints.NotBlank;
import lombok.Data;

@Data
public class AddLinkRequest {
    @NotBlank(message = "Source URL is required")
    private String sourceUrl;

    private String title;
}
