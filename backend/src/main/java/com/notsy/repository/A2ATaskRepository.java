package com.notsy.repository;

import com.notsy.entity.A2ATask;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.Pageable;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

import java.util.List;
import java.util.UUID;

/**
 * Repository for A2A task tracking
 */
@Repository
public interface A2ATaskRepository extends JpaRepository<A2ATask, UUID> {

    List<A2ATask> findByUserIdOrderByCreatedAtDesc(UUID userId);

    Page<A2ATask> findByUserId(UUID userId, Pageable pageable);

    List<A2ATask> findByUserIdAndStatusOrderByCreatedAtDesc(UUID userId, com.notsy.a2a.A2ATaskStatus status);
}