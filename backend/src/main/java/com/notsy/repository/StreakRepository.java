package com.notsy.repository;

import com.notsy.entity.Streak;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;
import org.springframework.stereotype.Repository;

import java.time.LocalDate;
import java.util.List;
import java.util.Optional;

@Repository
public interface StreakRepository extends JpaRepository<Streak, Long> {

    Optional<Streak> findByUserIdAndTopic_Id(Long userId, Long topicId);

    Optional<Streak> findByUserIdAndIsGlobalTrue(Long userId);

    @Query("SELECT s FROM Streak s WHERE s.user.id = :userId AND s.isGlobal = false")
    List<Streak> findByUserId(@Param("userId") Long userId);

    @Query("SELECT s FROM Streak s WHERE s.topic.id = :topicId AND s.lastReviewDate < :date AND s.user.id != :excludeUserId")
    List<Streak> findNeedingNudge(@Param("topicId") Long topicId, @Param("date") LocalDate date, @Param("excludeUserId") Long excludeUserId);

    @Query("SELECT s FROM Streak s WHERE s.lastReviewDate < :date AND s.isGlobal = true")
    List<Streak> findGlobalStreaksNeedingNudge(@Param("date") LocalDate date);
}
