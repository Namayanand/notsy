package com.notsy.repository;

import com.notsy.entity.Topic;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;
import org.springframework.stereotype.Repository;

import java.util.List;
import java.util.Optional;

@Repository
public interface TopicRepository extends JpaRepository<Topic, Long> {
    List<Topic> findByNotebookIdAndParentTopicIsNullOrderByOrderIndexAsc(Long notebookId);

    List<Topic> findByNotebookIdOrderByOrderIndexAsc(Long notebookId);

    @Query("SELECT t FROM Topic t WHERE t.id = :id AND t.notebook.id = :notebookId")
    Optional<Topic> findByIdAndNotebookId(@Param("id") Long id, @Param("notebookId") Long notebookId);

    @Query("SELECT t FROM Topic t WHERE t.id = :id AND t.notebook.user.id = :userId")
    Optional<Topic> findByIdAndUserId(@Param("id") Long id, @Param("userId") Long userId);

    @Query("SELECT t FROM Topic t WHERE t.id = :topicId AND t.notebook.id = :notebookId AND t.notebook.user.id = :userId")
    Optional<Topic> findByIdAndNotebookIdAndUserId(@Param("topicId") Long topicId, @Param("notebookId") Long notebookId, @Param("userId") Long userId);

    @Query("SELECT COALESCE(MAX(t.orderIndex), 0) FROM Topic t WHERE t.notebook.id = :notebookId AND t.parentTopic IS NULL")
    Integer findMaxOrderIndexForNotebook(@Param("notebookId") Long notebookId);

    @Query("SELECT COALESCE(MAX(t.orderIndex), 0) FROM Topic t WHERE t.parentTopic.id = :parentTopicId")
    Integer findMaxOrderIndexForParent(@Param("parentTopicId") Long parentTopicId);

    void deleteByNotebookId(Long notebookId);
}
