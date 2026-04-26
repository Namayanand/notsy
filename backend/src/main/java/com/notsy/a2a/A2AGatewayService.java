package com.notsy.a2a;

import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.core.ParameterizedTypeReference;
import org.springframework.http.MediaType;
import org.springframework.stereotype.Service;
import org.springframework.web.reactive.function.client.WebClient;
import reactor.core.publisher.Flux;
import reactor.core.publisher.Mono;

import java.util.Collections;
import java.util.List;
import java.util.Map;

/**
 * A2A Gateway Service - communicates with AI Service agents via A2A protocol
 */
@Service
@RequiredArgsConstructor
@Slf4j
public class A2AGatewayService {

    @Value("${notsy.ai-service.url:http://localhost:8000}")
    private String orchestratorUrl;

    private final WebClient aiServiceWebClient;

    /**
     * Send a task to the orchestrator agent
     */
    public Mono<A2ATaskResponse> sendTask(
            String skill,
            Map<String, Object> input,
            String userId,
            String sessionId) {

        A2ATaskRequest request = A2ATaskRequest.builder()
                .taskId(java.util.UUID.randomUUID().toString())
                .skill(A2ATaskRequest.A2ASkill.builder().id(skill).build())
                .message(A2ATaskRequest.A2AMessage.builder()
                        .role("user")
                        .content(input.get("content") != null ? input.get("content").toString() : "")
                        .metadata(Map.of(
                                "user_id", userId,
                                "session_id", sessionId != null ? sessionId : ""
                        ))
                        .build())
                .build();

        log.info("Sending task to orchestrator with skill: {}", skill);

        return aiServiceWebClient.post()
                .uri(orchestratorUrl + "/tasks/send")
                .contentType(MediaType.APPLICATION_JSON)
                .bodyValue(request)
                .retrieve()
                .bodyToMono(A2ATaskResponse.class)
                .doOnSuccess(response -> log.info("Task sent successfully: {}", response.getId()))
                .doOnError(error -> log.error("Failed to send task: {}", error.getMessage()));
    }

    /**
     * Poll task status
     */
    public Mono<A2ATaskResponse> getTaskStatus(String taskId) {
        return aiServiceWebClient.get()
                .uri(orchestratorUrl + "/tasks/{taskId}", taskId)
                .retrieve()
                .bodyToMono(A2ATaskResponse.class);
    }

    /**
     * Stream task updates via SSE
     */
    public Flux<String> streamTask(String taskId) {
        return aiServiceWebClient.get()
                .uri(orchestratorUrl + "/tasks/{taskId}/stream", taskId)
                .accept(MediaType.TEXT_EVENT_STREAM)
                .retrieve()
                .bodyToFlux(String.class);
    }

    /**
     * Cancel a running task
     */
    public Mono<Map<String, Object>> cancelTask(String taskId) {
        return aiServiceWebClient.post()
                .uri(orchestratorUrl + "/tasks/cancel")
                .contentType(MediaType.APPLICATION_JSON)
                .bodyValue(Map.of("taskId", taskId))
                .retrieve()
                .bodyToMono(new ParameterizedTypeReference<Map<String, Object>>() {});
    }

    /**
     * Get agent registry - all discovered agents and their skills
     */
    public Mono<Map<String, Object>> getAgentRegistry() {
        return aiServiceWebClient.get()
                .uri(orchestratorUrl + "/registry")
                .retrieve()
                .bodyToMono(new ParameterizedTypeReference<Map<String, Object>>() {})
                .onErrorReturn(Collections.emptyMap());
    }

    /**
     * Get all agent cards from registry
     */
    public Mono<List<A2AAgentCard>> getAgentCards() {
        return getAgentRegistry()
                .map(registry -> {
                    List<A2AAgentCard> cards = new java.util.ArrayList<>();
                    List<Map<String, Object>> agents = (List<Map<String, Object>>) registry.get("agents");
                    if (agents != null) {
                        for (Map<String, Object> agent : agents) {
                            Map<String, Object> cardMap = (Map<String, Object>) agent.get("card");
                            if (cardMap != null) {
                                A2AAgentCard card = A2AAgentCard.builder()
                                        .name((String) cardMap.get("name"))
                                        .description((String) cardMap.get("description"))
                                        .version((String) cardMap.get("version"))
                                        .url((String) cardMap.get("url"))
                                        .build();
                                cards.add(card);
                            }
                        }
                    }
                    return cards;
                });
    }

    /**
     * Get orchestrator health - aggregated system health
     */
    public Mono<Map<String, Object>> getOrchestratorHealth() {
        return aiServiceWebClient.get()
                .uri(orchestratorUrl + "/health")
                .retrieve()
                .bodyToMono(new ParameterizedTypeReference<Map<String, Object>>() {})
                .onErrorReturn(Collections.emptyMap());
    }
}