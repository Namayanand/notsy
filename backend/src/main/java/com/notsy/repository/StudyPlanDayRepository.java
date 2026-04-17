package com.notsy.repository;

import com.notsy.entity.StudyPlanDay;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

import java.util.List;

@Repository
public interface StudyPlanDayRepository extends JpaRepository<StudyPlanDay, Long> {

    List<StudyPlanDay> findByPlanIdOrderByDayNumberAscOrderIndexAsc(Long planId);

    List<StudyPlanDay> findByPlanIdAndIsCompletedFalse(Long planId);
}
