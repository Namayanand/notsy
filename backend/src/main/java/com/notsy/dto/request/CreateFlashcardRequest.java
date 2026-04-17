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
public class CreateFlashcardRequest {

    @NotBlank(message = "Front of card is required")
    private String front;

    @NotBlank(message = "Back of card is required")
    private String back;

    private String cardType; // BASIC, MULTIPLE_CHOICE, DEFINITION, SHORT_ANSWER

    private Long topicId;

    private Boolean isShared;
}
