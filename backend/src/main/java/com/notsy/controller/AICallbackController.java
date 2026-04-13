package com.notsy.controller;

import com.notsy.entity.Resource;
import com.notsy.repository.ResourceRepository;
import lombok.RequiredArgsConstructor;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.Map;

@RestController
@RequestMapping("/api/ai")
@RequiredArgsConstructor
public class AICallbackController {

    private final ResourceRepository resourceRepository;

    @PostMapping("/callback")
    public ResponseEntity<?> receiveCallback(@RequestBody Map<String, Object> callback) {
        Long resourceId = Long.valueOf(callback.get("resource_id").toString());
        String status = (String) callback.get("status");
        Integer chunkCount = callback.get("chunk_count") != null ?
                Integer.parseInt(callback.get("chunk_count").toString()) : null;

        resourceRepository.findById(resourceId).ifPresent(resource -> {
            if ("DONE".equals(status)) {
                resource.setEmbeddingStatus(Resource.EmbeddingStatus.DONE);
                if (chunkCount != null) {
                    resource.setChunkCount(chunkCount);
                }
            } else if ("FAILED".equals(status)) {
                resource.setEmbeddingStatus(Resource.EmbeddingStatus.FAILED);
            }
            resourceRepository.save(resource);
        });

        return ResponseEntity.ok(Map.of("status", "received"));
    }
}
