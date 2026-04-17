package com.notsy.controller;

import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.http.*;
import org.springframework.web.bind.annotation.*;
import org.springframework.web.client.HttpClientErrorException;
import org.springframework.web.client.RestTemplate;

import java.util.Map;

@RestController
@RequestMapping("/agent")
@RequiredArgsConstructor
@Slf4j
public class AgentController {

    private final RestTemplate restTemplate;

    @Value("${app.ai.service-url:http://localhost:8000}")
    private String aiServiceUrl;

    @PostMapping("/start-session")
    public ResponseEntity<?> startSession(@RequestBody Map<String, Object> request) {
        return proxyRequest("/agent/start-session", request);
    }

    @PostMapping("/message")
    public ResponseEntity<?> sendMessage(@RequestBody Map<String, Object> request) {
        return proxyRequest("/agent/message", request);
    }

    @GetMapping("/state/{sessionId}")
    public ResponseEntity<?> getSessionState(@PathVariable String sessionId) {
        return proxyGetRequest("/agent/state/" + sessionId);
    }

    @GetMapping("/roadmap/{sessionId}")
    public ResponseEntity<?> getRoadmap(@PathVariable String sessionId) {
        return proxyGetRequest("/agent/roadmap/" + sessionId);
    }

    @PostMapping("/quiz/generate")
    public ResponseEntity<?> generateQuiz(
            @RequestParam String sessionId,
            @RequestParam String topic,
            @RequestParam(defaultValue = "medium") String difficulty,
            @RequestParam(defaultValue = "5") int numQuestions) {
        return proxyGetRequest(String.format("/agent/quiz/generate?session_id=%s&topic=%s&difficulty=%s&num_questions=%d",
                sessionId, topic, difficulty, numQuestions));
    }

    @PostMapping("/quiz/evaluate")
    public ResponseEntity<?> evaluateAnswer(@RequestBody Map<String, Object> request) {
        return proxyRequest("/agent/quiz/evaluate", request);
    }

    @GetMapping("/insights/{userId}")
    public ResponseEntity<?> getInsights(@PathVariable int userId) {
        return proxyGetRequest("/agent/insights/" + userId);
    }

    @PostMapping("/end-session/{sessionId}")
    public ResponseEntity<?> endSession(@PathVariable String sessionId) {
        return proxyPostRequest("/agent/end-session/" + sessionId, null);
    }

    private ResponseEntity<?> proxyRequest(String path, Map<String, Object> body) {
        try {
            String url = aiServiceUrl + path;
            HttpHeaders headers = new HttpHeaders();
            headers.setContentType(MediaType.APPLICATION_JSON);

            HttpEntity<Map<String, Object>> entity = new HttpEntity<>(body, headers);
            ResponseEntity<Map> response = restTemplate.exchange(url, HttpMethod.POST, entity, Map.class);

            return ResponseEntity.status(response.getStatusCode()).body(response.getBody());
        } catch (HttpClientErrorException e) {
            log.error("AI service error: {}", e.getMessage());
            return ResponseEntity.status(e.getStatusCode())
                    .body(Map.of("error", e.getMessage()));
        } catch (Exception e) {
            log.error("Proxy error: {}", e.getMessage());
            return ResponseEntity.status(HttpStatus.INTERNAL_SERVER_ERROR)
                    .body(Map.of("error", "Failed to connect to AI service"));
        }
    }

    private ResponseEntity<?> proxyGetRequest(String path) {
        try {
            String url = aiServiceUrl + path;
            ResponseEntity<Map> response = restTemplate.getForEntity(url, Map.class);
            return ResponseEntity.status(response.getStatusCode()).body(response.getBody());
        } catch (HttpClientErrorException e) {
            log.error("AI service error: {}", e.getMessage());
            return ResponseEntity.status(e.getStatusCode())
                    .body(Map.of("error", e.getMessage()));
        } catch (Exception e) {
            log.error("Proxy error: {}", e.getMessage());
            return ResponseEntity.status(HttpStatus.INTERNAL_SERVER_ERROR)
                    .body(Map.of("error", "Failed to connect to AI service"));
        }
    }

    private ResponseEntity<?> proxyPostRequest(String path, Map<String, Object> body) {
        try {
            String url = aiServiceUrl + path;
            HttpHeaders headers = new HttpHeaders();
            headers.setContentType(MediaType.APPLICATION_JSON);

            HttpEntity<Map<String, Object>> entity = new HttpEntity<>(body, headers);
            ResponseEntity<Map> response = restTemplate.exchange(url, HttpMethod.POST, entity, Map.class);

            return ResponseEntity.status(response.getStatusCode()).body(response.getBody());
        } catch (HttpClientErrorException e) {
            log.error("AI service error: {}", e.getMessage());
            return ResponseEntity.status(e.getStatusCode())
                    .body(Map.of("error", e.getMessage()));
        } catch (Exception e) {
            log.error("Proxy error: {}", e.getMessage());
            return ResponseEntity.status(HttpStatus.INTERNAL_SERVER_ERROR)
                    .body(Map.of("error", "Failed to connect to AI service"));
        }
    }
}