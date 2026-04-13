package com.notsy.service;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.notsy.dto.request.AddLinkRequest;
import com.notsy.dto.response.ResourceResponse;
import com.notsy.entity.Resource;
import com.notsy.entity.Topic;
import com.notsy.entity.User;
import com.notsy.exception.BadRequestException;
import com.notsy.exception.ResourceNotFoundException;
import com.notsy.repository.ResourceRepository;
import com.notsy.repository.TopicRepository;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.scheduling.annotation.Async;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.web.multipart.MultipartFile;

import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.util.Arrays;
import java.util.List;
import java.util.UUID;
import java.util.stream.Collectors;

@Service
@RequiredArgsConstructor
@Slf4j
public class ResourceService {

    private final ResourceRepository resourceRepository;
    private final TopicRepository topicRepository;
    private final AIProxyService aiProxyService;

    @Value("${app.file.upload-dir}")
    private String uploadDir;

    private static final List<String> ALLOWED_TYPES = Arrays.asList("pdf", "png", "jpg", "jpeg", "mp4", "txt");
    private static final long MAX_FILE_SIZE = 50 * 1024 * 1024; // 50MB

    @Transactional(readOnly = true)
    public List<ResourceResponse> getResources(Long topicId, User user) {
        return resourceRepository.findByTopicIdAndUserId(topicId, user.getId())
                .stream()
                .map(this::toResourceResponse)
                .collect(Collectors.toList());
    }

    @Transactional
    public ResourceResponse uploadFile(Long topicId, MultipartFile file, User user) {
        Topic topic = topicRepository.findByIdAndUserId(topicId, user.getId())
                .orElseThrow(() -> new ResourceNotFoundException("Topic", topicId));

        validateFile(file);

        String fileType = determineFileType(file.getOriginalFilename());
        String filename = UUID.randomUUID() + "_" + file.getOriginalFilename();

        try {
            Path uploadPath = Paths.get(uploadDir, String.valueOf(user.getId()), String.valueOf(topicId));
            Files.createDirectories(uploadPath);
            Path filePath = uploadPath.resolve(filename);
            file.transferTo(filePath.toFile());

            Resource resource = Resource.builder()
                    .filename(filename)
                    .originalName(file.getOriginalFilename())
                    .filePath(filePath.toString())
                    .fileType(Resource.FileType.valueOf(fileType))
                    .fileSize(file.getSize())
                    .embeddingStatus(Resource.EmbeddingStatus.PENDING)
                    .topic(topic)
                    .build();

            resource = resourceRepository.save(resource);

            // Trigger async embedding
            triggerEmbedding(resource, topic);

            return toResourceResponse(resource);
        } catch (IOException e) {
            throw new BadRequestException("Failed to save file: " + e.getMessage());
        }
    }

    @Transactional
    public ResourceResponse addLink(Long topicId, AddLinkRequest request, User user) {
        Topic topic = topicRepository.findByIdAndUserId(topicId, user.getId())
                .orElseThrow(() -> new ResourceNotFoundException("Topic", topicId));

        Resource resource = Resource.builder()
                .filename(UUID.randomUUID() + "_link")
                .originalName(request.getTitle() != null ? request.getTitle() : request.getSourceUrl())
                .filePath(null)
                .fileType(Resource.FileType.link)
                .sourceUrl(request.getSourceUrl())
                .embeddingStatus(Resource.EmbeddingStatus.PENDING)
                .topic(topic)
                .build();

        resource = resourceRepository.save(resource);

        // Trigger async embedding for URL
        triggerUrlEmbedding(resource, topic);

        return toResourceResponse(resource);
    }

    @Transactional
    public void deleteResource(Long topicId, Long resourceId, User user) {
        Resource resource = resourceRepository.findByIdAndTopicIdAndUserId(resourceId, topicId, user.getId())
                .orElseThrow(() -> new ResourceNotFoundException("Resource", resourceId));

        // Delete file from storage if it's a file (not a link)
        if (resource.getFilePath() != null) {
            try {
                Path filePath = Paths.get(resource.getFilePath());
                Files.deleteIfExists(filePath);
            } catch (IOException e) {
                log.warn("Failed to delete file: {}", resource.getFilePath());
            }
        }

        resourceRepository.delete(resource);
    }

    @Transactional
    public ResourceResponse reembedResource(Long topicId, Long resourceId, User user) {
        Resource resource = resourceRepository.findByIdAndTopicIdAndUserId(resourceId, topicId, user.getId())
                .orElseThrow(() -> new ResourceNotFoundException("Resource", resourceId));

        resource.setEmbeddingStatus(Resource.EmbeddingStatus.PENDING);
        resource.setChunkCount(null);
        resource = resourceRepository.save(resource);

        Topic topic = resource.getTopic();

        if (resource.getFileType() == Resource.FileType.link) {
            triggerUrlEmbedding(resource, topic);
        } else {
            triggerEmbedding(resource, topic);
        }

        return toResourceResponse(resource);
    }

    public Resource getResourceEntity(Long resourceId, User user) {
        return resourceRepository.findById(resourceId)
                .orElseThrow(() -> new ResourceNotFoundException("Resource", resourceId));
    }

    @Async
    public void triggerEmbedding(Resource resource, Topic topic) {
        try {
            resource.setEmbeddingStatus(Resource.EmbeddingStatus.PROCESSING);
            resourceRepository.save(resource);

            aiProxyService.embedResource(
                    resource.getId(),
                    topic.getId(),
                    resource.getFilePath(),
                    null,
                    resource.getFileType().name().toLowerCase(),
                    topic.getNotebook().getUser().getId()
            );
        } catch (Exception e) {
            log.error("Failed to trigger embedding for resource {}", resource.getId(), e);
            resource.setEmbeddingStatus(Resource.EmbeddingStatus.FAILED);
            resourceRepository.save(resource);
        }
    }

    @Async
    public void triggerUrlEmbedding(Resource resource, Topic topic) {
        try {
            resource.setEmbeddingStatus(Resource.EmbeddingStatus.PROCESSING);
            resourceRepository.save(resource);

            aiProxyService.embedResource(
                    resource.getId(),
                    topic.getId(),
                    null,
                    resource.getSourceUrl(),
                    "link",
                    topic.getNotebook().getUser().getId()
            );
        } catch (Exception e) {
            log.error("Failed to trigger URL embedding for resource {}", resource.getId(), e);
            resource.setEmbeddingStatus(Resource.EmbeddingStatus.FAILED);
            resourceRepository.save(resource);
        }
    }

    private void validateFile(MultipartFile file) {
        if (file.isEmpty()) {
            throw new BadRequestException("File is empty");
        }
        if (file.getSize() > MAX_FILE_SIZE) {
            throw new BadRequestException("File size exceeds maximum allowed size of 50MB");
        }
        String fileType = determineFileType(file.getOriginalFilename());
        if (!ALLOWED_TYPES.contains(fileType)) {
            throw new BadRequestException("File type not allowed. Allowed types: " + ALLOWED_TYPES);
        }
    }

    private String determineFileType(String filename) {
        if (filename == null) {
            return "unknown";
        }
        String extension = "";
        int lastDot = filename.lastIndexOf('.');
        if (lastDot > 0) {
            extension = filename.substring(lastDot + 1).toLowerCase();
        }
        if (extension.equals("jpeg")) {
            extension = "jpg";
        }
        return extension;
    }

    private ResourceResponse toResourceResponse(Resource resource) {
        return ResourceResponse.builder()
                .id(resource.getId())
                .filename(resource.getFilename())
                .originalName(resource.getOriginalName())
                .fileType(resource.getFileType().name().toLowerCase())
                .fileSize(resource.getFileSize())
                .sourceUrl(resource.getSourceUrl())
                .embeddingStatus(resource.getEmbeddingStatus().name())
                .chunkCount(resource.getChunkCount())
                .topicId(resource.getTopic().getId())
                .createdAt(resource.getCreatedAt())
                .build();
    }
}
