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
public class MessageResponse {
    private Long id;
    private String role;
    private String content;
    private String sources;
    private Integer tokensUsed;
    private Long branchMessageId;
    private Integer selectionStart;
    private Integer selectionEnd;
    private LocalDateTime createdAt;
    private Boolean hasBranches;
    private List<MessageBranchInfo> branches;
}
