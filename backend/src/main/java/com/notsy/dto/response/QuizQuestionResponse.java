package com.notsy.dto.response;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class QuizQuestionResponse {
    private Long id;
    private String question;
    private String questionType;
    private String answer; // Only shown after submission
    private String options; // JSON array for MCQ
    private Boolean isCorrect;
    private String userAnswer;
    private Integer difficultyTier;
    private String areaCovered;
}