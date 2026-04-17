package com.notsy.dto.response;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.time.LocalDateTime;
import java.util.List;

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class QuizResponse {

    private Long id;
    private String title;
    private String quizType;
    private Long topicId;
    private Integer totalScore;
    private Integer maxScore;
    private Integer difficultyTier;
    private List<QuizQuestionResponse> questions;
    private LocalDateTime completedAt;
    private LocalDateTime createdAt;
}
