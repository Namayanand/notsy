package com.notsy.entity;

import jakarta.persistence.*;
import lombok.*;
import org.hibernate.annotations.CreationTimestamp;

import java.time.LocalDateTime;

@Entity
@Table(name = "topic_relations",
       uniqueConstraints = @UniqueConstraint(columnNames = {"source_topic_id", "target_topic_id"}))
@Getter
@Setter
@NoArgsConstructor
@AllArgsConstructor
@Builder
public class TopicRelation {

    public enum RelationshipType {
        RELATED, PREREQUISITE, EXTENDS, CONTRASTS
    }

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @ManyToOne(fetch = FetchType.LAZY)
    @JoinColumn(name = "source_topic_id", nullable = false)
    private Topic sourceTopic;

    @ManyToOne(fetch = FetchType.LAZY)
    @JoinColumn(name = "target_topic_id", nullable = false)
    private Topic targetTopic;

    @Enumerated(EnumType.STRING)
    @Column(name = "relationship_type", nullable = false)
    private RelationshipType relationshipType;

    @Column
    @Builder.Default
    private Float strength = 0.5f;

    @Builder.Default
    @Column(name = "ai_generated")
    private Boolean aiGenerated = false;

    @Column(columnDefinition = "TEXT")
    private String description;

    @CreationTimestamp
    @Column(name = "created_at", updatable = false)
    private LocalDateTime createdAt;
}
