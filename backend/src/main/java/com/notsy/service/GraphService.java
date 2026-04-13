package com.notsy.service;

import com.notsy.dto.request.AddRelationRequest;
import com.notsy.dto.response.GraphResponse;
import com.notsy.entity.Notebook;
import com.notsy.entity.Topic;
import com.notsy.entity.TopicRelation;
import com.notsy.entity.User;
import com.notsy.exception.BadRequestException;
import com.notsy.exception.ResourceNotFoundException;
import com.notsy.repository.TopicRelationRepository;
import com.notsy.repository.TopicRepository;
import lombok.RequiredArgsConstructor;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.util.List;
import java.util.stream.Collectors;

@Service
@RequiredArgsConstructor
public class GraphService {

    private final TopicRepository topicRepository;
    private final TopicRelationRepository topicRelationRepository;
    private final NotebookService notebookService;
    private final AIProxyService aiProxyService;

    @Transactional(readOnly = true)
    public GraphResponse getGraph(Long notebookId, User user) {
        Notebook notebook = notebookService.getNotebookEntity(notebookId, user);

        // Get all topics in the notebook
        List<Topic> topics = topicRepository.findByNotebookIdOrderByOrderIndexAsc(notebookId);

        // Get all relations in the notebook
        List<TopicRelation> relations = topicRelationRepository.findByNotebookId(notebookId);

        // Build nodes
        List<GraphResponse.NodeResponse> nodes = topics.stream()
                .map(topic -> GraphResponse.NodeResponse.builder()
                        .id(topic.getId())
                        .title(topic.getTitle())
                        .embeddingStatus(topic.getEmbeddingStatus().name())
                        .description(topic.getDescription())
                        .build())
                .collect(Collectors.toList());

        // Build edges
        List<GraphResponse.EdgeResponse> edges = relations.stream()
                .map(relation -> GraphResponse.EdgeResponse.builder()
                        .id(relation.getId())
                        .sourceTopicId(relation.getSourceTopic().getId())
                        .targetTopicId(relation.getTargetTopic().getId())
                        .relationshipType(relation.getRelationshipType().name())
                        .strength(relation.getStrength())
                        .description(relation.getDescription())
                        .build())
                .collect(Collectors.toList());

        return GraphResponse.builder()
                .nodes(nodes)
                .edges(edges)
                .build();
    }

    @Transactional
    public GraphResponse generateGraph(Long notebookId, User user) {
        Notebook notebook = notebookService.getNotebookEntity(notebookId, user);

        List<Topic> topics = topicRepository.findByNotebookIdOrderByOrderIndexAsc(notebookId);

        if (topics.size() < 2) {
            throw new BadRequestException("Need at least 2 topics to generate a knowledge graph");
        }

        // Prepare topics data for AI service
        List<AIProxyService.TopicData> topicData = topics.stream()
                .map(topic -> new AIProxyService.TopicData(topic.getId(), topic.getTitle(), topic.getDescription()))
                .collect(Collectors.toList());

        // Call AI service to generate relations
        List<AIProxyService.RelationData> relations = aiProxyService.generateGraph(notebookId, topicData);

        // Delete existing AI-generated relations
        topicRelationRepository.findByNotebookId(notebookId).stream()
                .filter(TopicRelation::getAiGenerated)
                .forEach(topicRelationRepository::delete);

        // Save new relations
        for (AIProxyService.RelationData relationData : relations) {
            Topic sourceTopic = topics.stream()
                    .filter(t -> t.getId().equals(relationData.getSourceTopicId()))
                    .findFirst()
                    .orElse(null);
            Topic targetTopic = topics.stream()
                    .filter(t -> t.getId().equals(relationData.getTargetTopicId()))
                    .findFirst()
                    .orElse(null);

            if (sourceTopic != null && targetTopic != null) {
                TopicRelation.RelationshipType relationshipType;
                try {
                    relationshipType = TopicRelation.RelationshipType.valueOf(relationData.getRelationshipType().toUpperCase());
                } catch (IllegalArgumentException e) {
                    relationshipType = TopicRelation.RelationshipType.RELATED;
                }

                TopicRelation relation = TopicRelation.builder()
                        .sourceTopic(sourceTopic)
                        .targetTopic(targetTopic)
                        .relationshipType(relationshipType)
                        .strength(relationData.getStrength())
                        .aiGenerated(true)
                        .description(relationData.getDescription())
                        .build();
                topicRelationRepository.save(relation);
            }
        }

        // Return updated graph
        return getGraph(notebookId, user);
    }

    @Transactional
    public GraphResponse.EdgeResponse addRelation(Long notebookId, AddRelationRequest request, User user) {
        Notebook notebook = notebookService.getNotebookEntity(notebookId, user);

        Topic sourceTopic = topicRepository.findByIdAndNotebookIdAndUserId(request.getSourceTopicId(), notebookId, user.getId())
                .orElseThrow(() -> new ResourceNotFoundException("Source topic", request.getSourceTopicId()));

        Topic targetTopic = topicRepository.findByIdAndNotebookIdAndUserId(request.getTargetTopicId(), notebookId, user.getId())
                .orElseThrow(() -> new ResourceNotFoundException("Target topic", request.getTargetTopicId()));

        TopicRelation.RelationshipType relationshipType;
        try {
            relationshipType = TopicRelation.RelationshipType.valueOf(request.getRelationshipType().toUpperCase());
        } catch (IllegalArgumentException e) {
            throw new BadRequestException("Invalid relationship type: " + request.getRelationshipType());
        }

        // Check if relation already exists
        if (topicRelationRepository.findBySourceTopicIdAndTargetTopicId(sourceTopic.getId(), targetTopic.getId()).isPresent()) {
            throw new BadRequestException("Relation already exists between these topics");
        }

        TopicRelation relation = TopicRelation.builder()
                .sourceTopic(sourceTopic)
                .targetTopic(targetTopic)
                .relationshipType(relationshipType)
                .strength(request.getStrength() != null ? request.getStrength() : 0.5f)
                .aiGenerated(false)
                .description(request.getDescription())
                .build();

        relation = topicRelationRepository.save(relation);

        return GraphResponse.EdgeResponse.builder()
                .id(relation.getId())
                .sourceTopicId(relation.getSourceTopic().getId())
                .targetTopicId(relation.getTargetTopic().getId())
                .relationshipType(relation.getRelationshipType().name())
                .strength(relation.getStrength())
                .description(relation.getDescription())
                .build();
    }

    @Transactional
    public void deleteRelation(Long notebookId, Long relationId, User user) {
        notebookService.getNotebookEntity(notebookId, user);

        TopicRelation relation = topicRelationRepository.findByIdAndNotebookId(relationId, notebookId)
                .orElseThrow(() -> new ResourceNotFoundException("Relation", relationId));

        topicRelationRepository.delete(relation);
    }
}
