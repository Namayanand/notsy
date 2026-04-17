package com.notsy.dto.response;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class MessageBranchInfo {
    private Long branchId;
    private Long branchConversationId;
    private Integer selectionStart;
    private Integer selectionEnd;
    private String title;
    private String branchContext;
}