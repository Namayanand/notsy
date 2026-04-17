package com.notsy.dto.response;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.util.List;

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class BranchNavigationResponse {
    private ConversationResponse parentConversation;
    private ConversationResponse branchConversation;
    private Integer parentMessageIndex;
    private List<BranchBreadcrumb> ancestry;
    private List<MessageResponse> parentContextMessages;
    private String parentAnchorText;
    private String branchTitle;
    private String systemPrompt;
}