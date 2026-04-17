package com.notsy.repository;

import com.notsy.entity.StudyPlan;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;
import org.springframework.stereotype.Repository;

import java.util.List;
import java.util.Optional;

@Repository
public interface StudyPlanRepository extends JpaRepository<StudyPlan, Long> {

    List<StudyPlan> findByUserIdOrderByCreatedAtDesc(Long userId);

    @Query("SELECT sp FROM StudyPlan sp WHERE sp.user.id = :userId AND sp.isCompleted = false ORDER BY sp.createdAt DESC")
    List<StudyPlan> findActiveByUserId(@Param("userId") Long userId);

    @Query("SELECT sp FROM StudyPlan sp LEFT JOIN FETCH sp.days WHERE sp.id = :planId")
    Optional<StudyPlan> findByIdWithDays(@Param("planId") Long planId);
}
