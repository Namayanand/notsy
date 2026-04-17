package com.notsy.controller;

import com.notsy.entity.User;
import com.notsy.dto.request.CreateFlashcardRequest;
import com.notsy.dto.request.ReviewFlashcardRequest;
import com.notsy.dto.response.FlashcardResponse;
import com.notsy.service.FlashcardService;
import lombok.RequiredArgsConstructor;
import org.springframework.http.ResponseEntity;
import org.springframework.security.core.annotation.AuthenticationPrincipal;
import org.springframework.web.bind.annotation.*;

import java.util.List;

@RestController
@RequestMapping("/api/flashcards")
@RequiredArgsConstructor
public class FlashcardController {

    private final FlashcardService flashcardService;

    @GetMapping
    public ResponseEntity<List<FlashcardResponse>> getMyFlashcards(@AuthenticationPrincipal User user) {
        return ResponseEntity.ok(flashcardService.getAllCards(user));
    }

    @GetMapping("/topic/{topicId}")
    public ResponseEntity<List<FlashcardResponse>> getFlashcardsByTopic(
            @PathVariable Long topicId,
            @AuthenticationPrincipal User user) {
        return ResponseEntity.ok(flashcardService.getFlashcardsByTopic(topicId, user));
    }

    @GetMapping("/due")
    public ResponseEntity<List<FlashcardResponse>> getDueCards(
            @RequestParam(required = false) Long topicId,
            @AuthenticationPrincipal User user) {
        return ResponseEntity.ok(flashcardService.getDueCards(topicId, user));
    }

    @PostMapping
    public ResponseEntity<FlashcardResponse> createFlashcard(
            @RequestBody CreateFlashcardRequest request,
            @AuthenticationPrincipal User user) {
        return ResponseEntity.ok(flashcardService.createFlashcard(request, user));
    }

    @PostMapping("/{cardId}/review")
    public ResponseEntity<FlashcardResponse> reviewFlashcard(
            @PathVariable Long cardId,
            @RequestBody ReviewFlashcardRequest request,
            @AuthenticationPrincipal User user) {
        return ResponseEntity.ok(flashcardService.reviewFlashcard(cardId, request, user));
    }

    @DeleteMapping("/{cardId}")
    public ResponseEntity<Void> deleteFlashcard(
            @PathVariable Long cardId,
            @AuthenticationPrincipal User user) {
        flashcardService.deleteFlashcard(cardId, user);
        return ResponseEntity.noContent().build();
    }

    @GetMapping("/shared")
    public ResponseEntity<List<FlashcardResponse>> getSharedCards(@AuthenticationPrincipal User user) {
        return ResponseEntity.ok(flashcardService.getSharedCards(user));
    }
}
