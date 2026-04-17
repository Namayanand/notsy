package com.notsy.dto.request;

import jakarta.validation.constraints.Max;
import jakarta.validation.constraints.Min;
import jakarta.validation.constraints.NotNull;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class ReviewFlashcardRequest {

    @NotNull(message = "Quality rating is required (0-5)")
    @Min(value = 0, message = "Quality must be between 0 and 5")
    @Max(value = 5, message = "Quality must be between 0 and 5")
    private Integer quality;

    private String userAnswer;
}
