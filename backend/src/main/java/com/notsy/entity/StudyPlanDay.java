package com.notsy.entity;

import jakarta.persistence.*;
import lombok.*;
import org.hibernate.annotations.CreationTimestamp;
import org.hibernate.annotations.UpdateTimestamp;

import java.time.LocalDate;
import java.time.LocalDateTime;

@Entity
@Table(name = "study_plan_days")
@Getter
@Setter
@NoArgsConstructor
@AllArgsConstructor
@Builder
public class StudyPlanDay {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @ManyToOne(fetch = FetchType.LAZY)
    @JoinColumn(name = "plan_id", nullable = false)
    private StudyPlan plan;

    @Column(name = "day_number", nullable = false)
    private Integer dayNumber;

    @Column(name = "date")
    private LocalDate date;

    @Column(columnDefinition = "TEXT")
    private String focus;  // e.g. "Thermodynamics basics"

    @Column(name = "topics_json", columnDefinition = "TEXT")
    private String topicsJson;  // Topics to cover as JSON

    @Column(name = "order_index")
    @Builder.Default
    private Integer orderIndex = 0;

    @Column(name = "hours_planned")
    @Builder.Default
    private Float hoursPlanned = 0f;

    @Column(name = "hours_completed")
    @Builder.Default
    private Float hoursCompleted = 0f;

    @Column(name = "is_completed")
    @Builder.Default
    private Boolean isCompleted = false;

    @Column(name = "completed_at")
    private LocalDateTime completedAt;

    @Column(name = "notes", columnDefinition = "TEXT")
    private String notes;
}