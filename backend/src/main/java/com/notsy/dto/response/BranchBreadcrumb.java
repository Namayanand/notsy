package com.notsy.dto.response;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class BranchBreadcrumb {
    private Long conversationId;
    private String title;
    private Long branchId;
    private Integer depth;
    private Boolean isCurrent;
}