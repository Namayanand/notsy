package com.notsy.service;

import com.notsy.entity.MemoryEntry;
import com.notsy.repository.MemoryEntryRepository;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;
import java.util.List;
import java.util.Optional;

@Service
public class MemoryService {

    @Autowired
    private MemoryEntryRepository memoryEntryRepository;

    public MemoryEntry createEntry(MemoryEntry entry) {
        return memoryEntryRepository.save(entry);
    }

    public List<MemoryEntry> getUserMemories(Long userId) {
        return memoryEntryRepository.findByUserIdOrderByCreatedAtDesc(userId);
    }

    public List<MemoryEntry> getUserMemoriesByType(Long userId, String memoryType) {
        return memoryEntryRepository.findByUserIdAndMemoryType(userId, memoryType);
    }

    public List<MemoryEntry> getUserMemoriesByTopic(Long userId, String topic) {
        return memoryEntryRepository.findByUserIdAndTopic(userId, topic);
    }

    public Optional<MemoryEntry> getById(Long id) {
        return memoryEntryRepository.findById(id);
    }

    public void deleteEntry(Long id) {
        memoryEntryRepository.deleteById(id);
    }
}