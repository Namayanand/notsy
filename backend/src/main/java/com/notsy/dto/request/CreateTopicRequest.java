package com.notsy.dto.request;

import jakarta.validation.constraints.NotBlank;
import lombok.Data;

@Data
public class CreateTopicRequest {
    @NotBlank(message = "Title is required")
    private String title;

    private String description;

    private Long parentTopicId;

    private Integer orderIndex;

    private java.util.List<String> tags;
}
