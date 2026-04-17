package com.notsy.entity;

import jakarta.persistence.*;
import lombok.*;
import org.hibernate.annotations.CreationTimestamp;

import java.time.LocalDateTime;

@Entity
@Table(name = "conversation_branches")
@Getter
@Setter
@NoArgsConstructor
@AllArgsConstructor
@Builder
public class ConversationBranch {

    public enum BranchStatus {
        ACTIVE, MERGED, DISCARDED
    }

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @ManyToOne(fetch = FetchType.LAZY)
    @JoinColumn(name = "parent_conversation_id", nullable = false)
    private Conversation parentConversation;

    @OneToOne(fetch = FetchType.LAZY)
    @JoinColumn(name = "branch_conversation_id", nullable = false)
    private Conversation branchConversation;

    @Column(name = "parent_message_id")
    private Long parentMessageId;

    @Column(name = "parent_message_snapshot", columnDefinition = "TEXT")
    private String parentMessageSnapshot;

    @Column(name = "selection_start")
    private Integer selectionStart;

    @Column(name = "selection_end")
    private Integer selectionEnd;

    @Column(name = "branch_context", columnDefinition = "TEXT")
    private String branchContext;

    @Enumerated(EnumType.STRING)
    @Column(name = "branch_status")
    @Builder.Default
    private BranchStatus branchStatus = BranchStatus.ACTIVE;

    @ManyToOne(fetch = FetchType.LAZY)
    @JoinColumn(name = "created_by_user_id", nullable = false)
    private User createdBy;

    @ManyToOne(fetch = FetchType.LAZY)
    @JoinColumn(name = "parent_branch_id")
    private ConversationBranch parentBranch;

    @OneToMany(mappedBy = "parentBranch")
    @Builder.Default
    private java.util.List<ConversationBranch> childBranches = new java.util.ArrayList<>();

    @Column(name = "branch_depth")
    @Builder.Default
    private Integer branchDepth = 0;

    @CreationTimestamp
    @Column(name = "created_at", updatable = false)
    private LocalDateTime createdAt;
}