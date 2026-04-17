package com.notsy.service;

import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.core.type.TypeReference;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.notsy.dto.request.ChatRequest;
import com.notsy.dto.request.CreateBranchRequest;
import com.notsy.dto.request.CreateConversationRequest;
import com.notsy.dto.request.CreateMessageBranchRequest;
import com.notsy.dto.request.MergeBranchRequest;
import com.notsy.dto.response.*;
import com.notsy.entity.*;
import com.notsy.exception.BadRequestException;
import com.notsy.exception.ResourceNotFoundException;
import com.notsy.repository.ConversationBranchRepository;
import com.notsy.repository.ConversationRepository;
import com.notsy.repository.MessageRepository;
import com.notsy.repository.NotebookMembershipRepository;
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
    private final ConversationBranchRepository conversationBranchRepository;
    private final NotebookMembershipRepository membershipRepository;
    private final AIProxyService aiProxyService;
    private final ObjectMapper objectMapper;

    private static final int MAX_CHAT_HISTORY = 10;
    private static final int MAX_BRANCH_DEPTH = 5;

    @Transactional(readOnly = true)
    public List<ConversationResponse> getConversations(Long topicId, User user) {
        return conversationRepository.findByTopicIdAndUserIdMembership(topicId, user.getId())
                .stream()
                .filter(c -> !c.getIsBranch())
                .map(this::toConversationSummary)
                .collect(Collectors.toList());
    }

    @Transactional
    public ConversationResponse createConversation(Long topicId, CreateConversationRequest request, User user) {
        Topic topic = topicRepository.findByIdAndUserIdMembership(topicId, user.getId())
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
        Conversation conversation = conversationRepository.findByIdAndTopicIdAndUserIdMembership(conversationId, topicId, user.getId())
                .orElseThrow(() -> new ResourceNotFoundException("Conversation", conversationId));
        return toConversationResponse(conversation);
    }

    @Transactional
    public void deleteConversation(Long topicId, Long conversationId, User user) {
        Conversation conversation = conversationRepository.findByIdAndTopicIdAndUserIdMembership(conversationId, topicId, user.getId())
                .orElseThrow(() -> new ResourceNotFoundException("Conversation", conversationId));

        // Check for active branches
        List<ConversationBranch> activeBranches = conversationBranchRepository
                .findByParentConversationIdAndBranchStatusOrderByCreatedAtDesc(
                        conversationId, ConversationBranch.BranchStatus.ACTIVE);

        if (!activeBranches.isEmpty()) {
            String branchTitles = activeBranches.stream()
                    .map(b -> b.getBranchConversation().getTitle())
                    .collect(Collectors.joining(", "));
            throw new BadRequestException(
                    "Cannot delete conversation with " + activeBranches.size() + " active branch(es): " + branchTitles +
                    ". Please merge or discard branches first.");
        }

        // Delete all messages
        messageRepository.deleteByConversationId(conversationId);

        // Delete the conversation
        conversationRepository.delete(conversation);
    }

    @Transactional
    public MessageResponse chat(Long topicId, Long conversationId, ChatRequest request, User user) {
        Conversation conversation = conversationRepository.findByIdAndTopicIdAndUserIdMembership(conversationId, topicId, user.getId())
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
                conversation.getLearningMode().name(),
                request.getUseWebSearch() != null ? request.getUseWebSearch() : false,
                request.getExplainDepth(),
                request.getSystemPrompt()
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
        Conversation parentConversation = conversationRepository.findByIdAndTopicIdAndUserIdMembership(conversationId, topicId, user.getId())
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
        Conversation mainConversation = conversationRepository.findByIdAndTopicIdAndUserIdMembership(conversationId, topicId, user.getId())
                .orElseThrow(() -> new ResourceNotFoundException("Conversation", conversationId));

        Conversation branchConversation = conversationRepository.findByIdAndTopicIdAndUserIdMembership(
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
        conversationRepository.findByIdAndTopicIdAndUserIdMembership(conversationId, topicId, user.getId())
                .orElseThrow(() -> new ResourceNotFoundException("Conversation", conversationId));

        return conversationRepository.findBranchesByParentIdAndUserIdMembership(conversationId, user.getId())
                .stream()
                .map(this::toConversationResponse)
                .collect(Collectors.toList());
    }

    @Transactional
    public BranchNavigationResponse branchFromMessage(Long topicId, Long conversationId,
                                                       CreateMessageBranchRequest request, User user) {
        // Verify parent conversation exists
        Conversation parentConversation = conversationRepository.findByIdAndTopicIdAndUserIdMembership(conversationId, topicId, user.getId())
                .orElseThrow(() -> new ResourceNotFoundException("Conversation", conversationId));

        // Verify parent message exists
        Message parentMessage = messageRepository.findById(request.getParentMessageId())
                .orElseThrow(() -> new ResourceNotFoundException("Message", request.getParentMessageId()));

        if (!parentMessage.getConversation().getId().equals(conversationId)) {
            throw new BadRequestException("Message does not belong to this conversation");
        }

        // Check if this is the first message (cannot branch from first message)
        List<Message> messages = messageRepository.findByConversationIdOrderByCreatedAtAsc(conversationId);
        int messageIndex = messages.indexOf(parentMessage);
        if (messageIndex == 0) {
            throw new BadRequestException("Cannot branch from the first message - there is no prior context");
        }

        // Check branch depth
        Integer currentDepth = parentConversation.getBranchDepth() != null ? parentConversation.getBranchDepth() : 0;
        if (currentDepth >= MAX_BRANCH_DEPTH) {
            throw new BadRequestException("Maximum branch depth of " + MAX_BRANCH_DEPTH + " reached");
        }

        // Determine learning mode
        Conversation.LearningMode learningMode = parentConversation.getLearningMode();
        if (request.getLearningMode() != null) {
            try {
                learningMode = Conversation.LearningMode.valueOf(request.getLearningMode().toUpperCase());
            } catch (IllegalArgumentException e) {
                throw new BadRequestException("Invalid learning mode: " + request.getLearningMode());
            }
        }

        // Use anchorText as the branch title (or fall back to branchContext or default)
        String branchTitle = request.getAnchorText();
        if (branchTitle == null || branchTitle.trim().isEmpty()) {
            branchTitle = request.getBranchContext();
        }
        if (branchTitle == null || branchTitle.trim().isEmpty()) {
            branchTitle = "Branch: " + parentConversation.getTitle();
        }

        // Create branch conversation
        Conversation branchConversation = Conversation.builder()
                .title(branchTitle)
                .learningMode(learningMode)
                .isBranch(true)
                .parentConversation(parentConversation)
                .branchContext(request.getBranchContext())
                .branchStatus(Conversation.BranchStatus.ACTIVE)
                .topic(parentConversation.getTopic())
                .branchDepth(currentDepth + 1)
                .build();
        branchConversation = conversationRepository.save(branchConversation);

        // Copy messages up to and including the parent message
        List<Message> messagesToCopy = messages.subList(0, messageIndex + 1);
        Map<Long, Long> messageIdMapping = new HashMap<>();
        for (Message originalMessage : messagesToCopy) {
            Message copiedMessage = Message.builder()
                    .role(originalMessage.getRole())
                    .content(originalMessage.getContent())
                    .sources(originalMessage.getSources())
                    .tokensUsed(originalMessage.getTokensUsed())
                    .conversation(branchConversation)
                    .build();
            copiedMessage = messageRepository.save(copiedMessage);
            messageIdMapping.put(originalMessage.getId(), copiedMessage.getId());

            // Mark the parent message as having spawned a branch
            if (originalMessage.getId().equals(parentMessage.getId())) {
                originalMessage.setBranchMessageId(copiedMessage.getId());
                if (request.getSelectionStart() != null) {
                    originalMessage.setSelectionStart(request.getSelectionStart());
                }
                if (request.getSelectionEnd() != null) {
                    originalMessage.setSelectionEnd(request.getSelectionEnd());
                }
                messageRepository.save(originalMessage);
            }
        }

        // Create ConversationBranch record
        String selectedText = null;
        if (request.getSelectionStart() != null && request.getSelectionEnd() != null) {
            int start = Math.min(request.getSelectionStart(), request.getSelectionEnd());
            int end = Math.max(request.getSelectionStart(), request.getSelectionEnd());
            if (start >= 0 && end <= parentMessage.getContent().length()) {
                selectedText = parentMessage.getContent().substring(start, end);
            }
        }

        // Use anchorText for branch context
        String finalBranchContext = request.getAnchorText();
        if (finalBranchContext == null || finalBranchContext.trim().isEmpty()) {
            finalBranchContext = request.getBranchContext();
        }

        ConversationBranch parentBranch = parentConversation.getBranchOf();

        ConversationBranch branch = ConversationBranch.builder()
                .parentConversation(parentConversation)
                .branchConversation(branchConversation)
                .parentMessageId(parentMessage.getId())
                .parentMessageSnapshot(parentMessage.getContent())
                .selectionStart(request.getSelectionStart())
                .selectionEnd(request.getSelectionEnd())
                .branchContext(finalBranchContext)
                .branchStatus(ConversationBranch.BranchStatus.ACTIVE)
                .createdBy(user)
                .parentBranch(parentBranch)
                .branchDepth(currentDepth + 1)
                .build();
        branch = conversationBranchRepository.save(branch);

        // Link branch conversation to the branch record
        branchConversation.setBranchOf(branch);
        conversationRepository.save(branchConversation);

        // Build breadcrumb ancestry
        List<BranchBreadcrumb> ancestry = buildBreadcrumb(branch);

        // Build parent context (last 6-10 messages before the branch point)
        int contextStart = Math.max(0, messageIndex - 9);
        List<Message> contextMessages = messages.subList(contextStart, messageIndex + 1);
        List<MessageResponse> parentContextMessages = contextMessages.stream()
                .map(this::toMessageResponse)
                .collect(Collectors.toList());

        // Build anchor text from selection
        String parentAnchorText = selectedText;
        if (parentAnchorText != null && parentAnchorText.length() > 100) {
            parentAnchorText = parentAnchorText.substring(0, 100) + "...";
        }

        // Build system prompt for the branch (hidden from user)
        StringBuilder systemPromptBuilder = new StringBuilder();
        systemPromptBuilder.append("This is a focused branch conversation.\n");
        systemPromptBuilder.append("The user was discussing: ").append(parentConversation.getTitle()).append("\n");
        systemPromptBuilder.append("Recent parent context:\n");
        for (int i = 0; i < Math.min(6, parentContextMessages.size()); i++) {
            MessageResponse msg = parentContextMessages.get(i);
            systemPromptBuilder.append("- ").append(msg.getRole()).append(": ").append(msg.getContent()).append("\n");
        }
        if (selectedText != null) {
            systemPromptBuilder.append("They want to explore the specific concept: \"").append(selectedText).append("\"\n");
            systemPromptBuilder.append("Start by explaining \"").append(selectedText).append("\" in depth.\n");
        }
        String systemPrompt = systemPromptBuilder.toString();

        return BranchNavigationResponse.builder()
                .parentConversation(toConversationSummary(parentConversation))
                .branchConversation(toConversationResponse(branchConversation))
                .parentMessageIndex(messageIndex)
                .ancestry(ancestry)
                .parentContextMessages(parentContextMessages)
                .parentAnchorText(parentAnchorText)
                .branchTitle(branchConversation.getTitle())
                .systemPrompt(systemPrompt)
                .build();
    }

    @Transactional(readOnly = true)
    public List<BranchBreadcrumb> getBreadcrumb(Long branchId, User user) {
        ConversationBranch branch = conversationBranchRepository.findByIdAndUserId(branchId, user.getId())
                .orElseThrow(() -> new ResourceNotFoundException("Branch", branchId));
        return buildBreadcrumb(branch);
    }

    @Transactional(readOnly = true)
    public BranchNavigationResponse navigateToParent(Long branchId, User user) {
        ConversationBranch branch = conversationBranchRepository.findByIdAndUserId(branchId, user.getId())
                .orElseThrow(() -> new ResourceNotFoundException("Branch", branchId));

        Conversation parentConversation = branch.getParentConversation();
        List<Message> parentMessages = messageRepository.findByConversationIdOrderByCreatedAtAsc(parentConversation.getId());
        int messageIndex = -1;
        for (int i = 0; i < parentMessages.size(); i++) {
            if (parentMessages.get(i).getId().equals(branch.getParentMessageId())) {
                messageIndex = i;
                break;
            }
        }

        List<BranchBreadcrumb> ancestry = buildBreadcrumb(branch.getParentBranch());

        return BranchNavigationResponse.builder()
                .parentConversation(toConversationResponse(parentConversation))
                .branchConversation(toConversationSummary(branch.getBranchConversation()))
                .parentMessageIndex(messageIndex)
                .ancestry(ancestry)
                .build();
    }

    @Transactional(readOnly = true)
    public List<ConversationResponse> getBranchesFromMessage(Long messageId, User user) {
        Message message = messageRepository.findById(messageId)
                .orElseThrow(() -> new ResourceNotFoundException("Message", messageId));

        List<ConversationBranch> branches = conversationBranchRepository.findActiveBranchesByMessageId(messageId);
        List<ConversationResponse> result = new ArrayList<>();
        for (ConversationBranch cb : branches) {
            result.add(toConversationSummary(cb.getBranchConversation()));
        }
        return result;
    }

    private List<BranchBreadcrumb> buildBreadcrumb(ConversationBranch branch) {
        List<BranchBreadcrumb> ancestry = new ArrayList<>();

        // Build path from root to current branch
        ConversationBranch current = branch;
        while (current != null) {
            Conversation conv = current.getBranchConversation();
            ancestry.add(0, BranchBreadcrumb.builder()
                    .conversationId(conv.getId())
                    .title(conv.getTitle())
                    .branchId(current.getId())
                    .depth(current.getBranchDepth())
                    .isCurrent(current.getId().equals(branch.getId()))
                    .build());
            current = current.getParentBranch();
        }

        // Add root conversation if not already there
        if (!ancestry.isEmpty()) {
            Conversation rootParent = ancestry.get(0).getConversationId() != null ?
                    conversationRepository.findById(ancestry.get(0).getConversationId())
                            .orElse(null) : null;
            if (rootParent != null && rootParent.getParentConversation() != null) {
                ancestry.add(0, BranchBreadcrumb.builder()
                        .conversationId(rootParent.getId())
                        .title(rootParent.getTitle())
                        .branchId(null)
                        .depth(0)
                        .isCurrent(false)
                        .build());
            }
        }

        return ancestry;
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
                .branchOfId(conversation.getBranchOf() != null ? conversation.getBranchOf().getId() : null)
                .branchDepth(conversation.getBranchDepth())
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
                .branchOfId(conversation.getBranchOf() != null ? conversation.getBranchOf().getId() : null)
                .branchDepth(conversation.getBranchDepth())
                .createdAt(conversation.getCreatedAt())
                .updatedAt(conversation.getUpdatedAt())
                .build();
    }

    private MessageResponse toMessageResponse(Message message) {
        // Get branches for this message
        List<ConversationBranch> branches = conversationBranchRepository.findActiveBranchesByMessageId(message.getId());
        List<MessageBranchInfo> branchInfos = branches.stream()
                .map(cb -> MessageBranchInfo.builder()
                        .branchId(cb.getId())
                        .branchConversationId(cb.getBranchConversation().getId())
                        .selectionStart(cb.getSelectionStart())
                        .selectionEnd(cb.getSelectionEnd())
                        .title(cb.getBranchConversation().getTitle())
                        .branchContext(cb.getBranchContext())
                        .build())
                .collect(Collectors.toList());

        return MessageResponse.builder()
                .id(message.getId())
                .role(message.getRole().name())
                .content(message.getContent())
                .sources(message.getSources())
                .tokensUsed(message.getTokensUsed())
                .branchMessageId(message.getBranchMessageId())
                .selectionStart(message.getSelectionStart())
                .selectionEnd(message.getSelectionEnd())
                .createdAt(message.getCreatedAt())
                .hasBranches(!branches.isEmpty())
                .branches(branchInfos)
                .build();
    }
}
