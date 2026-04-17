package com.notsy.dto.request;

import jakarta.validation.constraints.NotBlank;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class SemanticSearchRequest {

    @NotBlank(message = "Query is required")
    private String query;

    private Integer limit; // default 10

    private Long notebookId; // optional: scope to specific notebook
}
