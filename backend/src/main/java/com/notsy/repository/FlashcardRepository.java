package com.notsy.repository;

import com.notsy.entity.Flashcard;
import org.springframework.data.domain.Pageable;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;
import org.springframework.stereotype.Repository;

import java.time.LocalDateTime;
import java.util.List;

@Repository
public interface FlashcardRepository extends JpaRepository<Flashcard, Long> {

    List<Flashcard> findByUserIdOrderByCreatedAtDesc(Long userId);

    List<Flashcard> findByTopicIdOrderByCreatedAtDesc(Long topicId);

    @Query("SELECT f FROM Flashcard f WHERE f.topic.id = :topicId AND f.nextReviewDate <= :now AND f.user.id = :userId ORDER BY f.nextReviewDate ASC")
    List<Flashcard> findDueCards(@Param("topicId") Long topicId, @Param("userId") Long userId, @Param("now") LocalDateTime now, Pageable pageable);

    @Query("SELECT f FROM Flashcard f WHERE f.nextReviewDate <= :now AND f.user.id = :userId ORDER BY f.nextReviewDate ASC")
    List<Flashcard> findAllDueCards(@Param("userId") Long userId, @Param("now") LocalDateTime now, Pageable pageable);

    @Query("SELECT COUNT(f) FROM Flashcard f WHERE f.topic.id = :topicId AND f.user.id = :userId")
    long countByTopicId(@Param("topicId") Long topicId, @Param("userId") Long userId);

    @Query("SELECT f FROM Flashcard f WHERE f.topic.id IN (SELECT nm.notebook.id FROM com.notsy.entity.NotebookMembership nm WHERE nm.user.id = :userId) AND f.isShared = true")
    List<Flashcard> findSharedCards(@Param("userId") Long userId);

    @Query("SELECT f FROM Flashcard f WHERE f.user.id = :userId AND f.isShared = true")
    List<Flashcard> findCardsSharedByUser(@Param("userId") Long userId);

    void deleteByTopicId(Long topicId);
}
