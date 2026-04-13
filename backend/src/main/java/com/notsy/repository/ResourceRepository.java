package com.notsy.repository;

import com.notsy.entity.Resource;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;
import org.springframework.stereotype.Repository;

import java.util.List;
import java.util.Optional;

@Repository
public interface ResourceRepository extends JpaRepository<Resource, Long> {
    List<Resource> findByTopicIdOrderByCreatedAtDesc(Long topicId);

    @Query("SELECT r FROM Resource r WHERE r.id = :id AND r.topic.id = :topicId")
    Optional<Resource> findByIdAndTopicId(@Param("id") Long id, @Param("topicId") Long topicId);

    @Query("SELECT r FROM Resource r WHERE r.id = :id AND r.topic.id = :topicId AND r.topic.notebook.user.id = :userId")
    Optional<Resource> findByIdAndTopicIdAndUserId(@Param("id") Long id, @Param("topicId") Long topicId, @Param("userId") Long userId);

    @Query("SELECT r FROM Resource r WHERE r.topic.notebook.id = :notebookId")
    List<Resource> findByNotebookId(@Param("notebookId") Long notebookId);

    @Query("SELECT r FROM Resource r WHERE r.topic.id = :topicId AND r.topic.notebook.user.id = :userId")
    List<Resource> findByTopicIdAndUserId(@Param("topicId") Long topicId, @Param("userId") Long userId);

    void deleteByTopicId(Long topicId);
}
