package com.notsy.controller;

import com.notsy.dto.request.CreateMemoryEntryRequest;
import com.notsy.entity.MemoryEntry;
import com.notsy.service.MemoryService;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;
import java.util.List;

@RestController
@RequestMapping("/api/memory")
public class MemoryController {

    @Autowired
    private MemoryService memoryService;

    @PostMapping
    public ResponseEntity<?> createMemoryEntry(@RequestBody CreateMemoryEntryRequest request) {
        MemoryEntry entry = new MemoryEntry();
        entry.setUserId(request.getUserId());
        entry.setMemoryType(request.getMemoryType());
        entry.setContent(request.getContent());

        if (request.getMetadata() != null) {
            entry.setMetadata(request.getMetadata());
            entry.setTopic((String) request.getMetadata().get("topic"));
            if (request.getMetadata().get("score") != null) {
                entry.setScore(((Number) request.getMetadata().get("score")).intValue());
            }
        }

        MemoryEntry saved = memoryService.createEntry(entry);
        return ResponseEntity.ok(new ApiResponse(true, "Memory stored", saved));
    }

    @GetMapping("/user/{userId}")
    public ResponseEntity<?> getUserMemories(@PathVariable Long userId) {
        List<MemoryEntry> memories = memoryService.getUserMemories(userId);
        return ResponseEntity.ok(new ApiResponse(true, "Memories retrieved", memories));
    }

    @GetMapping("/user/{userId}/type/{memoryType}")
    public ResponseEntity<?> getUserMemoriesByType(
            @PathVariable Long userId,
            @PathVariable String memoryType) {
        List<MemoryEntry> memories = memoryService.getUserMemoriesByType(userId, memoryType);
        return ResponseEntity.ok(new ApiResponse(true, "Memories retrieved", memories));
    }

    @GetMapping("/user/{userId}/topic/{topic}")
    public ResponseEntity<?> getUserMemoriesByTopic(
            @PathVariable Long userId,
            @PathVariable String topic) {
        List<MemoryEntry> memories = memoryService.getUserMemoriesByTopic(userId, topic);
        return ResponseEntity.ok(new ApiResponse(true, "Memories retrieved", memories));
    }

    static class ApiResponse {
        public boolean success;
        public String message;
        public Object data;

        public ApiResponse(boolean success, String message, Object data) {
            this.success = success;
            this.message = message;
            this.data = data;
        }
    }
}