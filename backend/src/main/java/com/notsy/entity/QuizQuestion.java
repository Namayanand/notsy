package com.notsy.entity;

import jakarta.persistence.*;
import lombok.*;

@Entity
@Table(name = "quiz_questions")
@Getter
@Setter
@NoArgsConstructor
@AllArgsConstructor
@Builder
public class QuizQuestion {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(nullable = false, columnDefinition = "TEXT")
    private String question;

    @Enumerated(EnumType.STRING)
    @Column(name = "question_type")
    @Builder.Default
    private QuestionType questionType = QuestionType.MCQ;

    public enum QuestionType {
        MCQ, SHORT_ANSWER, DEFINITION_RECALL
    }

    @Column(nullable = false, columnDefinition = "TEXT")
    private String answer;

    @Column(columnDefinition = "TEXT")
    private String options;  // JSON array for MCQ options

    @Column(name = "is_correct")
    private Boolean isCorrect;

    @Column(name = "user_answer", columnDefinition = "TEXT")
    private String userAnswer;

    @ManyToOne(fetch = FetchType.LAZY)
    @JoinColumn(name = "quiz_id", nullable = false)
    private Quiz quiz;

    @Column(name = "difficulty_tier")
    @Builder.Default
    private Integer difficultyTier = 2;

    @Column(name = "area_covered")
    private String areaCovered;  // e.g. "thermodynamics", "calculus"
}
