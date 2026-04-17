package com.notsy.repository;

import com.notsy.entity.MemoryEntry;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;
import java.util.List;

@Repository
public interface MemoryEntryRepository extends JpaRepository<MemoryEntry, Long> {
    List<MemoryEntry> findByUserIdOrderByCreatedAtDesc(Long userId);
    List<MemoryEntry> findByUserIdAndMemoryType(Long userId, String memoryType);
    List<MemoryEntry> findByUserIdAndTopic(Long userId, String topic);
}