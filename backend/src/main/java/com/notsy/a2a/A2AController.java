package com.notsy.a2a;

import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.http.MediaType;
import org.springframework.http.ResponseEntity;
import org.springframework.security.core.annotation.AuthenticationPrincipal;
import org.springframework.web.bind.annotation.*;
import reactor.core.publisher.Flux;
import reactor.core.publisher.Mono;

import java.util.Map;

/**
 * A2A Controller - exposes A2A endpoints to the frontend
 */
@RestController
@RequestMapping("/api/a2a")
@RequiredArgsConstructor
@Slf4j
public class A2AController {

    private final A2AGatewayService gatewayService;

    /**
     * Send a task to the orchestrator
     */
    @PostMapping("/tasks/send")
    public Mono<ResponseEntity<A2ATaskResponse>> sendTask(
            @RequestBody Map<String, Object> request,
            @AuthenticationPrincipal org.springframework.security.core.userdetails.User user) {

        String skill = request.containsKey("skill") ? request.get("skill").toString() : "auto";
        Map<String, Object> input = (Map<String, Object>) request.getOrDefault("input", Map.of());
        String sessionId = request.containsKey("sessionId") ? request.get("sessionId").toString() : null;
        String userId = user != null ? user.getUsername() : "anonymous";

        log.info("Received task request with skill: {}", skill);

        return gatewayService.sendTask(skill, input, userId, sessionId)
                .map(ResponseEntity::ok)
                .defaultIfEmpty(ResponseEntity.badRequest().build());
    }

    /**
     * Get task status
     */
    @GetMapping("/tasks/{taskId}")
    public Mono<ResponseEntity<A2ATaskResponse>> getTask(@PathVariable String taskId) {
        return gatewayService.getTaskStatus(taskId)
                .map(ResponseEntity::ok)
                .defaultIfEmpty(ResponseEntity.notFound().build());
    }

    /**
     * Stream task updates via SSE
     */
    @GetMapping("/tasks/{taskId}/stream")
    public Flux<String> streamTask(@PathVariable String taskId) {
        log.info("Streaming task: {}", taskId);
        return gatewayService.streamTask(taskId)
                .map(data -> "data: " + data + "\n\n")
                .concatWith(Flux.just("data: {\"event\":\"done\"}\n\n"));
    }

    /**
     * Cancel a task
     */
    @DeleteMapping("/tasks/{taskId}")
    public Mono<ResponseEntity<Map<String, Object>>> cancelTask(@PathVariable String taskId) {
        return gatewayService.cancelTask(taskId)
                .map(response -> ResponseEntity.ok(Map.<String, Object>of(
                        "taskId", taskId,
                        "status", "cancelled"
                )))
                .defaultIfEmpty(ResponseEntity.<Map<String, Object>>notFound().build());
    }

    /**
     * Get agent registry - all discovered agents
     */
    @GetMapping("/registry")
    public Mono<ResponseEntity<Map<String, Object>>> getRegistry() {
        return gatewayService.getAgentRegistry()
                .map(ResponseEntity::ok)
                .defaultIfEmpty(ResponseEntity.ok(Map.of()));
    }

    /**
     * Health check - proxy to orchestrator for aggregated status
     */
    @GetMapping("/health")
    public Mono<ResponseEntity<Map<String, Object>>> health() {
        return gatewayService.getOrchestratorHealth()
                .map(ResponseEntity::ok)
                .defaultIfEmpty(ResponseEntity.ok(Map.of(
                        "status", "healthy",
                        "orchestrator", Map.of("status", "unknown"),
                        "agents", Map.of(),
                        "system_status", "unknown",
                        "total_tasks_processed", 0
                )));
    }
}