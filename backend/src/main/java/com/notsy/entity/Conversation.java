package com.notsy.entity;

import jakarta.persistence.*;
import lombok.*;
import org.hibernate.annotations.CreationTimestamp;
import org.hibernate.annotations.UpdateTimestamp;

import java.time.LocalDateTime;
import java.util.ArrayList;
import java.util.List;

@Entity
@Table(name = "conversations")
@Getter
@Setter
@NoArgsConstructor
@AllArgsConstructor
@Builder
public class Conversation {

    public enum LearningMode {
        GO_CRAZY, DEV_MODE, MASTER_THIS, LAST_MINUTE, TEACH_ME_TECH
    }

    public enum BranchStatus {
        ACTIVE, MERGED, DISCARDED
    }

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(nullable = false)
    private String title;

    @Enumerated(EnumType.STRING)
    @Column(name = "learning_mode")
    @Builder.Default
    private LearningMode learningMode = LearningMode.MASTER_THIS;

    @Builder.Default
    @Column(name = "is_branch")
    private Boolean isBranch = false;

    @ManyToOne(fetch = FetchType.LAZY)
    @JoinColumn(name = "parent_conversation_id")
    private Conversation parentConversation;

    @OneToMany(mappedBy = "parentConversation")
    @Builder.Default
    private List<Conversation> branches = new ArrayList<>();

    @Column(name = "branch_context", columnDefinition = "TEXT")
    private String branchContext;

    @Enumerated(EnumType.STRING)
    @Column(name = "branch_status")
    @Builder.Default
    private BranchStatus branchStatus = BranchStatus.ACTIVE;

    @ManyToOne(fetch = FetchType.LAZY)
    @JoinColumn(name = "conversation_branch_id")
    private ConversationBranch branchOf;

    @Column(name = "branch_depth")
    @Builder.Default
    private Integer branchDepth = 0;

    @ManyToOne(fetch = FetchType.LAZY)
    @JoinColumn(name = "topic_id", nullable = false)
    private Topic topic;

    @OneToMany(mappedBy = "conversation", cascade = CascadeType.ALL, orphanRemoval = true)
    @OrderBy("createdAt ASC")
    @Builder.Default
    private List<Message> messages = new ArrayList<>();

    @CreationTimestamp
    @Column(name = "created_at", updatable = false)
    private LocalDateTime createdAt;

    @UpdateTimestamp
    @Column(name = "updated_at")
    private LocalDateTime updatedAt;
}
