package com.notsy.service;

import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.core.type.TypeReference;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.notsy.dto.request.ChatRequest;
import com.notsy.dto.request.CreateBranchRequest;
import com.notsy.dto.request.CreateConversationRequest;
import com.notsy.dto.request.MergeBranchRequest;
import com.notsy.dto.response.ConversationResponse;
import com.notsy.dto.response.MessageResponse;
import com.notsy.entity.Conversation;
import com.notsy.entity.Message;
import com.notsy.entity.Topic;
import com.notsy.entity.User;
import com.notsy.exception.BadRequestException;
import com.notsy.exception.ResourceNotFoundException;
import com.notsy.repository.ConversationRepository;
import com.notsy.repository.MessageRepository;
import com.notsy.repository.TopicRepository;
import lombok.RequiredArgsConstructor;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.util.*;
import java.util.stream.Collectors;

@Service
@RequiredArgsConstructor
public class ConversationService {

    private final ConversationRepository conversationRepository;
    private final MessageRepository messageRepository;
    private final TopicRepository topicRepository;
    private final AIProxyService aiProxyService;
    private final ObjectMapper objectMapper;

    private static final int MAX_CHAT_HISTORY = 10;

    @Transactional(readOnly = true)
    public List<ConversationResponse> getConversations(Long topicId, User user) {
        return conversationRepository.findByTopicIdAndUserId(topicId, user.getId())
                .stream()
                .filter(c -> !c.getIsBranch())
                .map(this::toConversationSummary)
                .collect(Collectors.toList());
    }

    @Transactional
    public ConversationResponse createConversation(Long topicId, CreateConversationRequest request, User user) {
        Topic topic = topicRepository.findByIdAndUserId(topicId, user.getId())
                .orElseThrow(() -> new ResourceNotFoundException("Topic", topicId));

        Conversation.LearningMode learningMode = Conversation.LearningMode.MASTER_THIS;
        if (request.getLearningMode() != null) {
            try {
                learningMode = Conversation.LearningMode.valueOf(request.getLearningMode().toUpperCase());
            } catch (IllegalArgumentException e) {
                throw new BadRequestException("Invalid learning mode: " + request.getLearningMode());
            }
        }

        Conversation conversation = Conversation.builder()
                .title(request.getTitle())
                .learningMode(learningMode)
                .isBranch(false)
                .branchStatus(Conversation.BranchStatus.ACTIVE)
                .topic(topic)
                .build();

        conversation = conversationRepository.save(conversation);
        return toConversationResponse(conversation);
    }

    @Transactional(readOnly = true)
    public ConversationResponse getConversation(Long topicId, Long conversationId, User user) {
        Conversation conversation = conversationRepository.findByIdAndTopicIdAndUserId(conversationId, topicId, user.getId())
                .orElseThrow(() -> new ResourceNotFoundException("Conversation", conversationId));
        return toConversationResponse(conversation);
    }

    @Transactional
    public void deleteConversation(Long topicId, Long conversationId, User user) {
        Conversation conversation = conversationRepository.findByIdAndTopicIdAndUserId(conversationId, topicId, user.getId())
                .orElseThrow(() -> new ResourceNotFoundException("Conversation", conversationId));

        // Delete all messages
        messageRepository.deleteByConversationId(conversationId);

        // Delete the conversation
        conversationRepository.delete(conversation);
    }

    @Transactional
    public MessageResponse chat(Long topicId, Long conversationId, ChatRequest request, User user) {
        Conversation conversation = conversationRepository.findByIdAndTopicIdAndUserId(conversationId, topicId, user.getId())
                .orElseThrow(() -> new ResourceNotFoundException("Conversation", conversationId));

        Topic topic = conversation.getTopic();

        // Save user message
        Message userMessage = Message.builder()
                .role(Message.Role.user)
                .content(request.getMessage())
                .conversation(conversation)
                .build();
        messageRepository.save(userMessage);

        // Build history (last 10 messages)
        List<Message> recentMessages = messageRepository.findLastMessages(conversationId, MAX_CHAT_HISTORY);
        Collections.reverse(recentMessages);
        List<Map<String, String>> history = recentMessages.stream()
                .filter(m -> m.getRole() == Message.Role.user || m.getRole() == Message.Role.assistant)
                .map(m -> {
                    Map<String, String> msg = new HashMap<>();
                    msg.put("role", m.getRole().name());
                    msg.put("content", m.getContent());
                    return msg;
                })
                .collect(Collectors.toList());

        // Call AI service
        AIProxyService.ChatResponse aiResponse = aiProxyService.chat(
                topic.getId(),
                request.getMessage(),
                history,
                conversation.getLearningMode().name()
        );

        // Save assistant response
        String sourcesJson = null;
        try {
            sourcesJson = objectMapper.writeValueAsString(aiResponse.getSources());
        } catch (JsonProcessingException e) {
            sourcesJson = "[]";
        }

        Message assistantMessage = Message.builder()
                .role(Message.Role.assistant)
                .content(aiResponse.getResponse())
                .sources(sourcesJson)
                .tokensUsed(aiResponse.getTokensUsed())
                .conversation(conversation)
                .build();
        assistantMessage = messageRepository.save(assistantMessage);

        return toMessageResponse(assistantMessage);
    }

    @Transactional
    public ConversationResponse branchConversation(Long topicId, Long conversationId, CreateBranchRequest request, User user) {
        Conversation parentConversation = conversationRepository.findByIdAndTopicIdAndUserId(conversationId, topicId, user.getId())
                .orElseThrow(() -> new ResourceNotFoundException("Conversation", conversationId));

        Conversation.LearningMode learningMode = parentConversation.getLearningMode();
        if (request.getLearningMode() != null) {
            try {
                learningMode = Conversation.LearningMode.valueOf(request.getLearningMode().toUpperCase());
            } catch (IllegalArgumentException e) {
                throw new BadRequestException("Invalid learning mode: " + request.getLearningMode());
            }
        }

        Conversation branch = Conversation.builder()
                .title("Branch of: " + parentConversation.getTitle())
                .learningMode(learningMode)
                .isBranch(true)
                .parentConversation(parentConversation)
                .branchContext(request.getBranchContext())
                .branchStatus(Conversation.BranchStatus.ACTIVE)
                .topic(parentConversation.getTopic())
                .build();

        branch = conversationRepository.save(branch);
        return toConversationResponse(branch);
    }

    @Transactional
    public ConversationResponse mergeBranch(Long topicId, Long conversationId, MergeBranchRequest request, User user) {
        Conversation mainConversation = conversationRepository.findByIdAndTopicIdAndUserId(conversationId, topicId, user.getId())
                .orElseThrow(() -> new ResourceNotFoundException("Conversation", conversationId));

        Conversation branchConversation = conversationRepository.findByIdAndTopicIdAndUserId(
                request.getBranchConversationId(), topicId, user.getId())
                .orElseThrow(() -> new ResourceNotFoundException("Branch conversation", request.getBranchConversationId()));

        if (!branchConversation.getIsBranch()) {
            throw new BadRequestException("The specified conversation is not a branch");
        }
        if (!branchConversation.getParentConversation().getId().equals(conversationId)) {
            throw new BadRequestException("The specified branch does not belong to this conversation");
        }

        if ("merge".equalsIgnoreCase(request.getAction())) {
            branchConversation.setBranchStatus(Conversation.BranchStatus.MERGED);
        } else if ("discard".equalsIgnoreCase(request.getAction())) {
            branchConversation.setBranchStatus(Conversation.BranchStatus.DISCARDED);
        } else {
            throw new BadRequestException("Invalid action. Use 'merge' or 'discard'");
        }

        branchConversation = conversationRepository.save(branchConversation);
        return toConversationResponse(branchConversation);
    }

    @Transactional(readOnly = true)
    public List<ConversationResponse> getBranches(Long topicId, Long conversationId, User user) {
        // Verify the main conversation exists
        conversationRepository.findByIdAndTopicIdAndUserId(conversationId, topicId, user.getId())
                .orElseThrow(() -> new ResourceNotFoundException("Conversation", conversationId));

        return conversationRepository.findBranchesByParentIdAndUserId(conversationId, user.getId())
                .stream()
                .map(this::toConversationResponse)
                .collect(Collectors.toList());
    }

    private ConversationResponse toConversationResponse(Conversation conversation) {
        List<MessageResponse> messages = messageRepository.findByConversationIdOrderByCreatedAtAsc(conversation.getId())
                .stream()
                .map(this::toMessageResponse)
                .collect(Collectors.toList());

        return ConversationResponse.builder()
                .id(conversation.getId())
                .title(conversation.getTitle())
                .learningMode(conversation.getLearningMode().name())
                .isBranch(conversation.getIsBranch())
                .parentConversationId(conversation.getParentConversation() != null ? conversation.getParentConversation().getId() : null)
                .branchContext(conversation.getBranchContext())
                .branchStatus(conversation.getBranchStatus().name())
                .topicId(conversation.getTopic().getId())
                .messages(messages)
                .createdAt(conversation.getCreatedAt())
                .updatedAt(conversation.getUpdatedAt())
                .build();
    }

    private ConversationResponse toConversationSummary(Conversation conversation) {
        return ConversationResponse.builder()
                .id(conversation.getId())
                .title(conversation.getTitle())
                .learningMode(conversation.getLearningMode().name())
                .isBranch(conversation.getIsBranch())
                .parentConversationId(conversation.getParentConversation() != null ? conversation.getParentConversation().getId() : null)
                .branchContext(conversation.getBranchContext())
                .branchStatus(conversation.getBranchStatus().name())
                .topicId(conversation.getTopic().getId())
                .createdAt(conversation.getCreatedAt())
                .updatedAt(conversation.getUpdatedAt())
                .build();
    }

    private MessageResponse toMessageResponse(Message message) {
        return MessageResponse.builder()
                .id(message.getId())
                .role(message.getRole().name())
                .content(message.getContent())
                .sources(message.getSources())
                .tokensUsed(message.getTokensUsed())
                .createdAt(message.getCreatedAt())
                .build();
    }
}
