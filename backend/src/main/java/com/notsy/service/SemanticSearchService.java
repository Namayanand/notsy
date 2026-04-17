package com.notsy.service;

import com.notsy.dto.response.SemanticSearchResponse;
import com.notsy.dto.response.SemanticSearchResponse.*;
import com.notsy.entity.*;
import com.notsy.repository.*;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.http.*;
import org.springframework.stereotype.Service;
import org.springframework.web.client.RestTemplate;

import java.util.*;
import java.util.stream.Collectors;

@Service
@RequiredArgsConstructor
@Slf4j
public class SemanticSearchService {

    private final NotebookRepository notebookRepository;
    private final TopicRepository topicRepository;
    private final ResourceRepository resourceRepository;
    private final ConversationRepository conversationRepository;
    private final MessageRepository messageRepository;

    private static final String AI_SERVICE_URL = System.getenv("AI_SERVICE_URL") != null
        ? System.getenv("AI_SERVICE_URL") : "http://localhost:8000";

    public SemanticSearchResponse search(String query, Long notebookId, Long userId, int limit) {
        List<SearchResult> results = new ArrayList<>();

        try {
            // Call AI service for vector similarity search
            RestTemplate restTemplate = new RestTemplate();
            HttpHeaders headers = new HttpHeaders();
            headers.setContentType(MediaType.APPLICATION_JSON);

            Map<String, Object> requestBody = new HashMap<>();
            requestBody.put("query", query);
            requestBody.put("limit", limit);
            requestBody.put("user_id", userId);
            if (notebookId != null) {
                requestBody.put("notebook_id", notebookId);
            }

            HttpEntity<Map<String, Object>> entity = new HttpEntity<>(requestBody, headers);
            ResponseEntity<Map> response = restTemplate.exchange(
                AI_SERVICE_URL + "/search/semantic",
                HttpMethod.POST,
                entity,
                Map.class
            );

            if (response.getBody() != null && response.getBody().get("results") != null) {
                @SuppressWarnings("unchecked")
                List<Map<String, Object>> aiResults = (List<Map<String, Object>>) response.getBody().get("results");

                for (Map<String, Object> r : aiResults) {
                    String type = (String) r.getOrDefault("type", "topic");
                    Long id = ((Number) r.get("id")).longValue();
                    String title = (String) r.get("title");
                    String snippet = (String) r.getOrDefault("snippet", "");
                    Float score = r.get("score") != null ? ((Number) r.get("score")).floatValue() : 0f;

                    Long resultNotebookId = notebookId;
                    if (r.get("notebook_id") != null) {
                        resultNotebookId = ((Number) r.get("notebook_id")).longValue();
                    }

                    results.add(SearchResult.builder()
                        .type(type)
                        .id(id)
                        .notebookId(resultNotebookId)
                        .title(title)
                        .snippet(snippet)
                        .score(score)
                        .build());
                }
            }
        } catch (Exception e) {
            log.error("Semantic search failed, falling back to basic search: {}", e.getMessage());
            // Fallback: basic text search across entities
            results = basicSearch(query, notebookId, userId, limit);
        }

        // Sort by score descending
        results.sort((a, b) -> Float.compare(b.getScore(), a.getScore()));

        return SemanticSearchResponse.builder()
            .results(results)
            .build();
    }

    private List<SearchResult> basicSearch(String query, Long notebookId, Long userId, int limit) {
        List<SearchResult> results = new ArrayList<>();
        String lowerQuery = query.toLowerCase();

        // Search topics
        List<Topic> topics = notebookId != null
            ? topicRepository.findByNotebookIdOrderByOrderIndexAsc(notebookId)
            : topicRepository.findAll();
        for (Topic t : topics) {
            if (results.size() >= limit) break;
            if (t.getTitle().toLowerCase().contains(lowerQuery) ||
                (t.getDescription() != null && t.getDescription().toLowerCase().contains(lowerQuery))) {
                results.add(SearchResult.builder()
                    .type("topic")
                    .id(t.getId())
                    .notebookId(t.getNotebook().getId())
                    .title(t.getTitle())
                    .snippet(t.getDescription() != null ? t.getDescription().substring(0, Math.min(200, t.getDescription().length())) : "")
                    .score(1.0f)
                    .build());
            }
        }

        // Search resources
        List<Resource> resources = resourceRepository.findByUserId(userId);
        for (Resource r : resources) {
            if (results.size() >= limit) break;
            if (r.getOriginalName().toLowerCase().contains(lowerQuery)) {
                results.add(SearchResult.builder()
                    .type("resource")
                    .id(r.getId())
                    .notebookId(r.getTopic().getNotebook().getId())
                    .title(r.getOriginalName())
                    .snippet(r.getFileType().name())
                    .score(0.9f)
                    .build());
            }
        }

        return results;
    }
}
