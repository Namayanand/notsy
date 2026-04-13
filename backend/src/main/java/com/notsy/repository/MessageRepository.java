package com.notsy.repository;

import com.notsy.entity.Message;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;
import org.springframework.stereotype.Repository;

import java.util.List;
import java.util.Optional;

@Repository
public interface MessageRepository extends JpaRepository<Message, Long> {
    List<Message> findByConversationIdOrderByCreatedAtAsc(Long conversationId);

    @Query("SELECT m FROM Message m WHERE m.conversation.id = :conversationId ORDER BY m.createdAt DESC")
    List<Message> findRecentMessages(@Param("conversationId") Long conversationId);

    @Query("SELECT m FROM Message m WHERE m.conversation.id = :conversationId ORDER BY m.createdAt DESC LIMIT :limit")
    List<Message> findLastMessages(@Param("conversationId") Long conversationId, @Param("limit") int limit);

    Optional<Message> findTopByConversationIdOrderByCreatedAtDesc(Long conversationId);

    void deleteByConversationId(Long conversationId);
}
