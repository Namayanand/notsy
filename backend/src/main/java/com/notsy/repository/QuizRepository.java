package com.notsy.repository;

import com.notsy.entity.Quiz;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;
import org.springframework.stereotype.Repository;

import java.util.List;
import java.util.Optional;

@Repository
public interface QuizRepository extends JpaRepository<Quiz, Long> {

    List<Quiz> findByUserIdOrderByCreatedAtDesc(Long userId);

    List<Quiz> findByTopicIdOrderByCreatedAtDesc(Long topicId);

    @Query("SELECT q FROM Quiz q WHERE q.topic.id = :topicId AND q.user.id = :userId ORDER BY q.createdAt DESC")
    List<Quiz> findByTopicIdAndUserId(@Param("topicId") Long topicId, @Param("userId") Long userId);

    @Query("SELECT q FROM Quiz q WHERE q.user.id = :userId ORDER BY q.createdAt DESC")
    List<Quiz> findByUserId(@Param("userId") Long userId);

    @Query("SELECT q FROM Quiz q LEFT JOIN FETCH q.questions WHERE q.id = :quizId")
    Optional<Quiz> findByIdWithQuestions(@Param("quizId") Long quizId);

    @Query("SELECT AVG(CAST(JSON_VALUE(q.weakAreas, '$.score') AS double)) FROM Quiz q WHERE q.topic.id = :topicId AND q.user.id = :userId")
    Double findAverageScoreByTopic(@Param("topicId") Long topicId, @Param("userId") Long userId);

    @Query("SELECT q FROM Quiz q WHERE q.completedAt IS NOT NULL AND q.topic.id = :topicId AND q.user.id = :userId ORDER BY q.completedAt DESC")
    List<Quiz> findCompletedByTopicIdAndUserId(@Param("topicId") Long topicId, @Param("userId") Long userId);
}
