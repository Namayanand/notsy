package com.notsy.entity;

import jakarta.persistence.*;
import lombok.*;
import org.hibernate.annotations.CreationTimestamp;
import org.hibernate.annotations.UpdateTimestamp;

import java.time.LocalDateTime;

@Entity
@Table(name = "flashcards")
@Getter
@Setter
@NoArgsConstructor
@AllArgsConstructor
@Builder
public class Flashcard {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(nullable = false, columnDefinition = "TEXT")
    private String front;

    @Column(nullable = false, columnDefinition = "TEXT")
    private String back;

    @Enumerated(EnumType.STRING)
    @Column(name = "card_type")
    @Builder.Default
    private CardType cardType = CardType.BASIC;

    public enum CardType {
        BASIC, MULTIPLE_CHOICE, DEFINITION, SHORT_ANSWER
    }

    // SM-2 spaced repetition fields
    @Column(name = "ease_factor")
    @Builder.Default
    private Float easeFactor = 2.5f;

    @Column(name = "interval_days")
    @Builder.Default
    private Integer intervalDays = 1;

    @Column(name = "repetitions")
    @Builder.Default
    private Integer repetitions = 0;

    @Column(name = "next_review_date")
    private LocalDateTime nextReviewDate;

    @Column(name = "last_review_date")
    private LocalDateTime lastReviewDate;

    @Column(name = "last_quality")  // 0-5 rating from last review
    private Integer lastQuality;

    // Difficulty tier: 1=easy, 2=medium, 3=hard
    @Column(name = "difficulty_tier")
    @Builder.Default
    private Integer difficultyTier = 2;

    @ManyToOne(fetch = FetchType.LAZY)
    @JoinColumn(name = "topic_id", nullable = false)
    private Topic topic;

    @ManyToOne(fetch = FetchType.LAZY)
    @JoinColumn(name = "user_id", nullable = false)
    private User user;

    @ManyToOne(fetch = FetchType.LAZY)
    @JoinColumn(name = "conversation_id")
    private Conversation sourceConversation;

    @Column(name = "is_shared")
    @Builder.Default
    private Boolean isShared = false;

    @CreationTimestamp
    @Column(name = "created_at", updatable = false)
    private LocalDateTime createdAt;

    @UpdateTimestamp
    @Column(name = "updated_at")
    private LocalDateTime updatedAt;

    public void updateSM2(int quality) {
        // quality: 0-5 (0-2 = fail, 3-5 = pass)
        this.lastQuality = quality;
        this.lastReviewDate = LocalDateTime.now();

        if (quality < 3) {
            // Failed - reset
            this.repetitions = 0;
            this.intervalDays = 1;
        } else {
            // Passed
            if (this.repetitions == 0) {
                this.intervalDays = 1;
            } else if (this.repetitions == 1) {
                this.intervalDays = 6;
            } else {
                this.intervalDays = Math.round(this.intervalDays * this.easeFactor);
            }
            this.repetitions++;
        }

        // Update ease factor
        this.easeFactor = Math.max(1.3f,
            this.easeFactor + (0.1f - (5 - quality) * (0.08f + (5 - quality) * 0.02f)));

        this.nextReviewDate = LocalDateTime.now().plusDays(this.intervalDays);
    }
}
