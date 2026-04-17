package com.notsy.dto.response;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.time.LocalDate;
import java.time.LocalDateTime;

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class StreakResponse {

    private Long id;
    private Long topicId;
    private Boolean isGlobal;
    private Integer currentStreak;
    private Integer longestStreak;
    private LocalDate lastReviewDate;
    private Integer reviewCount;
    private Integer totalReviews;
    private LocalDateTime updatedAt;
}
