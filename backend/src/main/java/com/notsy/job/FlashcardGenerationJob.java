package com.notsy.job;

import com.notsy.entity.Flashcard;
import com.notsy.entity.Conversation;
import com.notsy.entity.User;
import com.notsy.repository.FlashcardRepository;
import com.notsy.repository.UserRepository;
import lombok.extern.slf4j.Slf4j;
import org.quartz.Job;
import org.quartz.JobExecutionContext;
import org.quartz.JobExecutionException;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.web.client.RestTemplate;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.springframework.stereotype.Component;

import java.util.*;

@Component
@Slf4j
public class FlashcardGenerationJob implements Job {

    @Autowired
    private FlashcardRepository flashcardRepository;

    @Autowired
    private UserRepository userRepository;

    @Autowired
    private ObjectMapper objectMapper;

    private static final String AI_SERVICE_URL = System.getenv("AI_SERVICE_URL") != null
        ? System.getenv("AI_SERVICE_URL") : "http://localhost:8000";

    @Override
    public void execute(JobExecutionContext context) throws JobExecutionException {
        Long conversationId = context.getJobDetail().getJobDataMap().getLong("conversationId");
        Long topicId = context.getJobDetail().getJobDataMap().getLong("topicId");
        Long userId = context.getJobDetail().getJobDataMap().getLong("userId");

        log.info("Executing FlashcardGenerationJob for conversation {} topic {} user {}", conversationId, topicId, userId);

        try {
            User user = userRepository.findById(userId).orElse(null);
            if (user == null) {
                throw new JobExecutionException("User not found");
            }

            // Build prompt for flashcard generation
            String prompt = buildFlashcardPrompt(conversationId, topicId, userId);

            RestTemplate restTemplate = new RestTemplate();
            Map<String, Object> requestBody = new HashMap<>();
            requestBody.put("prompt", prompt);
            requestBody.put("mode", "flashcard_generation");

            Map<String, Object> response = restTemplate.postForObject(
                AI_SERVICE_URL + "/generate_flashcards",
                requestBody,
                Map.class
            );

            if (response != null && response.get("flashcards") != null) {
                List<Map<String, Object>> cards = (List<Map<String, Object>>) response.get("flashcards");
                for (Map<String, Object> cardData : cards) {
                    Flashcard card = Flashcard.builder()
                        .front((String) cardData.get("front"))
                        .back((String) cardData.get("back"))
                        .cardType(Flashcard.CardType.valueOf(
                            cardData.getOrDefault("type", "BASIC").toString().toUpperCase()))
                        .topic(null) // Set after lookup
                        .user(user)
                        .difficultyTier(2)
                        .build();
                    flashcardRepository.save(card);
                }
                log.info("Generated {} flashcards for conversation {} topic {}",
                    cards.size(), conversationId, topicId);
            }
        } catch (Exception e) {
            log.error("FlashcardGenerationJob failed for conversation {}: {}", conversationId, e.getMessage());
            throw new JobExecutionException(e);
        }
    }

    private String buildFlashcardPrompt(Long conversationId, Long topicId, Long userId) {
        return String.format(
            "Generate 5-10 smart flashcards from the conversation (ID: %d) for topic ID: %d. " +
            "Create varied cards: basic Q&A, multiple choice, definitions, and short answer. " +
            "Format as JSON: [{\"front\": \"...\", \"back\": \"...\", \"type\": \"BASIC|MULTIPLE_CHOICE|DEFINITION|SHORT_ANSWER\"}]",
            conversationId, topicId
        );
    }
}
