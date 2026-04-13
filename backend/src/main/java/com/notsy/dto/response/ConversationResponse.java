package com.notsy.dto.response;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.time.LocalDateTime;
import java.util.List;

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class ConversationResponse {
    private Long id;
    private String title;
    private String learningMode;
    private Boolean isBranch;
    private Long parentConversationId;
    private String branchContext;
    private String branchStatus;
    private Long topicId;
    private List<MessageResponse> messages;
    private LocalDateTime createdAt;
    private LocalDateTime updatedAt;
}
