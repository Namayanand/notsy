package com.notsy.repository;

import com.notsy.entity.Conversation;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;
import org.springframework.stereotype.Repository;

import java.util.List;
import java.util.Optional;

@Repository
public interface ConversationRepository extends JpaRepository<Conversation, Long> {
    @Query("SELECT c FROM Conversation c WHERE c.topic.id = :topicId AND c.isBranch = false ORDER BY c.createdAt DESC")
    List<Conversation> findByTopicIdAndIsBranchFalseOrderByCreatedAtDesc(@Param("topicId") Long topicId);

    List<Conversation> findByParentConversationIdOrderByCreatedAtAsc(Long parentConversationId);

    @Query("SELECT c FROM Conversation c WHERE c.id = :id AND c.topic.id = :topicId")
    Optional<Conversation> findByIdAndTopicId(@Param("id") Long id, @Param("topicId") Long topicId);

    @Query("SELECT c FROM Conversation c WHERE c.id = :id AND c.topic.notebook.user.id = :userId")
    Optional<Conversation> findByIdAndUserId(@Param("id") Long id, @Param("userId") Long userId);

    @Query("SELECT c FROM Conversation c WHERE c.id = :id AND c.topic.id = :topicId AND c.topic.notebook.user.id = :userId")
    Optional<Conversation> findByIdAndTopicIdAndUserId(@Param("id") Long id, @Param("topicId") Long topicId, @Param("userId") Long userId);

    @Query("SELECT c FROM Conversation c WHERE c.parentConversation.id = :parentId AND c.topic.notebook.user.id = :userId")
    List<Conversation> findBranchesByParentIdAndUserId(@Param("parentId") Long parentId, @Param("userId") Long userId);

    @Query("SELECT c FROM Conversation c WHERE c.topic.id = :topicId AND c.topic.notebook.user.id = :userId")
    List<Conversation> findByTopicIdAndUserId(@Param("topicId") Long topicId, @Param("userId") Long userId);

    void deleteByTopicId(Long topicId);
}
