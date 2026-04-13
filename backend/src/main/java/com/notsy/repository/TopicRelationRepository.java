package com.notsy.repository;

import com.notsy.entity.TopicRelation;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Modifying;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;
import org.springframework.stereotype.Repository;

import java.util.List;
import java.util.Optional;

@Repository
public interface TopicRelationRepository extends JpaRepository<TopicRelation, Long> {
    @Query("SELECT tr FROM TopicRelation tr WHERE tr.sourceTopic.notebook.id = :notebookId OR tr.targetTopic.notebook.id = :notebookId")
    List<TopicRelation> findByNotebookId(@Param("notebookId") Long notebookId);

    @Query("SELECT tr FROM TopicRelation tr WHERE tr.id = :id AND (tr.sourceTopic.notebook.id = :notebookId OR tr.targetTopic.notebook.id = :notebookId)")
    Optional<TopicRelation> findByIdAndNotebookId(@Param("id") Long id, @Param("notebookId") Long notebookId);

    @Query("SELECT tr FROM TopicRelation tr WHERE tr.sourceTopic.notebook.user.id = :userId")
    List<TopicRelation> findByUserId(@Param("userId") Long userId);

    @Query("SELECT tr FROM TopicRelation tr WHERE (tr.sourceTopic.id = :topicId OR tr.targetTopic.id = :topicId) AND tr.sourceTopic.notebook.user.id = :userId")
    List<TopicRelation> findByTopicIdAndUserId(@Param("topicId") Long topicId, @Param("userId") Long userId);

    @Query("SELECT tr FROM TopicRelation tr WHERE tr.sourceTopic.id = :sourceTopicId AND tr.targetTopic.id = :targetTopicId")
    Optional<TopicRelation> findBySourceTopicIdAndTargetTopicId(@Param("sourceTopicId") Long sourceTopicId, @Param("targetTopicId") Long targetTopicId);

    @Modifying
    @Query("DELETE FROM TopicRelation tr WHERE tr.sourceTopic.id = :sourceTopicId OR tr.targetTopic.id = :targetTopicId")
    void deleteBySourceTopicIdOrTargetTopicId(@Param("sourceTopicId") Long sourceTopicId, @Param("targetTopicId") Long targetTopicId);

    @Modifying
    @Query("DELETE FROM TopicRelation tr WHERE tr.sourceTopic.notebook.id = :notebookId OR tr.targetTopic.notebook.id = :notebookId")
    void deleteAllByNotebook(@Param("notebookId") Long notebookId);

    @Modifying
    @Query("DELETE FROM TopicRelation tr WHERE tr.sourceTopic.notebook.id = :notebookId")
    void deleteAllBySourceTopicNotebookId(@Param("notebookId") Long notebookId);
}
