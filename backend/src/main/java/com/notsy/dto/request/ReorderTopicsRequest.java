package com.notsy.dto.request;

import jakarta.validation.constraints.NotNull;
import lombok.Data;

import java.util.List;

@Data
public class ReorderTopicsRequest {
    @NotNull(message = "Topic IDs are required")
    private List<Long> topicIds;
}
