package com.notsy.dto.request;

import jakarta.validation.constraints.NotBlank;
import lombok.Data;

@Data
public class CreateBranchRequest {
    @NotBlank(message = "Branch context is required")
    private String branchContext;

    private String learningMode;
}
