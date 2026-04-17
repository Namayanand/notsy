package com.notsy.controller;

import com.notsy.entity.User;
import com.notsy.dto.request.CreateQuizRequest;
import com.notsy.dto.request.SubmitQuizAnswerRequest;
import com.notsy.dto.response.QuizResponse;
import com.notsy.service.QuizService;
import lombok.RequiredArgsConstructor;
import org.springframework.http.ResponseEntity;
import org.springframework.security.core.annotation.AuthenticationPrincipal;
import org.springframework.web.bind.annotation.*;

import java.util.List;

@RestController
@RequestMapping("/api/quizzes")
@RequiredArgsConstructor
public class QuizController {

    private final QuizService quizService;

    @PostMapping("/generate")
    public ResponseEntity<QuizResponse> generateQuiz(
            @RequestBody CreateQuizRequest request,
            @AuthenticationPrincipal User user) {
        return ResponseEntity.ok(quizService.generateQuiz(request, user));
    }

    @GetMapping("/topic/{topicId}")
    public ResponseEntity<List<QuizResponse>> getQuizzesByTopic(
            @PathVariable Long topicId,
            @AuthenticationPrincipal User user) {
        return ResponseEntity.ok(quizService.getQuizzesByTopic(topicId, user));
    }

    @GetMapping("/{quizId}")
    public ResponseEntity<QuizResponse> getQuiz(
            @PathVariable Long quizId,
            @AuthenticationPrincipal User user) {
        return ResponseEntity.ok(quizService.getQuiz(quizId, user));
    }

    @PostMapping("/{quizId}/answer")
    public ResponseEntity<QuizResponse> submitAnswer(
            @PathVariable Long quizId,
            @RequestBody SubmitQuizAnswerRequest request,
            @AuthenticationPrincipal User user) {
        return ResponseEntity.ok(quizService.submitAnswer(quizId, request, user));
    }

    @PostMapping("/{quizId}/complete")
    public ResponseEntity<QuizResponse> completeQuiz(
            @PathVariable Long quizId,
            @AuthenticationPrincipal User user) {
        return ResponseEntity.ok(quizService.completeQuiz(quizId, user));
    }

    @GetMapping("/topic/{topicId}/weak-areas")
    public ResponseEntity<List<String>> getWeakAreas(
            @PathVariable Long topicId,
            @AuthenticationPrincipal User user) {
        return ResponseEntity.ok(quizService.getWeakAreas(topicId, user));
    }
}
