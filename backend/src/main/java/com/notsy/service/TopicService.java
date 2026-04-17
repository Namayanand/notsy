package com.notsy.service;

import com.notsy.dto.request.CreateTopicRequest;
import com.notsy.dto.request.ReorderTopicsRequest;
import com.notsy.dto.request.UpdateTopicRequest;
import com.notsy.dto.response.ConversationResponse;
import com.notsy.dto.response.ResourceResponse;
import com.notsy.dto.response.TopicResponse;
import com.notsy.entity.Notebook;
import com.notsy.entity.NotebookMembership;
import com.notsy.entity.Topic;
import com.notsy.entity.User;
import com.notsy.exception.BadRequestException;
import com.notsy.exception.ResourceNotFoundException;
import com.notsy.repository.NotebookMembershipRepository;
import com.notsy.repository.TopicRepository;
import lombok.RequiredArgsConstructor;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.util.List;
import java.util.stream.Collectors;

@Service
@RequiredArgsConstructor
public class TopicService {

    private final TopicRepository topicRepository;
    private final NotebookService notebookService;
    private final AIProxyService aiProxyService;
    private final NotebookMembershipRepository membershipRepository;

    @Transactional(readOnly = true)
    public List<TopicResponse> getRootTopics(Long notebookId, User user) {
        Notebook notebook = notebookService.getNotebookEntity(notebookId, user);
        return topicRepository.findByNotebookIdAndParentTopicIsNullOrderByOrderIndexAsc(notebookId)
                .stream()
                .map(topic -> toTopicResponse(topic, false))
                .collect(Collectors.toList());
    }

    @Transactional
    public TopicResponse createTopic(Long notebookId, CreateTopicRequest request, User user) {
        // Check if user can edit (owner or editor)
        NotebookMembership.Role role = getUserRole(notebookId, user.getId());
        if (role == null || role == NotebookMembership.Role.VIEWER) {
            throw new BadRequestException("You don't have permission to add topics to this notebook");
        }

        Notebook notebook = notebookService.getNotebookEntity(notebookId, user);

        Integer orderIndex = request.getOrderIndex();
        if (orderIndex == null) {
            if (request.getParentTopicId() != null) {
                orderIndex = topicRepository.findMaxOrderIndexForParent(request.getParentTopicId()) + 1;
            } else {
                orderIndex = topicRepository.findMaxOrderIndexForNotebook(notebookId) + 1;
            }
        }

        Topic parentTopic = null;
        if (request.getParentTopicId() != null) {
            parentTopic = topicRepository.findByIdAndNotebookIdAndUserIdMembership(request.getParentTopicId(), notebookId, user.getId())
                    .orElseThrow(() -> new ResourceNotFoundException("Parent topic not found"));
        }

        Topic topic = Topic.builder()
                .title(request.getTitle())
                .description(request.getDescription())
                .orderIndex(orderIndex)
                .notebook(notebook)
                .parentTopic(parentTopic)
                .embeddingStatus(Topic.EmbeddingStatus.PENDING)
                .tags(request.getTags() != null ? request.getTags() : List.of())
                .build();

        topic = topicRepository.save(topic);
        return toTopicResponse(topic, true);
    }

    @Transactional(readOnly = true)
    public TopicResponse getTopic(Long notebookId, Long topicId, User user) {
        Topic topic = topicRepository.findByIdAndNotebookIdAndUserIdMembership(topicId, notebookId, user.getId())
                .orElseThrow(() -> new ResourceNotFoundException("Topic", topicId));
        return toTopicResponse(topic, true);
    }

    @Transactional
    public TopicResponse updateTopic(Long notebookId, Long topicId, UpdateTopicRequest request, User user) {
        Topic topic = topicRepository.findByIdAndNotebookIdAndUserIdMembership(topicId, notebookId, user.getId())
                .orElseThrow(() -> new ResourceNotFoundException("Topic", topicId));

        if (request.getTitle() != null) {
            topic.setTitle(request.getTitle());
        }
        if (request.getDescription() != null) {
            topic.setDescription(request.getDescription());
        }
        if (request.getOrderIndex() != null) {
            topic.setOrderIndex(request.getOrderIndex());
        }
        if (request.getTags() != null) {
            topic.setTags(request.getTags());
        }

        topic = topicRepository.save(topic);
        return toTopicResponse(topic, true);
    }

    @Transactional
    public void deleteTopic(Long notebookId, Long topicId, User user) {
        Topic topic = topicRepository.findByIdAndNotebookIdAndUserIdMembership(topicId, notebookId, user.getId())
                .orElseThrow(() -> new ResourceNotFoundException("Topic", topicId));

        // Delete embeddings from AI service
        aiProxyService.deleteTopicEmbeddings(topicId);

        topicRepository.delete(topic);
    }

    @Transactional
    public void reorderTopics(Long notebookId, ReorderTopicsRequest request, User user) {
        notebookService.getNotebookEntity(notebookId, user);

        List<Long> topicIds = request.getTopicIds();
        int i = 0;
        for (Long topicId : topicIds) {
            Topic topic = topicRepository.findByIdAndNotebookIdAndUserIdMembership(topicId, notebookId, user.getId())
                    .orElseThrow(() -> new ResourceNotFoundException("Topic", topicId));
            topic.setOrderIndex(i);
            topicRepository.save(topic);
            i++;
        }
    }

    public Topic getTopicEntity(Long topicId, User user) {
        return topicRepository.findByIdAndUserIdMembership(topicId, user.getId())
                .orElseThrow(() -> new ResourceNotFoundException("Topic", topicId));
    }

    private NotebookMembership.Role getUserRole(Long notebookId, Long userId) {
        return membershipRepository.findByNotebookIdAndUserId(notebookId, userId)
                .map(NotebookMembership::getRole)
                .orElse(null);
    }

    private TopicResponse toTopicResponse(Topic topic, boolean includeDetails) {
        TopicResponse.TopicResponseBuilder builder = TopicResponse.builder()
                .id(topic.getId())
                .title(topic.getTitle())
                .description(topic.getDescription())
                .orderIndex(topic.getOrderIndex())
                .notebookId(topic.getNotebook().getId())
                .parentTopicId(topic.getParentTopic() != null ? topic.getParentTopic().getId() : null)
                .embeddingStatus(topic.getEmbeddingStatus().name())
                .tags(topic.getTags())
                .createdAt(topic.getCreatedAt());

        if (includeDetails) {
            List<ResourceResponse> resources = topic.getResources().stream()
                    .map(r -> ResourceResponse.builder()
                            .id(r.getId())
                            .filename(r.getFilename())
                            .originalName(r.getOriginalName())
                            .fileType(r.getFileType().name())
                            .fileSize(r.getFileSize())
                            .sourceUrl(r.getSourceUrl())
                            .embeddingStatus(r.getEmbeddingStatus().name())
                            .chunkCount(r.getChunkCount())
                            .topicId(topic.getId())
                            .createdAt(r.getCreatedAt())
                            .build())
                    .collect(Collectors.toList());

            List<TopicResponse.ConversationSummaryResponse> conversations = topic.getConversations().stream()
                    .filter(c -> !c.getIsBranch())
                    .map(c -> TopicResponse.ConversationSummaryResponse.builder()
                            .id(c.getId())
                            .title(c.getTitle())
                            .learningMode(c.getLearningMode().name())
                            .isBranch(c.getIsBranch())
                            .branchStatus(c.getBranchStatus().name())
                            .createdAt(c.getCreatedAt())
                            .build())
                    .collect(Collectors.toList());

            List<TopicResponse> subtopics = topic.getSubtopics().stream()
                    .map(st -> toTopicResponse(st, false))
                    .collect(Collectors.toList());

            builder.resources(resources);
            builder.conversations(conversations);
            builder.subtopics(subtopics);
        }

        return builder.build();
    }
}
