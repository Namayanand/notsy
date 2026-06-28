package com.notsy.service;

import com.fasterxml.jackson.core.type.TypeReference;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.notsy.dto.response.EmbedStatusResponse;
import com.notsy.entity.Resource;
import com.notsy.entity.Resource.EmbeddingStatus;
import com.notsy.repository.ResourceRepository;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.http.HttpStatusCode;
import org.springframework.http.MediaType;
import org.springframework.stereotype.Service;
import org.springframework.web.reactive.function.BodyInserters;
import org.springframework.web.reactive.function.client.WebClient;
import reactor.core.publisher.Mono;

import java.util.Collections;
import java.util.List;
import java.util.Map;

@Service
@RequiredArgsConstructor
@Slf4j
public class AIProxyService {

    private final WebClient aiServiceWebClient;
    private final ResourceRepository resourceRepository;
    private final ObjectMapper objectMapper;

    @Value("${app.ai.service-url}")
    private String aiServiceUrl;

    @Value("${spring-boot.callback-url:http://localhost:8080}")
    private String springBootCallbackUrl;

    public void embedResource(Long resourceId, Long topicId, String filePath, String sourceUrl, String fileType, Long userId) {
        Map<String, Object> requestBody = new java.util.HashMap<>();
        requestBody.put("resource_id", resourceId);
        requestBody.put("topic_id", topicId);
        requestBody.put("file_path", filePath);
        requestBody.put("source_url", sourceUrl);
        requestBody.put("file_type", fileType);
        requestBody.put("user_id", userId);

        aiServiceWebClient.post()
                .uri("/embed")
                .contentType(MediaType.APPLICATION_JSON)
                .body(BodyInserters.fromValue(requestBody))
                .retrieve()
                .onStatus(HttpStatusCode::isError, response -> {
                    log.error("Failed to trigger embedding, status: {}", response.statusCode());
                    updateResourceStatus(resourceId, EmbeddingStatus.FAILED, null);
                    return Mono.error(new RuntimeException("Failed to trigger embedding"));
                })
                .bodyToMono(Map.class)
                .doOnSuccess(result -> log.info("Embedding triggered for resource {}", resourceId))
                .doOnError(error -> {
                    log.error("Error triggering embedding for resource {}", resourceId, error);
                    updateResourceStatus(resourceId, EmbeddingStatus.FAILED, null);
                })
                .subscribe();
    }

    public AIProxyService.ChatResponse chat(Long topicId, String message, List<Map<String, String>> history, String learningMode) {
        return chat(topicId, message, history, learningMode, false, null, null);
    }

    public AIProxyService.ChatResponse chat(Long topicId, String message, List<Map<String, String>> history, String learningMode, boolean useWebSearch, String explainDepth) {
        return chat(topicId, message, history, learningMode, useWebSearch, explainDepth, null);
    }

    public AIProxyService.ChatResponse chat(Long topicId, String message, List<Map<String, String>> history, String learningMode, boolean useWebSearch, String explainDepth, String systemPrompt) {
        Map<String, Object> requestBody = new java.util.HashMap<>();
        requestBody.put("topic_id", topicId);
        requestBody.put("message", message);
        requestBody.put("history", history);
        requestBody.put("learning_mode", learningMode);
        requestBody.put("use_web_search", useWebSearch);
        requestBody.put("explain_depth", explainDepth);
        if (systemPrompt != null && !systemPrompt.isEmpty()) {
            requestBody.put("system_prompt", systemPrompt);
        }

        try {
            Map<String, Object> response = aiServiceWebClient.post()
                    .uri("/chat")
                    .contentType(MediaType.APPLICATION_JSON)
                    .body(BodyInserters.fromValue(requestBody))
                    .retrieve()
                    .onStatus(HttpStatusCode::isError, clientResponse ->
                            Mono.error(new RuntimeException("AI service error: " + clientResponse.statusCode())))
                    .bodyToMono(Map.class)
                    .block();

            if (response == null) {
                log.error("AI chat service returned an empty body (no error status). " +
                        "Likely an unfollowed redirect — verify AI_SERVICE_URL uses https:// and points at the AI service. URL={}", aiServiceUrl);
                return ChatResponse.builder()
                        .response("I apologize, but I encountered an error processing your request. Please try again.")
                        .sources(Collections.emptyList())
                        .tokensUsed(0)
                        .build();
            }

            String responseText = (String) response.get("response");
            int tokensUsed = response.get("tokens_used") != null ? ((Number) response.get("tokens_used")).intValue() : 0;

            List<SourceData> sources = Collections.emptyList();
            if (response.get("sources") != null) {
                sources = objectMapper.convertValue(response.get("sources"), new TypeReference<List<SourceData>>() {});
            }

            return ChatResponse.builder()
                    .response(responseText)
                    .sources(sources)
                    .tokensUsed(tokensUsed)
                    .build();
        } catch (Exception e) {
            log.error("Error calling AI chat service", e);
            return ChatResponse.builder()
                    .response("I apologize, but I encountered an error processing your request. Please try again.")
                    .sources(Collections.emptyList())
                    .tokensUsed(0)
                    .build();
        }
    }

    public List<RelationData> generateGraph(Long notebookId, List<TopicData> topics) {
        Map<String, Object> requestBody = new java.util.HashMap<>();
        requestBody.put("notebook_id", notebookId);
        requestBody.put("topics", topics);

        try {
            Map<String, Object> response = aiServiceWebClient.post()
                    .uri("/graph/generate")
                    .contentType(MediaType.APPLICATION_JSON)
                    .body(BodyInserters.fromValue(requestBody))
                    .retrieve()
                    .onStatus(HttpStatusCode::isError, clientResponse ->
                            Mono.error(new RuntimeException("AI service error: " + clientResponse.statusCode())))
                    .bodyToMono(Map.class)
                    .block();

            if (response != null && response.get("relations") != null) {
                return objectMapper.convertValue(response.get("relations"), new TypeReference<List<RelationData>>() {});
            }
        } catch (Exception e) {
            log.error("Error calling AI graph generation service", e);
        }

        return Collections.emptyList();
    }

    public void deleteTopicEmbeddings(Long topicId) {
        try {
            aiServiceWebClient.delete()
                    .uri("/embed/topic/" + topicId)
                    .retrieve()
                    .bodyToMono(Map.class)
                    .doOnSuccess(result -> log.info("Deleted embeddings for topic {}", topicId))
                    .doOnError(error -> log.error("Error deleting embeddings for topic {}", topicId, error))
                    .subscribe();
        } catch (Exception e) {
            log.error("Error calling AI service to delete topic embeddings", e);
        }
    }

    public EmbedStatusResponse getEmbedStatus(Long resourceId) {
        try {
            Map<String, Object> response = aiServiceWebClient.get()
                    .uri("/embed/status/" + resourceId)
                    .retrieve()
                    .bodyToMono(Map.class)
                    .block();

            if (response != null) {
                String status = (String) response.get("status");
                Integer chunkCount = response.get("chunk_count") != null ? ((Number) response.get("chunk_count")).intValue() : null;
                return EmbedStatusResponse.builder()
                        .resourceId(resourceId)
                        .status(status)
                        .chunkCount(chunkCount)
                        .build();
            }
        } catch (Exception e) {
            log.error("Error getting embed status for resource {}", resourceId, e);
        }

        // Fallback to DB status
        Resource resource = resourceRepository.findById(resourceId).orElse(null);
        if (resource != null) {
            return EmbedStatusResponse.builder()
                    .resourceId(resourceId)
                    .status(resource.getEmbeddingStatus().name())
                    .chunkCount(resource.getChunkCount())
                    .build();
        }

        return EmbedStatusResponse.builder()
                .resourceId(resourceId)
                .status("UNKNOWN")
                .chunkCount(null)
                .build();
    }

    private void updateResourceStatus(Long resourceId, EmbeddingStatus status, Integer chunkCount) {
        try {
            resourceRepository.findById(resourceId).ifPresent(resource -> {
                resource.setEmbeddingStatus(status);
                if (chunkCount != null) {
                    resource.setChunkCount(chunkCount);
                }
                resourceRepository.save(resource);
            });
        } catch (Exception e) {
            log.error("Error updating resource status for resource {}", resourceId, e);
        }
    }

    @Data
    @Builder
    @AllArgsConstructor
    @lombok.NoArgsConstructor
    public static class ChatResponse {
        private String response;
        private List<SourceData> sources;
        private int tokensUsed;
    }

    @Data
    @Builder
    @AllArgsConstructor
    @lombok.NoArgsConstructor
    public static class SourceData {
        private String filename;
        private String chunk;
        private double score;
    }

    @Data
    @AllArgsConstructor
    @lombok.NoArgsConstructor
    public static class TopicData {
        private Long id;
        private String title;
        private String description;
    }

    @Data
    @Builder
    @AllArgsConstructor
    @lombok.NoArgsConstructor
    public static class RelationData {
        private Long sourceTopicId;
        private Long targetTopicId;
        private String relationshipType;
        private float strength;
        private String description;
    }
}
