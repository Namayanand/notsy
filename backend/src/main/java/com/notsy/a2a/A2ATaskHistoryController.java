package com.notsy.a2a;

import com.notsy.entity.A2ATask;
import com.notsy.entity.User;
import com.notsy.repository.A2ATaskRepository;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.PageRequest;
import org.springframework.data.domain.Sort;
import org.springframework.http.ResponseEntity;
import org.springframework.security.core.annotation.AuthenticationPrincipal;
import org.springframework.web.bind.annotation.*;

import java.util.List;
import java.util.Map;
import java.util.UUID;
import java.util.stream.Collectors;

/**
 * Controller for A2A task history - used by frontend Agent Network panel
 */
@RestController
@RequestMapping("/api/a2a/history")
@RequiredArgsConstructor
@Slf4j
public class A2ATaskHistoryController {

    private final A2ATaskRepository taskRepository;

    /**
     * Get task history for user
     */
    @GetMapping
    public ResponseEntity<Map<String, Object>> getHistory(
            @AuthenticationPrincipal User user,
            @RequestParam(defaultValue = "0") int page,
            @RequestParam(defaultValue = "20") int size) {

        UUID userId = user != null ? new UUID(0, user.getId()) : new UUID(0, 0);

        Page<A2ATask> taskPage = taskRepository.findByUserId(
                userId,
                PageRequest.of(page, size, Sort.by(Sort.Direction.DESC, "createdAt"))
        );

        List<Map<String, Object>> tasks = taskPage.getContent().stream()
                .map(this::mapToResponse)
                .collect(Collectors.toList());

        return ResponseEntity.ok(Map.of(
                "tasks", tasks,
                "totalPages", taskPage.getTotalPages(),
                "currentPage", page,
                "totalElements", taskPage.getTotalElements()
        ));
    }

    /**
     * Get recent tasks for real-time updates
     */
    @GetMapping("/recent")
    public ResponseEntity<List<Map<String, Object>>> getRecentTasks(
            @AuthenticationPrincipal User user,
            @RequestParam(defaultValue = "10") int limit) {

        UUID userId = user != null ? new UUID(0, user.getId()) : new UUID(0, 0);

        List<A2ATask> tasks = taskRepository.findByUserIdOrderByCreatedAtDesc(userId)
                .stream()
                .limit(limit)
                .collect(Collectors.toList());

        List<Map<String, Object>> response = tasks.stream()
                .map(this::mapToResponse)
                .collect(Collectors.toList());

        return ResponseEntity.ok(response);
    }

    private Map<String, Object> mapToResponse(A2ATask task) {
        return Map.of(
                "id", task.getId().toString(),
                "skill", task.getSkill() != null ? task.getSkill() : "",
                "status", task.getStatus().getValue(),
                "agentName", task.getAgentName() != null ? task.getAgentName() : "",
                "agentChain", task.getAgentChain() != null ? task.getAgentChain() : "[]",
                "createdAt", task.getCreatedAt().toString(),
                "inputPayload", task.getInputPayload() != null ? task.getInputPayload() : Map.of(),
                "outputPayload", task.getOutputPayload() != null ? task.getOutputPayload() : Map.of()
        );
    }
}