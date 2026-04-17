package com.notsy.repository;

import com.notsy.entity.ConversationBranch;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;
import org.springframework.stereotype.Repository;

import java.util.List;
import java.util.Optional;

@Repository
public interface ConversationBranchRepository extends JpaRepository<ConversationBranch, Long> {

    List<ConversationBranch> findByParentConversationIdAndBranchStatusOrderByCreatedAtDesc(
            Long parentConversationId, ConversationBranch.BranchStatus status);

    List<ConversationBranch> findByBranchConversationId(Long branchConversationId);

    @Query("SELECT cb FROM ConversationBranch cb WHERE cb.branchConversation.id = :conversationId AND cb.branchStatus = 'ACTIVE'")
    Optional<ConversationBranch> findActiveBranchByConversationId(@Param("conversationId") Long conversationId);

    @Query("SELECT cb FROM ConversationBranch cb WHERE cb.parentConversation.id = :conversationId AND cb.createdBy.id = :userId")
    List<ConversationBranch> findByParentConversationIdAndUserId(
            @Param("conversationId") Long conversationId, @Param("userId") Long userId);

    @Query("SELECT cb FROM ConversationBranch cb WHERE cb.parentMessageId = :messageId AND cb.branchStatus = 'ACTIVE'")
    List<ConversationBranch> findActiveBranchesByMessageId(@Param("messageId") Long messageId);

    @Query("SELECT cb FROM ConversationBranch cb WHERE cb.id = :id AND cb.createdBy.id = :userId")
    Optional<ConversationBranch> findByIdAndUserId(@Param("id") Long id, @Param("userId") Long userId);
}