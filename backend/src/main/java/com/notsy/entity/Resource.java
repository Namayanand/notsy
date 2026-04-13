package com.notsy.entity;

import jakarta.persistence.*;
import lombok.*;
import org.hibernate.annotations.CreationTimestamp;

import java.time.LocalDateTime;

@Entity
@Table(name = "resources")
@Getter
@Setter
@NoArgsConstructor
@AllArgsConstructor
@Builder
public class Resource {

    public enum FileType {
        pdf, image, video, link, text
    }

    public enum EmbeddingStatus {
        PENDING, PROCESSING, DONE, FAILED
    }

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(name = "filename", nullable = false)
    private String filename;

    @Column(name = "original_name", nullable = false)
    private String originalName;

    @Column(name = "file_path")
    private String filePath;

    @Enumerated(EnumType.STRING)
    @Column(name = "file_type", nullable = false)
    private FileType fileType;

    @Column(name = "file_size")
    private Long fileSize;

    @Column(name = "source_url")
    private String sourceUrl;

    @Enumerated(EnumType.STRING)
    @Column(name = "embedding_status")
    @Builder.Default
    private EmbeddingStatus embeddingStatus = EmbeddingStatus.PENDING;

    @Column(name = "chunk_count")
    private Integer chunkCount;

    @ManyToOne(fetch = FetchType.LAZY)
    @JoinColumn(name = "topic_id", nullable = false)
    private Topic topic;

    @CreationTimestamp
    @Column(name = "created_at", updatable = false)
    private LocalDateTime createdAt;
}
