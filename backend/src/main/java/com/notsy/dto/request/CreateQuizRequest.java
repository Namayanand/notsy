package com.notsy.dto.request;

import jakarta.validation.constraints.NotNull;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.util.List;
import java.util.Map;

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class CreateQuizRequest {

    private String title;

    private String quizType; // MIXED, MCQ, SHORT_ANSWER, DEFINITION_RECALL

    @NotNull(message = "Topic ID is required")
    private Long topicId;

    private Integer difficultyTier; // 1=easy, 2=medium, 3=hard

    private Integer questionCount; // default 10
}
