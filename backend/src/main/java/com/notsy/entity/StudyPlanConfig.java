package com.notsy.entity;

import jakarta.persistence.*;
import lombok.*;
import org.hibernate.annotations.CreationTimestamp;
import org.hibernate.annotations.UpdateTimestamp;

import java.time.LocalDateTime;

@Entity
@Table(name = "study_plan_configs")
@Getter
@Setter
@NoArgsConstructor
@AllArgsConstructor
@Builder
public class StudyPlanConfig {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @ManyToOne(fetch = FetchType.LAZY)
    @JoinColumn(name = "user_id", nullable = false)
    private User user;

    @Column(name = "hours_per_day")
    @Builder.Default
    private Float hoursPerDay = 2.0f;

    @Column(name = "difficulty_preference")
    @Builder.Default
    private String difficultyPreference = "balanced";  // easy, balanced, hard

    @Column(name = "focus_areas", columnDefinition = "TEXT")
    private String focusAreas;  // JSON array

    @Column(name = "break_duration_minutes")
    @Builder.Default
    private Integer breakDurationMinutes = 15;

    @CreationTimestamp
    @Column(name = "created_at", updatable = false)
    private LocalDateTime createdAt;

    @UpdateTimestamp
    @Column(name = "updated_at")
    private LocalDateTime updatedAt;
}
