package com.notsy.controller;

import com.notsy.entity.User;
import com.notsy.dto.response.StreakResponse;
import com.notsy.service.StreakService;
import lombok.RequiredArgsConstructor;
import org.springframework.http.ResponseEntity;
import org.springframework.security.core.annotation.AuthenticationPrincipal;
import org.springframework.web.bind.annotation.*;

import java.util.List;

@RestController
@RequestMapping("/api/streaks")
@RequiredArgsConstructor
public class StreakController {

    private final StreakService streakService;

    @GetMapping("/global")
    public ResponseEntity<StreakResponse> getGlobalStreak(@AuthenticationPrincipal User user) {
        return ResponseEntity.ok(streakService.getGlobalStreak(user.getId()));
    }

    @GetMapping("/topic/{topicId}")
    public ResponseEntity<StreakResponse> getTopicStreak(
            @PathVariable Long topicId,
            @AuthenticationPrincipal User user) {
        return ResponseEntity.ok(streakService.getTopicStreak(user.getId(), topicId));
    }

    @GetMapping
    public ResponseEntity<List<StreakResponse>> getAllStreaks(@AuthenticationPrincipal User user) {
        return ResponseEntity.ok(streakService.getAllStreaks(user.getId()));
    }

    @PostMapping("/topic/{topicId}/review")
    public ResponseEntity<Void> recordReview(
            @PathVariable Long topicId,
            @AuthenticationPrincipal User user) {
        streakService.recordReview(user.getId(), topicId);
        return ResponseEntity.ok().build();
    }
}
