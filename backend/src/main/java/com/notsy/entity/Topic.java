package com.notsy.entity;

import jakarta.persistence.*;
import lombok.*;
import org.hibernate.annotations.CreationTimestamp;

import java.time.LocalDateTime;
import java.util.ArrayList;
import java.util.List;

@Entity
@Table(name = "topics")
@Getter
@Setter
@NoArgsConstructor
@AllArgsConstructor
@Builder
public class Topic {

    public enum EmbeddingStatus {
        PENDING, PROCESSING, DONE, FAILED
    }

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(nullable = false)
    private String title;

    @Column(columnDefinition = "TEXT")
    private String description;

    @Column(name = "order_index")
    private Integer orderIndex;

    @ManyToOne(fetch = FetchType.LAZY)
    @JoinColumn(name = "notebook_id", nullable = false)
    private Notebook notebook;

    @ManyToOne(fetch = FetchType.LAZY)
    @JoinColumn(name = "parent_topic_id")
    private Topic parentTopic;

    @OneToMany(mappedBy = "parentTopic", cascade = CascadeType.ALL)
    @OrderBy("orderIndex ASC")
    @Builder.Default
    private List<Topic> subtopics = new ArrayList<>();

    @Enumerated(EnumType.STRING)
    @Column(name = "embedding_status")
    @Builder.Default
    private EmbeddingStatus embeddingStatus = EmbeddingStatus.PENDING;

    @ElementCollection
    @CollectionTable(name = "topic_tags", joinColumns = @JoinColumn(name = "topic_id"))
    @Column(name = "tag")
    @Builder.Default
    private List<String> tags = new ArrayList<>();

    @OneToMany(mappedBy = "topic", cascade = CascadeType.ALL, orphanRemoval = true)
    @Builder.Default
    private List<Resource> resources = new ArrayList<>();

    @OneToMany(mappedBy = "topic", cascade = CascadeType.ALL, orphanRemoval = true)
    @Builder.Default
    private List<Conversation> conversations = new ArrayList<>();

    @CreationTimestamp
    @Column(name = "created_at", updatable = false)
    private LocalDateTime createdAt;

    @Transient
    public boolean isSubtopic() {
        return parentTopic != null;
    }
}
