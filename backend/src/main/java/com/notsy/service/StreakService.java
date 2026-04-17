package com.notsy.service;

import com.notsy.dto.response.StreakResponse;
import com.notsy.entity.Streak;
import com.notsy.entity.Topic;
import com.notsy.entity.User;
import com.notsy.repository.StreakRepository;
import com.notsy.repository.TopicRepository;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.time.LocalDate;
import java.util.List;
import java.util.Optional;
import java.util.stream.Collectors;

@Service
@RequiredArgsConstructor
@Slf4j
public class StreakService {

    private final StreakRepository streakRepository;
    private final TopicRepository topicRepository;

    @Transactional
    public void recordReview(Long userId, Long topicId) {
        if (topicId != null) {
            // Per-topic streak
            Optional<Streak> existing = streakRepository.findByUserIdAndTopic_Id(userId, topicId);
            Streak streak;
            if (existing.isPresent()) {
                streak = existing.get();
                streak.recordReview();
            } else {
                Topic topic = topicRepository.findById(topicId).orElse(null);
                streak = Streak.builder()
                    .user(null) // Will be set via userId
                    .topic(topic)
                    .isGlobal(false)
                    .currentStreak(1)
                    .longestStreak(1)
                    .lastReviewDate(LocalDate.now())
                    .reviewCount(1)
                    .totalReviews(1)
                    .build();
            }
            streakRepository.save(streak);
        }

        // Update global streak
        Optional<Streak> globalExisting = streakRepository.findByUserIdAndIsGlobalTrue(userId);
        Streak globalStreak;
        if (globalExisting.isPresent()) {
            globalStreak = globalExisting.get();
            globalStreak.recordReview();
        } else {
            globalStreak = Streak.builder()
                .isGlobal(true)
                .currentStreak(1)
                .longestStreak(1)
                .lastReviewDate(LocalDate.now())
                .reviewCount(1)
                .totalReviews(1)
                .build();
        }
        streakRepository.save(globalStreak);
    }

    @Transactional(readOnly = true)
    public StreakResponse getTopicStreak(Long userId, Long topicId) {
        return streakRepository.findByUserIdAndTopic_Id(userId, topicId)
            .map(this::toResponse)
            .orElse(StreakResponse.builder()
                .topicId(topicId)
                .currentStreak(0)
                .longestStreak(0)
                .build());
    }

    @Transactional(readOnly = true)
    public StreakResponse getGlobalStreak(Long userId) {
        return streakRepository.findByUserIdAndIsGlobalTrue(userId)
            .map(this::toResponse)
            .orElse(StreakResponse.builder()
                .isGlobal(true)
                .currentStreak(0)
                .longestStreak(0)
                .build());
    }

    @Transactional(readOnly = true)
    public List<StreakResponse> getAllStreaks(Long userId) {
        return streakRepository.findByUserId(userId)
            .stream().map(this::toResponse).collect(Collectors.toList());
    }

    private StreakResponse toResponse(Streak streak) {
        return StreakResponse.builder()
            .id(streak.getId())
            .topicId(streak.getTopic() != null ? streak.getTopic().getId() : null)
            .isGlobal(streak.getIsGlobal())
            .currentStreak(streak.getCurrentStreak())
            .longestStreak(streak.getLongestStreak())
            .lastReviewDate(streak.getLastReviewDate())
            .reviewCount(streak.getReviewCount())
            .totalReviews(streak.getTotalReviews())
            .updatedAt(streak.getUpdatedAt())
            .build();
    }
}
