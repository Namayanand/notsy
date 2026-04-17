package com.notsy.service;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.notsy.dto.request.CreateFlashcardRequest;
import com.notsy.dto.request.ReviewFlashcardRequest;
import com.notsy.dto.response.FlashcardResponse;
import com.notsy.entity.Flashcard;
import com.notsy.entity.Topic;
import com.notsy.entity.User;
import com.notsy.exception.ResourceNotFoundException;
import com.notsy.repository.FlashcardRepository;
import com.notsy.repository.TopicRepository;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.data.domain.PageRequest;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.time.LocalDateTime;
import java.util.List;
import java.util.stream.Collectors;

@Service
@RequiredArgsConstructor
@Slf4j
public class FlashcardService {

    private final FlashcardRepository flashcardRepository;
    private final TopicRepository topicRepository;
    private final ObjectMapper objectMapper;

    @Transactional(readOnly = true)
    public List<FlashcardResponse> getFlashcardsByTopic(Long topicId, User user) {
        return flashcardRepository.findByTopicIdOrderByCreatedAtDesc(topicId)
            .stream()
            .filter(c -> c.getUser().getId().equals(user.getId()))
            .map(this::toResponse)
            .collect(Collectors.toList());
    }

    @Transactional(readOnly = true)
    public List<FlashcardResponse> getDueCards(Long topicId, User user) {
        LocalDateTime now = LocalDateTime.now();
        List<Flashcard> dueCards = topicId != null
            ? flashcardRepository.findDueCards(topicId, user.getId(), now, PageRequest.of(0, 20))
            : flashcardRepository.findAllDueCards(user.getId(), now, PageRequest.of(0, 20));

        return dueCards.stream().map(this::toResponse).collect(Collectors.toList());
    }

    @Transactional(readOnly = true)
    public List<FlashcardResponse> getAllCards(User user) {
        return flashcardRepository.findByUserIdOrderByCreatedAtDesc(user.getId())
            .stream().map(this::toResponse).collect(Collectors.toList());
    }

    @Transactional
    public FlashcardResponse createFlashcard(CreateFlashcardRequest request, User user) {
        Topic topic = topicRepository.findByIdAndUserId(request.getTopicId(), user.getId())
            .orElseThrow(() -> new ResourceNotFoundException("Topic", request.getTopicId()));

        Flashcard card = Flashcard.builder()
            .front(request.getFront())
            .back(request.getBack())
            .cardType(request.getCardType() != null
                ? Flashcard.CardType.valueOf(request.getCardType().toUpperCase())
                : Flashcard.CardType.BASIC)
            .topic(topic)
            .user(user)
            .isShared(request.getIsShared() != null && request.getIsShared())
            .difficultyTier(2)
            .build();

        card = flashcardRepository.save(card);
        return toResponse(card);
    }

    @Transactional
    public FlashcardResponse reviewFlashcard(Long cardId, ReviewFlashcardRequest request, User user) {
        Flashcard card = flashcardRepository.findById(cardId)
            .orElseThrow(() -> new ResourceNotFoundException("Flashcard", cardId));

        if (!card.getUser().getId().equals(user.getId())) {
            throw new ResourceNotFoundException("Flashcard", cardId);
        }

        // SM-2 algorithm update
        card.updateSM2(request.getQuality());

        if (request.getUserAnswer() != null) {
            card.setLastQuality(request.getQuality());
        }

        card = flashcardRepository.save(card);
        return toResponse(card);
    }

    @Transactional
    public void deleteFlashcard(Long cardId, User user) {
        Flashcard card = flashcardRepository.findById(cardId)
            .orElseThrow(() -> new ResourceNotFoundException("Flashcard", cardId));

        if (!card.getUser().getId().equals(user.getId())) {
            throw new ResourceNotFoundException("Flashcard", cardId);
        }

        flashcardRepository.delete(card);
    }

    @Transactional(readOnly = true)
    public List<FlashcardResponse> getSharedCards(User user) {
        return flashcardRepository.findCardsSharedByUser(user.getId())
            .stream().map(this::toResponse).collect(Collectors.toList());
    }

    private FlashcardResponse toResponse(Flashcard card) {
        return FlashcardResponse.builder()
            .id(card.getId())
            .front(card.getFront())
            .back(card.getBack())
            .cardType(card.getCardType().name())
            .easeFactor(card.getEaseFactor())
            .intervalDays(card.getIntervalDays())
            .repetitions(card.getRepetitions())
            .nextReviewDate(card.getNextReviewDate())
            .lastReviewDate(card.getLastReviewDate())
            .difficultyTier(card.getDifficultyTier())
            .topicId(card.getTopic() != null ? card.getTopic().getId() : null)
            .userId(card.getUser().getId())
            .isShared(card.getIsShared())
            .createdAt(card.getCreatedAt())
            .build();
    }
}
