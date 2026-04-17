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
public class FlashcardResponse {

    private Long id;
    private String front;
    private String back;
    private String cardType;
    private Float easeFactor;
    private Integer intervalDays;
    private Integer repetitions;
    private LocalDateTime nextReviewDate;
    private LocalDateTime lastReviewDate;
    private Integer difficultyTier;
    private Long topicId;
    private Long userId;
    private Boolean isShared;
    private LocalDateTime createdAt;
}

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
class FlashcardListResponse {
    private List<FlashcardResponse> cards;
    private long totalDue;
    private long totalReviewed;
}
